from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from db_utils.tortoise import get_db


@dataclass
class User:
    id: int = 0
    telegram_id: int = 0
    username: Optional[str] = None
    full_name: Optional[str] = None
    language: str = "uz"
    hemis_login: Optional[str] = None
    hemis_password: Optional[str] = None
    group_name: Optional[str] = None
    reminder_enabled: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def _row_to_user(row) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        username=row["username"],
        full_name=row["full_name"],
        language=row["language"],
        hemis_login=row["hemis_login"],
        hemis_password=row["hemis_password"],
        group_name=row["group_name"],
        reminder_enabled=bool(row["reminder_enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_user(tid: int) -> Optional[User]:
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (tid,)
    )
    row = await cursor.fetchone()
    return _row_to_user(row) if row else None


async def get_or_create_user(tid: int, defaults: Optional[dict] = None) -> tuple[User, bool]:
    user = await get_user(tid)
    if user:
        return user, False
    username = (defaults or {}).get("username")
    full_name = (defaults or {}).get("full_name")
    db = get_db()
    cursor = await db.execute(
        "INSERT INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
        (tid, username, full_name),
    )
    await db.commit()
    user = await get_user(tid)
    return user, True


async def update_user(tid: int, **kwargs) -> None:
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [tid]
    db = get_db()
    await db.execute(
        f"UPDATE users SET updated_at = CURRENT_TIMESTAMP, {sets} WHERE telegram_id = ?",
        vals,
    )
    await db.commit()


async def count_users() -> int:
    db = get_db()
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM users")
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


async def count_connected_users() -> int:
    db = get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE hemis_login IS NOT NULL"
    )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


async def count_reminder_users() -> int:
    db = get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE reminder_enabled = 1"
    )
    row = await cursor.fetchone()
    return row["cnt"] if row else 0


async def get_all_users(limit: int = 0) -> list[User]:
    db = get_db()
    query = "SELECT * FROM users ORDER BY id"
    if limit > 0:
        query += f" LIMIT {limit}"
    cursor = await db.execute(query)
    rows = await cursor.fetchall()
    return [_row_to_user(r) for r in rows]


async def get_all_telegram_ids() -> list[int]:
    db = get_db()
    cursor = await db.execute("SELECT telegram_id FROM users")
    rows = await cursor.fetchall()
    return [r["telegram_id"] for r in rows]


async def get_reminder_users() -> list[User]:
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM users WHERE reminder_enabled = 1 AND hemis_login IS NOT NULL"
    )
    rows = await cursor.fetchall()
    return [_row_to_user(r) for r in rows]


async def delete_all_users() -> int:
    db = get_db()
    cursor = await db.execute("DELETE FROM users")
    await db.commit()
    return cursor.rowcount
