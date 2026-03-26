from sqlalchemy import create_engine, text
from src.shared.config.settings import get_settings
settings = get_settings()
engine = create_engine(settings.database_url.replace('postgres://', 'postgresql://'), future=True)
with engine.begin() as conn:
    conn.execute(text('DELETE FROM candles;'))
    conn.execute(text('DELETE FROM candle_sync_state;'))
print('Base de datos depurada!')
