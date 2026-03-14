from collections.abc import Mapping
from typing import Any

import httpx
from httpx import AsyncClient, Response

from shared.config.settings import Settings
from shared.errors.base import AuthenticationError, ExternalServiceError, IntegrationError
from shared.infrastructure.http import build_async_client


class IgRestClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_client(self, extra_headers: Mapping[str, str] | None = None) -> AsyncClient:
        headers = {
            "X-IG-API-KEY": self._settings.ig_api_key,
            "Accept": "application/json; charset=UTF-8",
        }
        if extra_headers:
            headers.update(extra_headers)
        return build_async_client(self._settings.ig_api_url, self._settings.ig_timeout_seconds, headers)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        extra_headers: Mapping[str, str] | None = None,
        params: Mapping[str, object] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> dict[str, object]:
        try:
            async with self.build_client(extra_headers) as client:
                response = await client.request(method, path, params=params, json=json)
                self._raise_for_ig_error(response)
                return response.json()
        except httpx.TimeoutException as exc:
            raise ExternalServiceError("IG API timed out") from exc
        except httpx.NetworkError as exc:
            raise ExternalServiceError("Unable to reach IG API") from exc

    def _raise_for_ig_error(self, response: Response) -> None:
        if response.is_success:
            return

        detail = self._extract_ig_error_detail(response)
        if response.status_code == 401:
            raise AuthenticationError(detail)
        if response.is_client_error:
            raise IntegrationError(detail, status_code=response.status_code)
        raise ExternalServiceError(detail)

    @staticmethod
    def _extract_ig_error_detail(response: Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"IG API error ({response.status_code})"

        error_code = payload.get("errorCode")
        if error_code:
            return str(error_code)
        return f"IG API error ({response.status_code})"
