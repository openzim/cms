from collections.abc import Callable, Sequence
from typing import Any

from fastapi.routing import RouteContext, iter_route_contexts
from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import BaseRoute, Match
from starlette.types import ASGIApp, Receive, Scope, Send

CORS_PUBLIC_ATTR = "_cors_public"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def cors_public[F: Callable[..., Any]](func: F) -> F:
    """Mark a route handler as readable from any origin."""
    setattr(func, CORS_PUBLIC_ATTR, True)
    return func


def is_cors_public(endpoint: Any) -> bool:
    return bool(getattr(endpoint, CORS_PUBLIC_ATTR, False))


def effective_route_contexts(routes: Sequence[BaseRoute]) -> list[RouteContext]:
    """Resolve the app routes, including routes from included routers."""
    return list(iter_route_contexts(routes))


def validate_public_cors_routes(contexts: Sequence[RouteContext]) -> None:
    """Reject @cors_public on anything but read-only routes."""
    for context in contexts:
        if not is_cors_public(context.endpoint):
            continue

        unsafe_methods = set(context.methods or ()) - SAFE_METHODS
        if unsafe_methods:
            raise RuntimeError(
                f"@cors_public is only allowed on safe methods; "
                f"{context.path} exposes {', '.join(sorted(unsafe_methods))}"
            )


def _public_methods(contexts: Sequence[RouteContext]) -> list[str]:
    methods = sorted(
        {
            method
            for context in contexts
            if is_cors_public(context.endpoint)
            for method in (context.methods or ())
        }
    )
    return methods or ["GET", "HEAD"]


class PublicRouteCORSMiddleware:
    """Select the wildcard or allowlisted CORS policy per request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        route_contexts: Sequence[RouteContext],
        allowed_origins: Sequence[str] | None = None,
        expose_headers: Sequence[str] = ("ETag",),
    ) -> None:
        self.route_contexts = route_contexts

        self.public = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=_public_methods(route_contexts),
            allow_headers=["*"],
            expose_headers=list(expose_headers),
        )
        self.private: ASGIApp = (
            CORSMiddleware(
                app,
                allow_origins=list(allowed_origins),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            if allowed_origins
            else app
        )

    @staticmethod
    def _requested_method(scope: Scope) -> str:
        """Return the method a preflight is actually asking about."""
        if scope["method"] == "OPTIONS":
            headers = Headers(scope=scope)
            if "origin" in headers and "access-control-request-method" in headers:
                return headers["access-control-request-method"].upper()
        return scope["method"]

    def _is_public(self, scope: Scope) -> bool:
        # Match against the method the request (or its preflight) targets so
        # that e.g. POST /v1/collections is not classified as public just
        # because GET on the same path is.
        match_scope = {**scope, "method": self._requested_method(scope)}
        for context in self.route_contexts:
            match, _ = context.matches(match_scope)
            if match is Match.FULL:
                return is_cors_public(context.endpoint)
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._is_public(scope):
            await self.public(scope, receive, send)
        else:
            await self.private(scope, receive, send)
