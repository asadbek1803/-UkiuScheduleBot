from pathlib import Path

import aiosqlite

_connection: aiosqlite.Connection | None = None


async def init_db():
    global _connection
    root_dir = Path(__file__).parent.parent
    db_path = root_dir / "kiuf_bot.db"

    _connection = await aiosqlite.connect(str(db_path))
    _connection.row_factory = aiosqlite.Row

    await _connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id     INTEGER UNIQUE NOT NULL,
            username        TEXT,
            full_name       TEXT,
            language        TEXT DEFAULT 'uz',
            hemis_login     TEXT,
            hemis_password  TEXT,
            group_name      TEXT,
            reminder_enabled INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_telegram_id
            ON users(telegram_id);

        CREATE TABLE IF NOT EXISTS schedules (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            week_id      TEXT NOT NULL,
            day          TEXT NOT NULL,
            pair_number  INTEGER DEFAULT 0,
            subject      TEXT DEFAULT '',
            teacher      TEXT,
            room         TEXT,
            lesson_type  TEXT,
            lesson_time  TEXT DEFAULT '',
            cached_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_schedules_user_week
            ON schedules(user_id, week_id);
    """)
    await _connection.commit()


async def close_db():
    global _connection
    if _connection:
        await _connection.close()
        _connection = None


def get_db() -> aiosqlite.Connection | None:
    return _connection
