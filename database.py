import aiosqlite
from datetime import datetime, timedelta

DB_PATH = "database.db"


async def init_db():
    """Создаёт таблицы при первом запуске"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                timestamp TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS new_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                join_date TEXT
            )
        """)
        await db.commit()


async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, datetime.now().isoformat())
        )
        await db.commit()


async def update_user_info(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
            (username, first_name, user_id)
        )
        await db.commit()


async def log_message(user_id: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO message_log (user_id, chat_id, timestamp) VALUES (?, ?, ?)",
            (user_id, chat_id, datetime.now().isoformat())
        )
        await db.commit()


async def log_new_member(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO new_members (chat_id, user_id, join_date) VALUES (?, ?, ?)",
            (chat_id, user_id, datetime.now().isoformat())
        )
        await db.commit()


async def get_user_messages(user_id: int, chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM message_log WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        row = await cursor.fetchone()
        return row[0]


async def get_top_users_period(chat_id: int, days: int, limit: int = 10):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, COUNT(*) as cnt FROM message_log "
            "WHERE chat_id = ? AND timestamp > ? "
            "GROUP BY user_id ORDER BY cnt DESC LIMIT ?",
            (chat_id, since, limit)
        )
        return await cursor.fetchall()


async def get_messages_count_period(chat_id: int, days: int) -> int:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM message_log WHERE chat_id = ? AND timestamp > ?",
            (chat_id, since)
        )
        row = await cursor.fetchone()
        return row[0]


async def get_new_members_count(chat_id: int, days: int = 30) -> int:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM new_members WHERE chat_id = ? AND join_date > ?",
            (chat_id, since)
        )
        row = await cursor.fetchone()
        return row[0]


async def get_all_chat_users(chat_id: int):
    """Все пользователи, которые хотя бы раз писали в чат"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT DISTINCT u.user_id, u.username, u.first_name "
            "FROM users u JOIN message_log m ON u.user_id = m.user_id "
            "WHERE m.chat_id = ?",
            (chat_id,)
        )
        rows = await cursor.fetchall()
        return [{"user_id": r[0], "username": r[1], "first_name": r[2]} for r in rows]


async def get_user_info(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username, first_name FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {"username": row[0], "first_name": row[1]}
        return None