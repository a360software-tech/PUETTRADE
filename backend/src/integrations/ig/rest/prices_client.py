from integrations.ig.rest.base import IgRestClient


class IgPricesClient(IgRestClient):
    async def get_prices(
        self,
        epic: str,
        resolution: str,
        auth_headers: dict[str, str],
        max_points: int = 200,
    ) -> dict[str, object]:
        params = {"resolution": resolution, "max": max_points, "pageSize": 0}
        return await self.request_json(
            "GET",
            f"/prices/{epic}",
            extra_headers={**auth_headers, "Version": "3"},
            params=params,
        )

    async def get_prices_by_range(
        self,
        epic: str,
        resolution: str,
        start_date: str,
        end_date: str,
        auth_headers: dict[str, str],
    ) -> dict[str, object]:
        return await self.request_json(
            "GET",
            f"/prices/{epic}/{resolution}/{start_date}/{end_date}",
            extra_headers={**auth_headers, "Version": "3"},
        )
