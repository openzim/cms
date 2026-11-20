# pyright: strict, reportUnusedFunction=false
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient

from cms_backend.api.main import create_app
from cms_backend.api.middleware.cors import (
    PublicRouteCORSMiddleware,
    cors_public,
    effective_route_contexts,
    is_cors_public,
    validate_public_cors_routes,
)

ALLOWED_ORIGIN = "https://allowed.example"
OTHER_ORIGIN = "https://other.example"


def make_test_app(*, allowed_origins: list[str] | None) -> FastAPI:
    """Small app with public, private and mixed-method routes."""
    app = FastAPI()

    @app.get("/public")
    @cors_public
    def read_public() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"ETag": '"abc"'})

    @app.get("/public/{item_id}")
    @cors_public
    def read_public_item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    @app.get("/private")
    def read_private() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/mixed")
    @cors_public
    def read_mixed() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/mixed")
    def write_mixed() -> dict[str, bool]:
        return {"ok": True}

    route_contexts = effective_route_contexts(app.routes)
    validate_public_cors_routes(route_contexts)
    app.add_middleware(
        PublicRouteCORSMiddleware,
        route_contexts=route_contexts,
        allowed_origins=allowed_origins,
    )
    return app


def test_public_route_allows_arbitrary_origin() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    response = client.get("/public", headers={"Origin": OTHER_ORIGIN})

    assert response.status_code == HTTPStatus.OK
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    assert response.headers["access-control-expose-headers"] == "ETag"


def test_public_route_preflight_allows_arbitrary_origin() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    response = client.options(
        "/public",
        headers={
            "Origin": OTHER_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, If-None-Match",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    assert "GET" in response.headers["access-control-allow-methods"]
    assert (
        response.headers["access-control-allow-headers"]
        == "Authorization, If-None-Match"
    )


def test_public_route_with_path_parameter() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    response = client.get("/public/abc", headers={"Origin": OTHER_ORIGIN})

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"item_id": "abc"}
    assert response.headers["access-control-allow-origin"] == "*"


def test_public_route_without_allowed_origins() -> None:
    client = TestClient(make_test_app(allowed_origins=None))

    response = client.get("/public", headers={"Origin": OTHER_ORIGIN})

    assert response.headers["access-control-allow-origin"] == "*"


def test_private_route_rejects_arbitrary_origin() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    response = client.get("/private", headers={"Origin": OTHER_ORIGIN})

    assert response.status_code == HTTPStatus.OK
    assert "access-control-allow-origin" not in response.headers


def test_private_route_preflight_rejects_arbitrary_origin() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    response = client.options(
        "/private",
        headers={
            "Origin": OTHER_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "access-control-allow-origin" not in response.headers


def test_private_route_allows_allowlisted_origin() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    response = client.get("/private", headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_public_status_is_method_specific() -> None:
    client = TestClient(make_test_app(allowed_origins=[ALLOWED_ORIGIN]))

    public_preflight = client.options(
        "/mixed",
        headers={
            "Origin": OTHER_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert public_preflight.status_code == HTTPStatus.OK
    assert public_preflight.headers["access-control-allow-origin"] == "*"

    private_preflight = client.options(
        "/mixed",
        headers={
            "Origin": OTHER_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert private_preflight.status_code == HTTPStatus.BAD_REQUEST
    assert "access-control-allow-origin" not in private_preflight.headers


def test_cors_public_rejects_unsafe_methods() -> None:
    app = FastAPI()

    @app.post("/danger")
    @cors_public
    def write_danger() -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(RuntimeError, match="@cors_public"):
        validate_public_cors_routes(list(iter_route_contexts(app.routes)))


EXPECTED_PUBLIC_ROUTES = {
    ("/v1/staging/catalog.xml", "GET"),
    ("/v1/staging/catalog.xml", "HEAD"),
    ("/v1/staging/opds.xml", "GET"),
    ("/v1/staging/opds.xml", "HEAD"),
    ("/v1/collections", "GET"),
    ("/v1/collections/{collection_id_or_name}", "GET"),
    ("/v1/collections/{collection_id_or_name}/catalog.xml", "GET"),
    ("/v1/collections/{collection_id_or_name}/catalog.xml", "HEAD"),
    ("/v1/collections/{collection_id_or_name}/opds.xml", "GET"),
    ("/v1/collections/{collection_id_or_name}/opds.xml", "HEAD"),
    ("/v1/books", "GET"),
    ("/v1/books/zims", "GET"),
    ("/v1/books/languages", "GET"),
    ("/v1/books/flavours", "GET"),
    ("/v1/books/{book_id}", "GET"),
    ("/v1/books/{book_id}/raw_metadata/{metadata}", "GET"),
    ("/v1/titles", "GET"),
    ("/v1/titles/{title_identifier}", "GET"),
    ("/v1/config", "GET"),
    ("/v1/events", "GET"),
    ("/v1/healthcheck", "GET"),
    ("/v1/warehouses", "GET"),
    ("/v1/stats/downloads/titles/{title_identifier}", "GET"),
}


def test_marks_expected_public_routes() -> None:
    app = create_app(debug=True, allowed_origins=[])
    contexts = effective_route_contexts(app.routes)

    actual = {
        (context.path, method)
        for context in contexts
        if is_cors_public(context.endpoint)
        for method in (context.methods or ())
    }

    assert actual == EXPECTED_PUBLIC_ROUTES


def test_does_not_mark_restricted_methods_on_public_paths() -> None:
    app = create_app(debug=True, allowed_origins=[ALLOWED_ORIGIN])
    client = TestClient(app)

    public_preflight = client.options(
        "/v1/collections",
        headers={
            "Origin": OTHER_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert public_preflight.status_code == HTTPStatus.OK
    assert public_preflight.headers["access-control-allow-origin"] == "*"

    private_preflight = client.options(
        "/v1/collections",
        headers={
            "Origin": OTHER_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert private_preflight.status_code == HTTPStatus.BAD_REQUEST
    assert "access-control-allow-origin" not in private_preflight.headers
