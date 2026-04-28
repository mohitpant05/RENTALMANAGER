import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const host = request.headers.get("host") || "";
  const isLocalhost = host.startsWith("localhost") || host.startsWith("127.0.0.1");

  let tenantSlug: string | null = null;

  if (isLocalhost) {
    const match = pathname.match(/^\/t\/([^/]+)(\/.*)?$/);
    if (match) {
      tenantSlug = match[1];
      const rewrittenPath = match[2] || "/";
      const url = request.nextUrl.clone();
      url.pathname = rewrittenPath;
      const response = NextResponse.rewrite(url);
      response.headers.set("x-tenant-slug", tenantSlug);
      return response;
    }
  } else {
    const parts = host.split(".");
    if (parts.length >= 3) {
      tenantSlug = parts[0];
    }
  }

  if (tenantSlug) {
    const response = NextResponse.next();
    response.headers.set("x-tenant-slug", tenantSlug);
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
