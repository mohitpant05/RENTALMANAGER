import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.core.admin.ip_middleware import SuperadminIPMiddleware


def _make_request(path: str, client_ip: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "root_path": "",
        "client": (client_ip, 0),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_ip_middleware_allows_when_whitelist_empty():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="")
    request = _make_request("/api/platform/login", "1.2.3.4")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ip_middleware_blocks_unlisted_ip():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="10.0.0.1,10.0.0.2")
    request = _make_request("/api/platform/login", "1.2.3.4")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ip_middleware_allows_listed_ip():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="10.0.0.1,10.0.0.2")
    request = _make_request("/api/platform/login", "10.0.0.1")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ip_middleware_skips_non_platform_paths():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="10.0.0.1")
    request = _make_request("/api/auth/login", "1.2.3.4")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
