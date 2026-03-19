from strategy.domain.models import IndicatorConfig


def calculate_ema(values: list[float], period: int) -> list[float | None]:
    ema_values: list[float | None] = []
    multiplier = 2 / (period + 1)
    ema: float | None = None

    for index, value in enumerate(values):
        if index + 1 < period:
            ema_values.append(None)
            continue

        if ema is None:
            ema = sum(values[index + 1 - period:index + 1]) / period
        else:
            ema = ((value - ema) * multiplier) + ema

        ema_values.append(ema)

    return ema_values


def calculate_rsi(values: list[float], period: int) -> list[float | None]:
    if len(values) < 2:
        return [None for _ in values]

    gains: list[float] = []
    losses: list[float] = []
    output: list[float | None] = [None]

    avg_gain: float | None = None
    avg_loss: float | None = None

    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

        if index < period:
            output.append(None)
            continue

        if avg_gain is None or avg_loss is None:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
        else:
            avg_gain = ((avg_gain * (period - 1)) + gains[-1]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[-1]) / period

        if avg_loss == 0:
            output.append(100.0)
            continue

        rs = avg_gain / avg_loss
        output.append(100 - (100 / (1 + rs)))

    return output


def build_indicator_snapshots(closes: list[float], config: IndicatorConfig) -> list[dict[str, float | None]]:
    fast_ema = calculate_ema(closes, config.fast_ema)
    slow_ema = calculate_ema(closes, config.slow_ema)
    rsi = calculate_rsi(closes, config.rsi_period)

    snapshots: list[dict[str, float | None]] = []
    for index, close in enumerate(closes):
        snapshots.append(
            {
                "close": close,
                "fast_ema": fast_ema[index],
                "slow_ema": slow_ema[index],
                "rsi": rsi[index],
            }
        )
    return snapshots
