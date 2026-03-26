from integrations.ig.rest.base import IgRestClient


class IgAccountsClient(IgRestClient):
    async def fetch_accounts(self, auth_headers: dict[str, str]) -> dict[str, object]:
        return await self.request_json(
            "GET",
            "/accounts",
            extra_headers={**auth_headers, "Version": "1"},
        )
