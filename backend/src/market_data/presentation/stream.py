import asyncio
import json
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from authentication.application.dto import StreamingTokensResponse
from authentication.application.service import AuthService, get_auth_service
from integrations.ig.streaming.lightstreamer import (
    CandleUpdate,
    LightstreamerCredentials,
    lightstreamer_gateway,
)
from market_data.application.dto import Resolution
from market_data.domain.candles import to_lightstreamer_resolution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data-stream"])


async def get_streaming_tokens(
    auth_service: AuthService = Depends(get_auth_service),
) -> StreamingTokensResponse:
    return await auth_service.get_session_tokens()


async def generate_sse_events(
    epic: str,
    resolution: str,
    auth_service: AuthService,
):
    listener_id: str | None = None
    try:
        tokens = await auth_service.get_session_tokens()
        status = auth_service.get_status()

        credentials = LightstreamerCredentials(
            account_id=tokens.account_id,
            cst=tokens.cst,
            x_security_token=tokens.x_security_token,
            endpoint=status.lightstreamer_endpoint or "https://demo-apd.marketdatasystems.com",
        )

        await lightstreamer_gateway.connect(credentials)

        queue: asyncio.Queue[CandleUpdate | None] = asyncio.Queue()

        loop = asyncio.get_running_loop()

        def callback(update: CandleUpdate) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, update)

        listener_id = await lightstreamer_gateway.subscribe_to_candles(
            epic=epic,
            resolution=resolution,
            callback=callback,
        )

        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'epic': epic})}\n\n"

        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=30)

                if update is None:
                    break

                data = {
                    "type": "candle_update",
                    "epic": update.epic,
                    "time": update.time,
                    "open": update.open_price,
                    "high": update.high,
                    "low": update.low,
                    "close": update.close,
                    "volume": update.volume,
                    "completed": update.completed,
                }

                yield f"data: {json.dumps(data)}\n\n"

            except asyncio.TimeoutError:
                yield f": heartbeat\n\n"

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    finally:
        if listener_id is not None:
            try:
                await lightstreamer_gateway.unsubscribe(epic, resolution, listener_id)
            except Exception:
                pass


@router.get("/{epic}/stream")
async def stream_candles(
    epic: str,
    resolution: Resolution = Query(default="MINUTE"),
    auth_service: AuthService = Depends(get_auth_service),
):
    ls_resolution = to_lightstreamer_resolution(resolution)

    return StreamingResponse(
        generate_sse_events(epic, ls_resolution, auth_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
