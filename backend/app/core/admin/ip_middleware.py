import ipaddress

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

PLATFORM_PREFIXES = ("/api/platform/",)


class SuperadminIPMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_ips: str = ""):
        super().__init__(app)
        self._networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in allowed_ips.split(","):
            entry = entry.strip()
            if entry:
                self._networks.append(ipaddress.ip_network(entry, strict=False))

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not any(path.startswith(p) for p in PLATFORM_PREFIXES):
            return await call_next(request)

        if not self._networks:
            return await call_next(request)

        client_ip = request.client.host if request.client else "0.0.0.0"
        addr = ipaddress.ip_address(client_ip)
        if any(addr in net for net in self._networks):
            return await call_next(request)

        return Response(status_code=404)
