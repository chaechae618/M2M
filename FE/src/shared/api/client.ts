import type { ApiEnvelope } from "@/shared/api/types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "REQUEST_FAILED",
    public readonly details: Array<{ field?: string | null; reason: string }> = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  const response = await fetch(`/api/backend/${path.replace(/^\//, "")}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const envelope = (await response.json().catch(() => null)) as ApiEnvelope<T> | null;
  if (!response.ok || !envelope || !envelope.success) {
    const failure = envelope && !envelope.success ? envelope.error : null;
    throw new ApiError(
      failure?.message ?? "요청을 처리하지 못했습니다.",
      response.status,
      failure?.code,
      failure?.details,
    );
  }

  return envelope.data;
}

export function jsonRequest(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function apiAssetUrl(url?: string | null): string | null {
  if (!url) return null;
  return url.startsWith("/uploads/") ? `/api/files/${url.slice("/uploads/".length)}` : url;
}
