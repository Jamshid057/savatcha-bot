import { getInitData } from "../lib/telegram";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
  }
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  onUnauthorized = fn;
}

export function authHeaders(): Record<string, string> {
  const initData = getInitData();
  return initData ? { Authorization: `tma ${initData}` } : {};
}

type Query = Record<string, string | number | boolean | undefined | null>;

export function withQuery(path: string, query?: Query): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "validation_error";
  } catch {
    /* tana JSON emas */
  }
  return `http_${res.status}`;
}

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown; query?: Query } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...authHeaders() };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(withQuery(`/api${path}`, opts.query), {
    method: opts.method ?? "GET",
    headers,
    body,
    credentials: "same-origin",
  });
  if (!res.ok) {
    if (res.status === 401) onUnauthorized?.();
    throw new ApiError(res.status, await errorDetail(res));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Himoyalangan rasm (chek): <img> sarlavha yubora olmagani uchun blob sifatida olinadi. */
export async function fetchBlobUrl(path: string): Promise<string> {
  const res = await fetch(`/api${path}`, { headers: authHeaders(), credentials: "same-origin" });
  if (!res.ok) throw new ApiError(res.status, await errorDetail(res));
  return URL.createObjectURL(await res.blob());
}
