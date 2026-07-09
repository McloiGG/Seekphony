const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function apiBaseUrl(): string {
  const runtimeUrl = window.__SEEKPHONY_CONFIG__?.apiBaseUrl;
  const buildUrl = import.meta.env.VITE_API_BASE_URL;
  return stripTrailingSlash(runtimeUrl || buildUrl || DEFAULT_API_BASE_URL);
}

function stripTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}
