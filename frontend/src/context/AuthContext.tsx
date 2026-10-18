import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, UserRole, TokenResponse } from '../types';
import { authApi } from '../api/auth';
import { setSessionToken } from '../api/sessionToken';
import { useToast } from './ToastContext';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<TokenResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (...roles: UserRole[]) => boolean;
  isAdmin: boolean;
  isOperator: boolean;
  canManage: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const savedUser = localStorage.getItem('agro_user');
    if (savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [token, setToken] = useState<string | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const { success, error: toastError } = useToast();

  const refreshUser = useCallback(async () => {
    try {
      const userProfile = await authApi.getMe();
      setUser(userProfile);
    } catch (err) {
      console.warn('Session check failed or expired:', err);
      setUser(null);
      setToken(null);
      setSessionToken(null);
      localStorage.removeItem('agro_access_token');
      localStorage.removeItem('agro_user');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (usernameOrEmail: string, password: string): Promise<TokenResponse> => {
    try {
      const resp = await authApi.login({
        username_or_email: usernameOrEmail,
        password: password,
      });

      setToken(resp.access_token);
      setSessionToken(resp.access_token);
      setUser(resp.user);
      localStorage.removeItem('agro_access_token');

      success(`Welcome back, ${resp.user.full_name || resp.user.username}!`, 'Zero Trust session established.');
      return resp;
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { error?: { message?: string }; detail?: string } } };
      const detail = errorObj.response?.data?.error?.message || errorObj.response?.data?.detail || 'Authentication failed.';
      toastError('Login Failed', detail);
      throw err;
    }
  };

  const logout = async () => {
    try {
      // The access token lives only in memory and is gone after a reload.
      // The httpOnly cookie is still sent, and that is enough to revoke the session.
      await authApi.logout();
    } catch (e) {
      console.error('Logout error note:', e);
    } finally {
      setToken(null);
      setSessionToken(null);
      setUser(null);
      localStorage.removeItem('agro_access_token');
      localStorage.removeItem('agro_user');
      success('Logged Out', 'Zero Trust session revoked.');
    }
  };

  const hasRole = (...roles: UserRole[]): boolean => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  const isAdmin = user?.role === 'ADMIN';
  const isOperator = user?.role === 'OPERATOR';
  const canManage = user?.role === 'ADMIN' || user?.role === 'OPERATOR';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
        hasRole,
        isAdmin,
        isOperator,
        canManage,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
