import json
import logging
import sys
from pathlib import Path

from sqlalchemy import Column, Index, Integer, MetaData, PrimaryKeyConstraint, String, Table, Text, create_engine, text
from sqlalchemy.engine import Engine

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
    Column("payload", Text, nullable=False),
)
Index("idx_positions_status_epic_mode", positions_table.c.status, positions_table.c.epic, positions_table.c.execution_mode)

engine_meta_table = Table(
    "engine_meta",
    metadata,
    Column("key", String, primary_key=True),
    Column("payload", Text, nullable=False),
)

engine_epics_table = Table(
    "engine_epics",
    metadata,
    Column("epic", String, primary_key=True),
    Column("payload", Text, nullable=False),
)

execution_events_table = Table(
    "execution_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("epic", String, nullable=False),
    Column("position_id", String),
    Column("execution_mode", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("payload", Text, nullable=False),
)
Index("idx_execution_events_position_event", execution_events_table.c.position_id, execution_events_table.c.epic, execution_events_table.c.event_type)

candles_table = Table(
    "candles",
    metadata,
    Column("epic", String, nullable=False),
    Column("resolution", String, nullable=False),
    Column("time", String, nullable=False),
    Column("open", String, nullable=False),
    Column("high", String, nullable=False),
    Column("low", String, nullable=False),
    Column("close", String, nullable=False),
    Column("volume", String, nullable=False),
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
    def __init__(self, database_path: Path | str) -> None:
        self._database_url = _normalize_database_url(database_path)
        self._engine = create_engine(self._database_url, future=True)
        self._initialize()

    def load_positions(self) -> list[dict[str, object]]:
        with self._engine.begin() as connection:
            rows = connection.execute(text("SELECT payload FROM positions ORDER BY id")).mappings().all()
        return [json.loads(str(row["payload"])) for row in rows]

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
                "payload": json.dumps(payload),
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
            mode = str(json.loads(str(mode_row["payload"])).get("mode", mode))
        return mode, [json.loads(str(row["payload"])) for row in state_rows]

    def save_engine_mode(self, mode: str) -> None:
        self._execute(
            """
            INSERT INTO engine_meta (key, payload)
            VALUES ('mode', :payload)
            ON CONFLICT(key) DO UPDATE SET payload = excluded.payload
            """,
            {"payload": json.dumps({"mode": mode})},
        )

    def save_engine_epic(self, epic: str, payload: dict[str, object]) -> None:
        self._execute(
            """
            INSERT INTO engine_epics (epic, payload)
            VALUES (:epic, :payload)
            ON CONFLICT(epic) DO UPDATE SET payload = excluded.payload
            """,
            {"epic": epic, "payload": json.dumps(payload)},
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
                "payload": json.dumps(payload),
            },
        )

    def load_execution_events(self) -> list[dict[str, object]]:
        with self._engine.begin() as connection:
            rows = connection.execute(
                text("SELECT epic, position_id, execution_mode, event_type, payload FROM execution_events ORDER BY id")
            ).mappings().all()
        events: list[dict[str, object]] = []
        for row in rows:
            event_payload = json.loads(str(row["payload"]))
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
                "open": str(open_price),
                "high": str(high),
                "low": str(low),
                "close": str(close),
                "volume": str(volume),
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


_persistence: DatabasePersistence | None = None


def get_persistence() -> DatabasePersistence:
    global _persistence
    if _persistence is None:
        settings = get_settings()
        target = resolve_database_target(settings)
        try:
            _persistence = DatabasePersistence(target)
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
            _persistence = DatabasePersistence(fallback_path)
    return _persistence


def _is_pytest_runtime() -> bool:
    return "pytest" in sys.modules
