from pydantic import BaseModel

from integrations.ig.rest.base import IgRestClient


class IgLoginCommand(BaseModel):
    identifier: str
    password: str


class IgSessionClient(IgRestClient):
    async def login(self, command: IgLoginCommand) -> dict[str, object]:
        payload = {"identifier": command.identifier, "password": command.password}
        return await self.request_json(
            "POST",
            "/session",
            extra_headers={"Version": "3", "Content-Type": "application/json"},
            json=payload,
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, object]:
        return await self.request_json(
            "POST",
            "/session/refresh-token",
            extra_headers={"Version": "1", "Content-Type": "application/json"},
            json={"refresh_token": refresh_token},
        )

    async def fetch_session_tokens(self, oauth_bearer: str) -> dict[str, str]:
        async with self.build_client({"Authorization": f"Bearer {oauth_bearer}"}) as client:
            response = await client.get("/session", params={"fetchSessionTokens": True})
            self._raise_for_ig_error(response)
            return {
                "cst": response.headers.get("CST", ""),
                "x_security_token": response.headers.get("X-SECURITY-TOKEN", ""),
            }
