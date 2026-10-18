import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse, RawAxiosResponseHeaders, AxiosResponseHeaders } from 'axios';
import { getSessionToken, setSessionToken } from './sessionToken';

// Base API configuration
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  '/api/v1';

// In-Memory Fast Client-Side TTL Cache
interface CacheItem {
  data: unknown;
  headers: RawAxiosResponseHeaders | AxiosResponseHeaders;
  status: number;
  statusText: string;
  expiresAt: number;
}

const memoryCache = new Map<string, CacheItem>();
const DEFAULT_GET_CACHE_TTL_MS = 20000;
/** Map pages stay warm longer — revisit should feel instant */
const MAP_GET_CACHE_TTL_MS = 90000;

function cacheTtlForUrl(url?: string): number {
  const u = url || '';
  if (
    u.includes('/dashboard/map-layer') ||
    u.includes('/global-trees') ||
    u.includes('/regions')
  ) {
    return MAP_GET_CACHE_TTL_MS;
  }
  return DEFAULT_GET_CACHE_TTL_MS;
}

export function clearApiClientCache(prefix?: string) {
  if (!prefix) {
    memoryCache.clear();
    return;
  }
  for (const key of memoryCache.keys()) {
    if (key.includes(prefix)) {
      memoryCache.delete(key);
    }
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 20000,
  withCredentials: true,
});

// Request Interceptor: Attach JWT Token, Zero-Trust Timestamp & Check In-Memory Cache
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getSessionToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (config.headers) {
      config.headers['X-Timestamp'] = (Date.now() / 1000).toString();
    }

    if (config.method?.toLowerCase() === 'get') {
      const cacheKey = `${config.url}?${JSON.stringify(config.params || {})}`;
      const cached = memoryCache.get(cacheKey);

      if (cached && Date.now() < cached.expiresAt) {
        config.adapter = async () => ({
          data: cached.data,
          status: cached.status,
          statusText: cached.statusText,
          headers: cached.headers,
          config,
          request: {},
        });
      }
    } else {
      const resource = config.url?.split('/')[1] || '';
      if (resource) {
        clearApiClientCache(resource);
        // Cross-domain cache invalidation: tree/region/alert changes impact dashboard and map layers
        if (['trees', 'detections', 'regions', 'measurements', 'alerts'].includes(resource)) {
          clearApiClientCache('dashboard');
          clearApiClientCache('map-layer');
          clearApiClientCache('global-trees');
        }
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Cache GET Responses & Handle Auth Expiry
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    if (response.config.method?.toLowerCase() === 'get' && response.status === 200) {
      const cacheKey = `${response.config.url}?${JSON.stringify(response.config.params || {})}`;
      memoryCache.set(cacheKey, {
        data: response.data,
        headers: response.headers,
        status: response.status,
        statusText: response.statusText,
        expiresAt: Date.now() + cacheTtlForUrl(response.config.url),
      });
    }
    return response;
  },
  (error: AxiosError) => {
    if (!error.response) {
      console.error(
        '[API Connection Error] Could not connect to backend server at ' +
          API_BASE_URL +
          '. Ensure FastAPI is running (uvicorn app.main:app --reload --port 8000).'
      );
    } else if (error.response.status === 401) {
      const requestUrl = error.config?.url || '';
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && !requestUrl.includes('/auth/logout')) {
        setSessionToken(null);
        localStorage.removeItem('agro_access_token');
        localStorage.removeItem('agro_user');
        memoryCache.clear();
        window.location.href = '/login?session_expired=true';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
