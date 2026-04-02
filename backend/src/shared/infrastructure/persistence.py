import json
import logging
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, Index, Integer, MetaData, Numeric, PrimaryKeyConstraint, String, Table, Text, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from shared.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


metadata = MetaData()

positions_table = Table(
    "positions",
    metadata,
    Column("id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("epic", String, nullable=False),
    Column("execution_mode", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
Index("idx_positions_status_epic_mode", positions_table.c.status, positions_table.c.epic, positions_table.c.execution_mode)

engine_meta_table = Table(
    "engine_meta",
    metadata,
    Column("key", String, primary_key=True),
    Column("payload", JSON, nullable=False),
)

engine_epics_table = Table(
    "engine_epics",
    metadata,
    Column("epic", String, primary_key=True),
    Column("payload", JSON, nullable=False),
)

execution_events_table = Table(
    "execution_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("epic", String, nullable=False),
    Column("position_id", String),
    Column("execution_mode", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("payload", JSON, nullable=False),
)
Index("idx_execution_events_position_event", execution_events_table.c.position_id, execution_events_table.c.epic, execution_events_table.c.event_type)

candles_table = Table(
    "candles",
    metadata,
    Column("epic", String, nullable=False),
    Column("resolution", String, nullable=False),
    Column("time", String, nullable=False),
    Column("open", Numeric(18, 8), nullable=False),
    Column("high", Numeric(18, 8), nullable=False),
    Column("low", Numeric(18, 8), nullable=False),
    Column("close", Numeric(18, 8), nullable=False),
    Column("volume", Numeric(18, 8), nullable=False),
    PrimaryKeyConstraint("epic", "resolution", "time"),
)
Index("idx_candles_epic_resolution_time", candles_table.c.epic, candles_table.c.resolution, candles_table.c.time.desc())

candle_sync_state_table = Table(
    "candle_sync_state",
    metadata,
    Column("epic", String, nullable=False),
    Column("resolution", String, nullable=False),
    Column("status", String, nullable=False),
    Column("last_synced_at", String, nullable=False),
    Column("last_candle_time", String),
    Column("source", String, nullable=False),
    PrimaryKeyConstraint("epic", "resolution"),
)


class DatabasePersistence:
    def __init__(self, database_path: Path | str, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._database_url = _normalize_database_url(database_path)
        self._engine = create_engine(self._database_url, future=True, **_build_engine_options(self._database_url, self._settings))
        should_auto_create = settings is None or self._settings.database_auto_create_schema
        if should_auto_create:
            self._initialize()

    @property
    def engine(self) -> Engine:
        return self._engine

    def load_positions(self) -> list[dict[str, object]]:
        with self._engine.begin() as connection:
            rows = connection.execute(text("SELECT payload FROM positions ORDER BY id")).mappings().all()
        return [_decode_json_payload(row["payload"]) for row in rows]

    def save_position(self, position_id: str, payload: dict[str, object], status: str, epic: str, execution_mode: str) -> None:
        self._execute(
            """
            INSERT INTO positions (id, status, epic, execution_mode, payload)
            VALUES (:id, :status, :epic, :execution_mode, :payload)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                epic = excluded.epic,
                execution_mode = excluded.execution_mode,
                payload = excluded.payload
            """,
            {
                "id": position_id,
                "status": status,
                "epic": epic,
                "execution_mode": execution_mode,
                "payload": _encode_json_payload(payload),
            },
        )

    def clear_positions(self) -> None:
        self._execute("DELETE FROM positions")

    def load_engine_state(self) -> tuple[str, list[dict[str, object]]]:
        with self._engine.begin() as connection:
            mode_row = connection.execute(text("SELECT payload FROM engine_meta WHERE key = 'mode'" )).mappings().first()
            state_rows = connection.execute(text("SELECT payload FROM engine_epics ORDER BY epic")).mappings().all()
        mode = "STOPPED"
        if mode_row is not None:
            mode = str(_decode_json_payload(mode_row["payload"]).get("mode", mode))
        return mode, [_decode_json_payload(row["payload"]) for row in state_rows]

    def save_engine_mode(self, mode: str) -> None:
        self._execute(
            """
            INSERT INTO engine_meta (key, payload)
            VALUES ('mode', :payload)
            ON CONFLICT(key) DO UPDATE SET payload = excluded.payload
            """,
            {"payload": _encode_json_payload({"mode": mode})},
        )

    def save_engine_epic(self, epic: str, payload: dict[str, object]) -> None:
        self._execute(
            """
            INSERT INTO engine_epics (epic, payload)
            VALUES (:epic, :payload)
            ON CONFLICT(epic) DO UPDATE SET payload = excluded.payload
            """,
            {"epic": epic, "payload": _encode_json_payload(payload)},
        )

    def clear_engine_state(self) -> None:
        self._execute("DELETE FROM engine_meta")
        self._execute("DELETE FROM engine_epics")

    def append_execution_event(
        self,
        *,
        epic: str,
        position_id: str | None,
        execution_mode: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        self._execute(
            """
            INSERT INTO execution_events (epic, position_id, execution_mode, event_type, payload)
            VALUES (:epic, :position_id, :execution_mode, :event_type, :payload)
            """,
            {
                "epic": epic,
                "position_id": position_id,
                "execution_mode": execution_mode,
                "event_type": event_type,
                "payload": _encode_json_payload(payload),
            },
        )

    def load_execution_events(self) -> list[dict[str, object]]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                text("SELECT epic, position_id, execution_mode, event_type, payload FROM execution_events ORDER BY id")
            ).mappings().all()
        events: list[dict[str, object]] = []
        for row in rows:
            event_payload = _decode_json_payload(row["payload"])
            event_payload.update(
                {
                    "epic": row["epic"],
                    "position_id": row["position_id"],
                    "execution_mode": row["execution_mode"],
                    "event_type": row["event_type"],
                }
            )
            events.append(event_payload)
        return events

    def upsert_candle(
        self,
        *,
        epic: str,
        resolution: str,
        time: str,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
    ) -> None:
        self._execute(
            """
            INSERT INTO candles (epic, resolution, time, open, high, low, close, volume)
            VALUES (:epic, :resolution, :time, :open, :high, :low, :close, :volume)
            ON CONFLICT(epic, resolution, time) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume
            """,
            {
                "epic": epic,
                "resolution": resolution,
                "time": time,
                "open": _decimal_value(open_price),
                "high": _decimal_value(high),
                "low": _decimal_value(low),
                "close": _decimal_value(close),
                "volume": _decimal_value(volume),
            },
        )

    def load_candles(
        self,
        *,
        epic: str,
        resolution: str,
        limit: int = 200,
        from_time: str | None = None,
        to_time: str | None = None,
    ) -> list[dict[str, object]]:
        query = "SELECT epic, resolution, time, open, high, low, close, volume FROM candles WHERE epic = :epic AND resolution = :resolution"
        params: dict[str, object] = {"epic": epic, "resolution": resolution, "limit": limit}
        if from_time is not None:
            query += " AND time >= :from_time"
            params["from_time"] = from_time
        if to_time is not None:
            query += " AND time <= :to_time"
            params["to_time"] = to_time
        query += " ORDER BY time DESC LIMIT :limit"

        with self._engine.begin() as connection:
            rows = connection.execute(text(query), params).mappings().all()
        return [dict(row) for row in reversed(rows)]

    def get_latest_candle_time(self, *, epic: str, resolution: str) -> str | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT time FROM candles WHERE epic = :epic AND resolution = :resolution ORDER BY time DESC LIMIT 1"
                ),
                {"epic": epic, "resolution": resolution},
            ).mappings().first()
        return None if row is None else str(row["time"])

    def save_candle_sync_state(
        self,
        *,
        epic: str,
        resolution: str,
        status: str,
        last_synced_at: str,
        last_candle_time: str | None,
        source: str,
    ) -> None:
        self._execute(
            """
            INSERT INTO candle_sync_state (epic, resolution, status, last_synced_at, last_candle_time, source)
            VALUES (:epic, :resolution, :status, :last_synced_at, :last_candle_time, :source)
            ON CONFLICT(epic, resolution) DO UPDATE SET
                status = excluded.status,
                last_synced_at = excluded.last_synced_at,
                last_candle_time = excluded.last_candle_time,
                source = excluded.source
            """,
            {
                "epic": epic,
                "resolution": resolution,
                "status": status,
                "last_synced_at": last_synced_at,
                "last_candle_time": last_candle_time,
                "source": source,
            },
        )

    def load_candle_sync_state(self, *, epic: str, resolution: str) -> dict[str, object] | None:
        with self._engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT epic, resolution, status, last_synced_at, last_candle_time, source FROM candle_sync_state WHERE epic = :epic AND resolution = :resolution"
                ),
                {"epic": epic, "resolution": resolution},
            ).mappings().first()
        return None if row is None else dict(row)

    def clear_candles(self) -> None:
        self._execute("DELETE FROM candles")
        self._execute("DELETE FROM candle_sync_state")

    def clear_execution_events(self) -> None:
        self._execute("DELETE FROM execution_events")

    def _initialize(self) -> None:
        metadata.create_all(self._engine)

    def _execute(self, statement: str, params: dict[str, object] | None = None) -> None:
        with self._engine.begin() as connection:
            connection.execute(text(statement), params or {})


def resolve_database_target(settings: Settings) -> str | Path:
    if _is_pytest_runtime():
        return Path(__file__).resolve().parents[3] / ".runtime" / "test-trading-platform.sqlite3"

    database_url = settings.database_url.strip()
    if database_url:
        return database_url
    return Path(__file__).resolve().parents[3] / ".runtime" / "trading-platform.sqlite3"


def _normalize_database_url(database_target: Path | str) -> str:
    if isinstance(database_target, Path):
        database_target.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{database_target.as_posix()}"

    target = database_target.strip()
    if target.startswith("postgres://"):
        target = "postgresql://" + target.removeprefix("postgres://")
    if target.startswith("sqlite:///"):
        path = Path(target.removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)
        return target
    return target


def _build_engine_options(database_url: str, settings: Settings) -> dict[str, Any]:
    options: dict[str, Any] = {"echo": settings.database_echo}
    if database_url.startswith("sqlite:///"):
        options["connect_args"] = {"check_same_thread": False}
        options["poolclass"] = NullPool
        return options

    options.update(
        {
            "pool_pre_ping": True,
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_timeout": settings.database_pool_timeout_seconds,
            "pool_recycle": settings.database_pool_recycle_seconds,
        }
    )
    return options


def _encode_json_payload(payload: dict[str, object]) -> dict[str, object] | str:
    return payload


def _decode_json_payload(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    raise TypeError(f"Unsupported JSON payload type: {type(payload)!r}")


def _decimal_value(value: float) -> float:
    return float(value)


_persistence: DatabasePersistence | None = None


def get_persistence() -> DatabasePersistence:
    global _persistence
    if _persistence is None:
        settings = get_settings()
        target = resolve_database_target(settings)
        try:
            _persistence = DatabasePersistence(target, settings)
        except Exception as exc:
            if not _is_pytest_runtime():
                raise RuntimeError(
                    f"Failed to initialize persistence using DATABASE_URL '{settings.database_url}'."
                ) from exc

            fallback_path = Path(__file__).resolve().parents[3] / ".runtime" / "test-trading-platform.sqlite3"
            logger.warning(
                "Persistence failed for DATABASE_URL '%s' during tests; falling back to SQLite at %s. Error: %s",
                settings.database_url,
                fallback_path,
                exc,
            )
            _persistence = DatabasePersistence(fallback_path, settings)
    return _persistence


def _is_pytest_runtime() -> bool:
    return "pytest" in sys.modules
