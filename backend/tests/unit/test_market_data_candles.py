from market_data.domain.candles import (
    BufferedCandle,
    CandleSeriesBuffer,
    CandleCloseNotifier,
    TickCandleBuilder,
    TickInput,
    supports_buffered_resolution,
    to_lightstreamer_resolution,
)


def test_resolution_maps_to_lightstreamer_format() -> None:
    assert to_lightstreamer_resolution("MINUTE_5") == "5MINUTE"
    assert to_lightstreamer_resolution("HOUR") == "1HOUR"
    assert supports_buffered_resolution("MINUTE_5") is True
    assert supports_buffered_resolution("WEEK") is False


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
    assert buffer.get_current("CS.D.EURUSD.CFD.IP", "1MINUTE") is None
    assert buffer.get_last_completed("CS.D.EURUSD.CFD.IP", "1MINUTE") is not None


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


def test_seed_completed_history_populates_buffer_and_marks_candles_complete() -> None:
    buffer = CandleSeriesBuffer(maxlen=10)

    buffer.seed_completed(
        [
            BufferedCandle(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="5MINUTE",
                time="2026-03-18T12:00:00",
                open_price=1.101,
                high=1.102,
                low=1.1,
                close=1.1015,
                volume=100.0,
                completed=False,
            ),
            BufferedCandle(
                epic="CS.D.EURUSD.CFD.IP",
                resolution="5MINUTE",
                time="2026-03-18T12:05:00",
                open_price=1.1015,
                high=1.103,
                low=1.101,
                close=1.1025,
                volume=120.0,
                completed=False,
            ),
        ]
    )

    candles = buffer.get("CS.D.EURUSD.CFD.IP", "5MINUTE")

    assert len(candles) == 2
    assert all(candle.completed for candle in candles)
    assert candles[0].time == "2026-03-18T12:00:00"
    assert candles[1].close == 1.1025


def test_buffer_exposes_current_and_completed_series_separately() -> None:
    buffer = CandleSeriesBuffer(maxlen=10)

    buffer.upsert(
        BufferedCandle(
            epic="CS.D.EURUSD.CFD.IP",
            resolution="1MINUTE",
            time="2026-03-18T12:00:00",
            open_price=1.1,
            high=1.11,
            low=1.09,
            close=1.105,
            volume=10.0,
            completed=True,
        )
    )
    buffer.upsert(
        BufferedCandle(
            epic="CS.D.EURUSD.CFD.IP",
            resolution="1MINUTE",
            time="2026-03-18T12:01:00",
            open_price=1.105,
            high=1.115,
            low=1.1,
            close=1.112,
            volume=5.0,
            completed=False,
        )
    )

    current = buffer.get_current("CS.D.EURUSD.CFD.IP", "1MINUTE")
    last_completed = buffer.get_last_completed("CS.D.EURUSD.CFD.IP", "1MINUTE")
    completed_series = buffer.get_series(
        "CS.D.EURUSD.CFD.IP",
        "1MINUTE",
        include_incomplete=False,
    )

    assert current is not None
    assert current.time == "2026-03-18T12:01:00"
    assert current.close_time == "2026-03-18T12:02:00"
    assert last_completed is not None
    assert last_completed.time == "2026-03-18T12:00:00"
    assert len(completed_series) == 1
    assert completed_series[0].completed is True


def test_tick_candle_builder_closes_candle_and_notifies_listener() -> None:
    buffer = CandleSeriesBuffer(maxlen=10)
    notifier = CandleCloseNotifier()
    builder = TickCandleBuilder(buffer=buffer, notifier=notifier, resolutions=["1MINUTE", "5MINUTE"])
    closed_events: list[BufferedCandle] = []

    listener_id = notifier.register(closed_events.append)

    first_closed = builder.update_with_tick(
        TickInput(epic="CS.D.EURUSD.CFD.IP", price=1.1, timestamp="2026-03-18T12:00:05", volume=1.0)
    )
    second_closed = builder.update_with_tick(
        TickInput(epic="CS.D.EURUSD.CFD.IP", price=1.101, timestamp="2026-03-18T12:01:05", volume=2.0)
    )

    notifier.unregister(listener_id)

    assert first_closed == []
    assert len(second_closed) == 1
    assert second_closed[0].resolution == "1MINUTE"
    assert closed_events[0].resolution == "1MINUTE"
    assert buffer.get_current("CS.D.EURUSD.CFD.IP", "1MINUTE") is not None
    assert buffer.get_last_completed("CS.D.EURUSD.CFD.IP", "1MINUTE") is not None


def test_tick_candle_builder_generates_fake_history_into_buffer() -> None:
    buffer = CandleSeriesBuffer(maxlen=200)
    builder = TickCandleBuilder(buffer=buffer, resolutions=["5MINUTE"])

    generated = builder.generate_fake_history(
        "CS.D.EURUSD.CFD.IP",
        resolution="5MINUTE",
        count=5,
        start_price=1.1,
        seed=11,
    )

    series = buffer.get_series("CS.D.EURUSD.CFD.IP", "5MINUTE", include_incomplete=False)

    assert len(generated) == 5
    assert len(series) == 5
    assert all(candle.completed for candle in series)
