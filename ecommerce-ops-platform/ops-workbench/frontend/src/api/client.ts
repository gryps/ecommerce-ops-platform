const TOKEN_KEY = "production_workbench_token";

export function storedToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function apiErrorMessage(payload: unknown, status: number): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      const error = item as { loc?: unknown[]; msg?: unknown };
      const field = String(error.loc?.at(-1) ?? "");
      const label = { username: "账号", password: "密码", current_password: "当前密码", new_password: "新密码" }[field] ?? field;
      const rawMessage = typeof error.msg === "string" ? error.msg : "输入内容无效";
      const minimum = rawMessage.match(/at least (\d+) characters?/i);
      if (minimum) return `${label}至少需要 ${minimum[1]} 个字符`;
      if (/field required/i.test(rawMessage)) return `请填写${label}`;
      return label ? `${label}：${rawMessage}` : rawMessage;
    });
    if (messages.length) return messages.join("；");
  }
  return `请求失败 (${status})`;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (authenticated) {
    const token = storedToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  if (response.status === 401 && authenticated) clearToken();
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(payload, response.status));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = storedToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`/api/v1${path}`, { ...options, headers });
  if (response.status === 401) clearToken();
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(payload, response.status));
  }
  return response.blob();
}
