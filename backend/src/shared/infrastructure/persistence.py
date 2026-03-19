import json
import sqlite3
from pathlib import Path

from shared.config.settings import Settings, get_settings


class SQLitePersistence:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def load_positions(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM positions ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_position(self, position_id: str, payload: dict[str, object], status: str, epic: str, execution_mode: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO positions (id, status, epic, execution_mode, payload)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    epic = excluded.epic,
                    execution_mode = excluded.execution_mode,
                    payload = excluded.payload
                """,
                (position_id, status, epic, execution_mode, json.dumps(payload)),
            )
            connection.commit()

    def clear_positions(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM positions")
            connection.commit()

    def load_engine_state(self) -> tuple[str, list[dict[str, object]]]:
        with self._connect() as connection:
            mode_row = connection.execute("SELECT payload FROM engine_meta WHERE key = 'mode'").fetchone()
            state_rows = connection.execute("SELECT payload FROM engine_epics ORDER BY epic").fetchall()

        mode = "STOPPED"
        if mode_row is not None:
            mode = str(json.loads(mode_row[0]).get("mode", mode))
        states = [json.loads(row[0]) for row in state_rows]
        return mode, states

    def save_engine_mode(self, mode: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO engine_meta (key, payload)
                VALUES ('mode', ?)
                ON CONFLICT(key) DO UPDATE SET payload = excluded.payload
                """,
                (json.dumps({"mode": mode}),),
            )
            connection.commit()

    def save_engine_epic(self, epic: str, payload: dict[str, object]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO engine_epics (epic, payload)
                VALUES (?, ?)
                ON CONFLICT(epic) DO UPDATE SET payload = excluded.payload
                """,
                (epic, json.dumps(payload)),
            )
            connection.commit()

    def clear_engine_state(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM engine_meta")
            connection.execute("DELETE FROM engine_epics")
            connection.commit()

    def append_execution_event(
        self,
        *,
        epic: str,
        position_id: str | None,
        execution_mode: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO execution_events (epic, position_id, execution_mode, event_type, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (epic, position_id, execution_mode, event_type, json.dumps(payload)),
            )
            connection.commit()

    def load_execution_events(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT epic, position_id, execution_mode, event_type, payload FROM execution_events ORDER BY id"
            ).fetchall()
        events: list[dict[str, object]] = []
        for epic, position_id, execution_mode, event_type, payload in rows:
            event_payload = json.loads(payload)
            event_payload.update(
                {
                    "epic": epic,
                    "position_id": position_id,
                    "execution_mode": execution_mode,
                    "event_type": event_type,
                }
            )
            events.append(event_payload)
        return events

    def clear_execution_events(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM execution_events")
            connection.commit()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    epic TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS engine_meta (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS engine_epics (
                    epic TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epic TEXT NOT NULL,
                    position_id TEXT,
                    execution_mode TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)


def resolve_sqlite_path(settings: Settings) -> Path:
    database_url = settings.database_url.strip()
    if database_url.startswith("sqlite:///"):
        return Path(database_url.removeprefix("sqlite:///"))
    return Path(__file__).resolve().parents[3] / ".runtime" / "trading-platform.sqlite3"


_persistence: SQLitePersistence | None = None


def get_persistence() -> SQLitePersistence:
    global _persistence
    if _persistence is None:
        _persistence = SQLitePersistence(resolve_sqlite_path(get_settings()))
    return _persistence
