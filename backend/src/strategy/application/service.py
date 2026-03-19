from shared.errors.base import ApplicationError
from market_data.application.dto import Resolution
from strategy.application.dto import StrategyEvaluateRequest, StrategyEvaluationResponse
from strategy.application.sources import StreamBufferStrategyCandleSource, StrategyCandleSource
from strategy.domain.indicators import build_indicator_snapshots
from strategy.domain.models import IndicatorSnapshot, StrategyManifest, StrategySignal, TriggerRule


class StrategyService:
    def __init__(self, candle_source: StrategyCandleSource | None = None) -> None:
        self._candle_source = candle_source or StreamBufferStrategyCandleSource()

    def evaluate(self, request: StrategyEvaluateRequest) -> StrategyEvaluationResponse:
        if len(request.candles) < 5:
            raise ApplicationError("Strategy evaluation requires at least 5 candles")

        closes = [candle.close for candle in request.candles]
        snapshots = build_indicator_snapshots(closes, request.manifest.indicators)
        latest = snapshots[-1]
        previous = snapshots[-2] if len(snapshots) > 1 else None
        signal = _evaluate_triggers(request, latest, previous)

        return StrategyEvaluationResponse(
            epic=request.epic,
            resolution=request.resolution,
            manifest_name=request.manifest.name,
            source="manual",
            status="ok",
            candles_analyzed=len(request.candles),
            latest_indicators=_to_snapshot(latest),
            previous_indicators=None if previous is None else _to_snapshot(previous),
            signal=signal,
        )

    def evaluate_live(
        self,
        epic: str,
        resolution: Resolution,
        limit: int = 100,
        manifest: StrategyManifest | None = None,
    ) -> StrategyEvaluationResponse:
        selected_manifest = manifest or StrategyManifest()
        candles = self._candle_source.get_candles(epic=epic, resolution=resolution, limit=limit)

        if len(candles) < 5:
            return StrategyEvaluationResponse(
                epic=epic,
                resolution=resolution,
                manifest_name=selected_manifest.name,
                source="stream_buffer",
                status="insufficient_candles",
                detail="Not enough completed candles in the live buffer to evaluate the strategy",
                candles_analyzed=len(candles),
                latest_indicators=None,
                previous_indicators=None,
                signal=None,
            )

        request = StrategyEvaluateRequest(
            epic=epic,
            resolution=resolution,
            candles=candles,
            manifest=selected_manifest,
        )
        response = self.evaluate(request)
        response.source = "stream_buffer"
        response.detail = None if response.signal is not None else "No trigger matched the current live candle series"
        return response


def get_strategy_service() -> StrategyService:
    return StrategyService()


def _evaluate_triggers(
    request: StrategyEvaluateRequest,
    latest: dict[str, float | None],
    previous: dict[str, float | None] | None,
) -> StrategySignal | None:
    if previous is None:
        return None

    for rule in request.manifest.triggers:
        phase = _match_rule(rule, latest, previous)
        if phase is None:
            continue

        latest_candle = request.candles[-1]
        return StrategySignal(
            side=rule.action,
            price=latest_candle.close,
            time=latest_candle.time,
            momentum=latest.get("rsi"),
            phase=phase,
            reason=rule.condition,
        )

    return None


def _match_rule(
    rule: TriggerRule,
    latest: dict[str, float | None],
    previous: dict[str, float | None],
) -> str | None:
    condition = rule.condition.strip().upper()

    if condition == "EMA_CROSS_UP":
        prev_fast = previous.get("fast_ema")
        prev_slow = previous.get("slow_ema")
        latest_fast = latest.get("fast_ema")
        latest_slow = latest.get("slow_ema")
        if _are_numbers(prev_fast, prev_slow, latest_fast, latest_slow):
            if prev_fast < prev_slow and latest_fast > latest_slow:
                return "EMA_CROSS_BULL"
        return None

    if condition == "EMA_CROSS_DOWN":
        prev_fast = previous.get("fast_ema")
        prev_slow = previous.get("slow_ema")
        latest_fast = latest.get("fast_ema")
        latest_slow = latest.get("slow_ema")
        if _are_numbers(prev_fast, prev_slow, latest_fast, latest_slow):
            if prev_fast > prev_slow and latest_fast < latest_slow:
                return "EMA_CROSS_BEAR"
        return None

    if condition.startswith("RSI <"):
        rsi = latest.get("rsi")
        threshold = _parse_threshold(condition, "<")
        if rsi is not None and rsi < threshold:
            return "RSI_OVERSOLD"
        return None

    if condition.startswith("RSI >"):
        rsi = latest.get("rsi")
        threshold = _parse_threshold(condition, ">")
        if rsi is not None and rsi > threshold:
            return "RSI_OVERBOUGHT"
        return None

    return None


def _to_snapshot(values: dict[str, float | None]) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        close=values.get("close") or 0.0,
        fast_ema=values.get("fast_ema"),
        slow_ema=values.get("slow_ema"),
        rsi=values.get("rsi"),
    )


def _parse_threshold(condition: str, operator: str) -> float:
    return float(condition.split(operator, maxsplit=1)[1].strip())


def _are_numbers(*values: float | None) -> bool:
    return all(isinstance(value, (int, float)) for value in values)
