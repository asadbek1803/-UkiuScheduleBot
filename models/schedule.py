from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from db_utils.tortoise import get_db


@dataclass
class Schedule:
    id: int = 0
    user_id: int = 0
    week_id: str = ""
    day: str = ""
    pair_number: int = 0
    subject: str = ""
    teacher: Optional[str] = None
    room: Optional[str] = None
    lesson_type: Optional[str] = None
    lesson_time: str = ""
    cached_at: Optional[datetime] = None


def _row_to_schedule(row) -> Schedule:
    return Schedule(
        id=row["id"],
        user_id=row["user_id"],
        week_id=row["week_id"],
        day=row["day"],
        pair_number=row["pair_number"],
        subject=row["subject"],
        teacher=row["teacher"],
        room=row["room"],
        lesson_type=row["lesson_type"],
        lesson_time=row["lesson_time"],
        cached_at=row["cached_at"],
    )


async def get_user_id_by_telegram(tid: int) -> Optional[int]:
    db = get_db()
    cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (tid,))
    row = await cursor.fetchone()
    return row["id"] if row else None


async def get_cached_schedules(tid: int, week_id: str) -> Optional[list[Schedule]]:
    uid = await get_user_id_by_telegram(tid)
    if not uid:
        return None
    db = get_db()
    cursor = await db.execute(
        "SELECT * FROM schedules WHERE user_id = ? AND week_id = ? ORDER BY pair_number",
        (uid, week_id),
    )
    rows = await cursor.fetchall()
    if not rows:
        return None
    return [_row_to_schedule(r) for r in rows]


async def delete_cached_schedules(tid: int, week_id: str) -> None:
    uid = await get_user_id_by_telegram(tid)
    if not uid:
        return
    db = get_db()
    await db.execute(
        "DELETE FROM schedules WHERE user_id = ? AND week_id = ?",
        (uid, week_id),
    )
    await db.commit()


async def create_schedule(tid: int, week_id: str, data: dict) -> Schedule:
    uid = await get_user_id_by_telegram(tid)
    if not uid:
        raise ValueError(f"User with telegram_id={tid} not found")
    db = get_db()
    cursor = await db.execute(
        """INSERT INTO schedules
           (user_id, week_id, day, pair_number, subject, teacher, room, lesson_type, lesson_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            uid,
            week_id,
            data.get("day", ""),
            data.get("pair_number", 0),
            data.get("subject", ""),
            data.get("teacher"),
            data.get("room"),
            data.get("lesson_type"),
            data.get("lesson_time", ""),
        ),
    )
    await db.commit()
    sid = cursor.lastrowid
    cursor2 = await db.execute("SELECT * FROM schedules WHERE id = ?", (sid,))
    row = await cursor2.fetchone()
    return _row_to_schedule(row)


async def delete_old_schedules(cutoff: datetime) -> int:
    db = get_db()
    cursor = await db.execute(
        "DELETE FROM schedules WHERE cached_at < ?", (cutoff.isoformat(),)
    )
    await db.commit()
    return cursor.rowcount


async def delete_all_schedules() -> None:
    db = get_db()
    await db.execute("DELETE FROM schedules")
    await db.commit()
