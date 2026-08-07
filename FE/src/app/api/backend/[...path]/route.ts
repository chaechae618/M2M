import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const ACCESS_COOKIE = "m2m_access_token";
const REFRESH_COOKIE = "m2m_refresh_token";
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

type TokenData = {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
};

function setTokenCookies(response: NextResponse, tokens: TokenData) {
  const secure = process.env.NODE_ENV === "production";
  response.cookies.set(ACCESS_COOKIE, tokens.accessToken, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: tokens.expiresIn,
  });
  response.cookies.set(REFRESH_COOKIE, tokens.refreshToken, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: 60 * 60 * 24 * 14,
  });
}

function clearTokenCookies(response: NextResponse) {
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
}

async function refreshTokens(refreshToken: string): Promise<TokenData | null> {
  const response = await fetch(`${backendUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ refreshToken }),
    cache: "no-store",
  });
  if (!response.ok) return null;
  const payload = await response.json();
  return payload.data as TokenData;
}

async function proxy(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const routePath = path.map(encodeURIComponent).join("/");
  const incomingUrl = new URL(request.url);
  const targetUrl = `${backendUrl}/api/v1/${routePath}${incomingUrl.search}`;
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_COOKIE)?.value;
  const refreshToken = cookieStore.get(REFRESH_COOKIE)?.value;
  const method = request.method.toUpperCase();
  const originalBody = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();
  const isLogin = routePath === "auth/login";
  const isSignup = routePath === "auth/signup";
  const isLogout = routePath === "auth/logout";

  const makeHeaders = (token?: string) => {
    const headers = new Headers();
    const contentType = request.headers.get("content-type");
    const idempotencyKey = request.headers.get("idempotency-key");
    headers.set("Accept", "application/json");
    if (contentType) headers.set("Content-Type", contentType);
    if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return headers;
  };

  const requestBody = isLogout && refreshToken
    ? new TextEncoder().encode(JSON.stringify({ refreshToken })).buffer
    : originalBody;
  let backendResponse = await fetch(targetUrl, {
    method,
    headers: makeHeaders(accessToken),
    body: requestBody,
    cache: "no-store",
  });
  let rotatedTokens: TokenData | null = null;

  if (backendResponse.status === 401 && refreshToken && !isLogin && !isSignup && !isLogout) {
    rotatedTokens = await refreshTokens(refreshToken);
    if (rotatedTokens) {
      backendResponse = await fetch(targetUrl, {
        method,
        headers: makeHeaders(rotatedTokens.accessToken),
        body: originalBody,
        cache: "no-store",
      });
    }
  }

  const responseBody = await backendResponse.arrayBuffer();
  const response = new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      "Content-Type": backendResponse.headers.get("content-type") ?? "application/json",
      ...(backendResponse.headers.get("content-disposition")
        ? { "Content-Disposition": backendResponse.headers.get("content-disposition") as string }
        : {}),
      "Cache-Control": "no-store",
    },
  });

  if (rotatedTokens) setTokenCookies(response, rotatedTokens);

  if (backendResponse.ok && (isLogin || isSignup)) {
    const payload = JSON.parse(new TextDecoder().decode(responseBody));
    const tokens: TokenData = {
      accessToken: payload.data.accessToken,
      refreshToken: payload.data.refreshToken,
      expiresIn: payload.data.expiresIn,
    };
    delete payload.data.accessToken;
    delete payload.data.refreshToken;
    const authResponse = NextResponse.json(payload, {
      status: backendResponse.status,
      headers: { "Cache-Control": "no-store" },
    });
    setTokenCookies(authResponse, tokens);
    return authResponse;
  }

  if (isLogout || (backendResponse.status === 401 && !rotatedTokens)) {
    clearTokenCookies(response);
  }
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
