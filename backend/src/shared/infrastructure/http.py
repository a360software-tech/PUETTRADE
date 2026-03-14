import httpx


def build_async_client(base_url: str, timeout: float, headers: dict[str, str] | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url, timeout=timeout, headers=headers)
