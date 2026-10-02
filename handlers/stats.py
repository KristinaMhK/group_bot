from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database import (
    get_user_messages, get_top_users_period,
    get_messages_count_period, get_new_members_count, get_user_info
)

router = Router()

# Титулы для топа
TITLES = {
    1: "👑 Король",
    2: "🥈 Вице-король",
    3: "🥉 Принц",
    4: "⭐ Рыцарь",
    5: "⭐ Рыцарь",
}


def get_title(rank: int) -> str:
    return TITLES.get(rank, "💬 Участник")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    chat_id = message.chat.id

    msgs_today = await get_messages_count_period(chat_id, 1)
    msgs_week = await get_messages_count_period(chat_id, 7)
    new_month = await get_new_members_count(chat_id, 30)
    user_msgs = await get_user_messages(message.from_user.id, chat_id)

    text = (
        f"📊 *Статистика группы*\n\n"
        f"💬 Сообщений сегодня: `{msgs_today}`\n"
        f"💬 Сообщений за 7 дней: `{msgs_week}`\n"
        f"👥 Новых участников за месяц: `{new_month}`\n"
        f"📝 Твоих сообщений всего: `{user_msgs}`\n\n"
        f"Используй /top чтобы увидеть самых активных!"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("top"))
async def cmd_top(message: Message):
    chat_id = message.chat.id

    top_day = await get_top_users_period(chat_id, 1, 5)
    top_week = await get_top_users_period(chat_id, 7, 5)
    top_month = await get_top_users_period(chat_id, 30, 5)

    async def format_top(users, title: str) -> str:
        if not users:
            return f"*{title}*\nПока нет данных"
        lines = [f"*{title}*"]
        for i, (uid, count) in enumerate(users, 1):
            info = await get_user_info(uid)
            name = info["first_name"] if info else "Неизвестный"
            title_emoji = get_title(i)
            lines.append(f"{i}. {title_emoji} {name} — `{count}` сообщ.")
        return "\n".join(lines)

    text = "🏆 *Топ активных*\n\n"
    text += await format_top(top_day, "📅 За сегодня:")
    text += "\n\n"
    text += await format_top(top_week, "📆 За неделю:")
    text += "\n\n"
    text += await format_top(top_month, "🗓 За месяц:")

    await message.answer(text, parse_mode="Markdown")
    