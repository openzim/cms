from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cms_backend.context import Context


class XPullRestrictionMiddleware(BaseHTTPMiddleware):
    """Reject CDN pull requests except on the illustrations API.

    Requests forwarded by our CDN carry an ``X-Pull`` header. We only want the
    CDN to be able to serve illustrations, so any other endpoint is rejected.
    """

    ILLUSTRATIONS_PATH = "/v1/illustrations/"
    ALLOWED_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.headers.get(
            "x-pull"
        ) == Context.x_pull_header and not self._is_illustration_request(request):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "CDN pull requests are only allowed for illustrations",
                },
            )

        return await call_next(request)

    def _is_illustration_request(self, request: Request) -> bool:
        if request.method not in self.ALLOWED_METHODS:
            return False
        path = request.scope["path"]
        return path.startswith(self.ILLUSTRATIONS_PATH) or path == (
            self.ILLUSTRATIONS_PATH.rstrip("/")
        )
