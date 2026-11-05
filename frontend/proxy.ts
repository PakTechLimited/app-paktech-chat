import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Route guard (Next 16 "proxy", formerly middleware).
 *
 * The real session is an httpOnly refresh cookie on the API's origin plus an
 * in-memory access token, neither of which Next can see. So this only checks
 * the non-secret `pt_session` hint cookie the client sets at login: visitors
 * who clearly never signed in are redirected before any app code is sent.
 *
 * This is UX, not security: every API call is still authenticated and
 * authorised server-side (admin role is checked live in the database).
 */
export function proxy(request: NextRequest) {
  if (!request.cookies.has("pt_session")) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/wall/:path*", "/ai/:path*", "/admin/:path*"],
};
