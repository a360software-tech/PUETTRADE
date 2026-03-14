import asyncio
import json
import logging
from typing import Annotated

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
from shared.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-data", tags=["market-data-stream"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_streaming_tokens(auth_service: AuthServiceDep) -> StreamingTokensResponse:
    return await auth_service.get_session_tokens()


async def generate_sse_events(
    epic: str,
    resolution: str,
    auth_service: AuthService,
):
    try:
        tokens = await auth_service.get_session_tokens()
        
        credentials = LightstreamerCredentials(
            account_id=tokens.account_id,
            cst=tokens.cst,
            x_security_token=tokens.x_security_token,
            endpoint="https://demo-apd.marketdatasystems.com",
        )
        
        await lightstreamer_gateway.connect(credentials)
        
        queue: asyncio.Queue[CandleUpdate | None] = asyncio.Queue()
        
        async def callback(update: CandleUpdate):
            await queue.put(update)
        
        await lightstreamer_gateway.subscribe_to_candles(
            epic=epic,
            resolution=resolution,
            callback=callback
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
        try:
            await lightstreamer_gateway.unsubscribe(epic)
        except Exception:
            pass


@router.get("/{epic}/stream")
async def stream_candles(
    epic: str,
    resolution: Resolution = Query(default="MINUTE"),
    auth_service: AuthServiceDep = AuthServiceDep,
    settings: SettingsDep = SettingsDep,
):
    resolution_map = {
        "MINUTE": "1MINUTE",
        "MINUTE_2": "2MINUTE",
        "MINUTE_3": "3MINUTE",
        "MINUTE_5": "5MINUTE",
        "MINUTE_10": "10MINUTE",
        "MINUTE_15": "15MINUTE",
        "MINUTE_30": "30MINUTE",
        "HOUR": "1HOUR",
        "HOUR_2": "2HOUR",
        "HOUR_3": "3HOUR",
        "HOUR_4": "4HOUR",
        "DAY": "1DAY",
    }
    
    ls_resolution = resolution_map.get(resolution, "1MINUTE")
    
    return StreamingResponse(
        generate_sse_events(epic, ls_resolution, auth_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
