from integrations.ig.rest.base import IgRestClient


class IgMarketsClient(IgRestClient):
    async def search(self, search_term: str, auth_headers: dict[str, str]) -> dict[str, object]:
        return await self.request_json("GET", "/markets", extra_headers=auth_headers, params={"searchTerm": search_term})

    async def get_market(self, epic: str, auth_headers: dict[str, str]) -> dict[str, object]:
        return await self.request_json("GET", f"/markets/{epic}", extra_headers={**auth_headers, "Version": "4"})

    async def get_categories(self, auth_headers: dict[str, str]) -> dict[str, object]:
        return await self.request_json("GET", "/categories", extra_headers=auth_headers)

    async def get_instruments(self, category_id: str, auth_headers: dict[str, str]) -> dict[str, object]:
        return await self.request_json("GET", f"/categories/{category_id}/instruments", extra_headers=auth_headers)
