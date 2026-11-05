"""CSRF defence for the cookie-authenticated auth endpoints.

SameSite=Lax already stops cross-site POSTs from carrying the refresh cookie,
but "same site" is wider than "same origin" (any other port or subdomain on the
same host counts). So the cookie endpoints also require:

* a custom ``X-Requested-With`` header, which a browser only sends cross-origin
  after a CORS preflight that our allow-list rejects, and
* an ``Origin`` header (when the browser sends one) from the allow-list.

Non-browser clients send no Origin and must still set the header.
"""

from fastapi import HTTPException, Request, status

from app.core.config import settings

CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "pt"


async def require_csrf(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Origin not allowed.")
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing CSRF header.")
