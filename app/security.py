import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class LocalSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        host = request.url.hostname
        if host not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return JSONResponse({"error":"Local access only."}, status_code=403)
        if request.method not in {"GET","HEAD","OPTIONS"} and not request.url.path.startswith("/desktop/"):
            expected = request.session.get("csrf")
            received = request.headers.get("X-CSRF-Token", "")
            origin = request.headers.get("origin")
            if (not expected or not secrets.compare_digest(expected, received) or
                (origin and origin != str(request.base_url).rstrip("/"))):
                return JSONResponse({"error":"Session expired. Reload the app before trying again."}, status_code=403)
            if int(request.headers.get("content-length","0") or 0) > 55 * 1024 * 1024:
                return JSONResponse({"error":"Maximum request size is 55 MB."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' https://pbs.twimg.com data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        return response
