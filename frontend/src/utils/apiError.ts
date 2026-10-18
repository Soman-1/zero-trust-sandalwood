/** Pull a user-facing message out of an Axios/FastAPI error. */

type ApiErrorBody = {
  error?: { message?: string };
  detail?: string | { msg?: string }[];
  message?: string;
};

function detailToText(detail: ApiErrorBody['detail']): string | undefined {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const first = detail.find((item) => item?.msg);
    if (first?.msg) return first.msg;
  }
  return undefined;
}

export function getApiErrorMessage(err: unknown, fallback = 'Request failed.'): string {
  if (!err || typeof err !== 'object') {
    return err instanceof Error ? err.message : fallback;
  }

  const data = (err as { response?: { data?: ApiErrorBody } }).response?.data;
  const fromBody = data?.error?.message || detailToText(data?.detail) || data?.message;
  if (fromBody) return fromBody;

  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
