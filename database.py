import os
import asyncpg
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db_connection():
    """Создает подключение к PostgreSQL"""
    return await asyncpg.connect(DATABASE_URL)


async def init_db():
    """Создаёт таблицы в PostgreSQL при первом запуске"""
    conn = await get_db_connection()
    try:
        # Таблица пользователей ( BIGINT используется для Telegram ID )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TEXT
            )
        """)
        # Лог сообщений
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                chat_id BIGINT,
                timestamp TEXT
            )
        """)
        # Лог вступлений в группу
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS new_members (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT,
                user_id BIGINT,
                join_date TEXT
            )
        """)
    finally:
        await conn.close()


async def add_user(user_id: int, username: str, first_name: str):
    conn = await get_db_connection()
    try:
        await conn.execute("""
            INSERT INTO users (user_id, username, first_name, join_date)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE 
            SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
        """, user_id, username, first_name, datetime.now().isoformat())
    finally:
        await conn.close()


async def update_user_info(user_id: int, username: str, first_name: str):
    await add_user(user_id, username, first_name)


async def log_message(user_id: int, chat_id: int):
    conn = await get_db_connection()
    try:
        await conn.execute("""
            INSERT INTO message_log (user_id, chat_id, timestamp) 
            VALUES ($1, $2, $3)
        """, user_id, chat_id, datetime.now().isoformat())
    finally:
        await conn.close()


async def log_new_member(chat_id: int, user_id: int):
    conn = await get_db_connection()
    try:
        await conn.execute("""
            INSERT INTO new_members (chat_id, user_id, join_date) 
            VALUES ($1, $2, $3)
        """, chat_id, user_id, datetime.now().isoformat())
    finally:
        await conn.close()


async def get_user_messages(user_id: int, chat_id: int) -> int:
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            SELECT COUNT(*) FROM message_log 
            WHERE user_id = $1 AND chat_id = $2
        """, user_id, chat_id)
        return row[0] if row else 0
    finally:
        await conn.close()


async def get_top_users_period(chat_id: int, days: int, limit: int = 10):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT user_id, COUNT(*) as cnt FROM message_log
            WHERE chat_id = $1 AND timestamp > $2
            GROUP BY user_id ORDER BY cnt DESC LIMIT $3
        """, chat_id, since, limit)
        return [(r['user_id'], r['cnt']) for r in rows]
    finally:
        await conn.close()


async def get_messages_count_period(chat_id: int, days: int) -> int:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            SELECT COUNT(*) FROM message_log 
            WHERE chat_id = $1 AND timestamp > $2
        """, chat_id, since)
        return row[0] if row else 0
    finally:
        await conn.close()


async def get_new_members_count(chat_id: int, days: int = 30) -> int:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            SELECT COUNT(*) FROM new_members 
            WHERE chat_id = $1 AND join_date > $2
        """, chat_id, since)
        return row[0] if row else 0
    finally:
        await conn.close()


async def get_all_chat_users(chat_id: int):
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT u.user_id, u.username, u.first_name
            FROM users u
            WHERE u.user_id IN (
                SELECT user_id FROM message_log WHERE chat_id = $1
                UNION
                SELECT user_id FROM new_members WHERE chat_id = $2
            )
        """, chat_id, chat_id)
        return [{"user_id": r['user_id'], "username": r['username'], "first_name": r['first_name']} for r in rows]
    finally:
        await conn.close()


async def get_user_info(user_id: int):
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            SELECT username, first_name FROM users WHERE user_id = $1
        """, user_id)
        if row:
            return {"username": row['username'], "first_name": row['first_name']}
        return None
    finally:
        await conn.close()
        #КОНЕЦ
