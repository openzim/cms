from collections.abc import Callable, Sequence
from typing import Any

from fastapi.routing import RouteContext
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Match
from starlette.types import ASGIApp

from cms_backend.context import Context

CDN_PULL_ALLOWED_ATTR = "_cdn_pull_allowed"


def cdn_pull_allowed[F: Callable[..., Any]](func: F) -> F:
    """Mark a route as allowed to be served to our CDN."""
    setattr(func, CDN_PULL_ALLOWED_ATTR, True)
    return func


def is_cdn_pull_allowed(endpoint: Any) -> bool:
    return bool(getattr(endpoint, CDN_PULL_ALLOWED_ATTR, False))


class XPullRestrictionMiddleware(BaseHTTPMiddleware):
    """Reject CDN pull requests except on routes marked with @cdn_pull_allowed.

    Requests forwarded by our CDN carry an ``X-Pull`` header. Only endpoints
    explicitly marked with `cdn_pull_allowed` are served to the CDN.
    OPTIONS requests are always accepted so CORS preflights keep working.
    """

    def __init__(self, app: ASGIApp, *, route_contexts: Sequence[RouteContext]) -> None:
        super().__init__(app)
        self.route_contexts = route_contexts

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.headers.get(
            "x-pull"
        ) == Context.x_pull_header and not self._is_allowed(request):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "CDN pull requests are only allowed on CDN routes",
                },
            )

        return await call_next(request)

    def _is_allowed(self, request: Request) -> bool:
        if request.method == "OPTIONS":
            return True
        for context in self.route_contexts:
            match, _ = context.matches(request.scope)
            if match is Match.FULL and is_cdn_pull_allowed(context.endpoint):
                return True
        return False
