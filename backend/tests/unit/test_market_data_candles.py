from market_data.domain.candles import BufferedCandle, CandleSeriesBuffer, to_lightstreamer_resolution


def test_resolution_maps_to_lightstreamer_format() -> None:
    assert to_lightstreamer_resolution("MINUTE_5") == "5MINUTE"
    assert to_lightstreamer_resolution("HOUR") == "1HOUR"


def test_buffer_replaces_latest_candle_with_same_timestamp() -> None:
    buffer = CandleSeriesBuffer(maxlen=10)

    buffer.upsert(
        BufferedCandle(
            epic="CS.D.EURUSD.CFD.IP",
            resolution="1MINUTE",
            time="2026-03-18T12:00:00",
            open_price=1.1,
            high=1.2,
            low=1.0,
            close=1.15,
            volume=10.0,
            completed=False,
        )
    )
    buffer.upsert(
        BufferedCandle(
            epic="CS.D.EURUSD.CFD.IP",
            resolution="1MINUTE",
            time="2026-03-18T12:00:00",
            open_price=1.1,
            high=1.25,
            low=0.99,
            close=1.22,
            volume=15.0,
            completed=True,
        )
    )

    candles = buffer.get("CS.D.EURUSD.CFD.IP", "1MINUTE")

    assert len(candles) == 1
    assert candles[0].high == 1.25
    assert candles[0].close == 1.22
    assert candles[0].completed is True


def test_buffer_derives_higher_timeframe_from_completed_minutes() -> None:
    buffer = CandleSeriesBuffer(maxlen=20)

    closes = [1.101, 1.102, 1.103, 1.104, 1.105]
    highs = [1.102, 1.103, 1.104, 1.105, 1.106]
    lows = [1.099, 1.1, 1.101, 1.102, 1.103]

    for index in range(5):
        minute = f"2026-03-18T12:0{index}:00"
        buffer.upsert(
            BufferedCandle(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="1MINUTE",
                time=minute,
                open_price=1.1 + (index * 0.001),
                high=highs[index],
                low=lows[index],
                close=closes[index],
                volume=10.0 + index,
                completed=True,
            )
        )

    candles = buffer.get("CS.D.EURUSD.CFD.IP", "5MINUTE")

    assert len(candles) == 1
    assert candles[0].time == "2026-03-18T12:00:00"
    assert candles[0].open_price == 1.1
    assert candles[0].high == 1.106
    assert candles[0].low == 1.099
    assert candles[0].close == 1.105
    assert candles[0].volume == 60.0
    assert candles[0].completed is True
