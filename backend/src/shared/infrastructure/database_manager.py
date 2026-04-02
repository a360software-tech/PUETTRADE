from shared.infrastructure.persistence import DatabasePersistence, get_persistence


DatabaseManager = DatabasePersistence


def get_database_manager() -> DatabaseManager:
    return get_persistence()
