from fastapi import HTTPException, Request
from .settings import API_KEY

def is_loopback(request: Request) -> bool:
    host = request.client.host if request and request.client else ""
    return host in ("127.0.0.1", "::1")

def guard(x_api_key: str | None, request: Request):
    if is_loopback(request):
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
