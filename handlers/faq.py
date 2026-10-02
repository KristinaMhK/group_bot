import asyncio
import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards import faq_keyboard
from database import get_all_chat_users, add_user

router = Router()

HELP_TEXT = (
    "<b>🐻 Привет! Я помощник Sib.Bear.</b>\n\n"
    "<b>Что я умею:</b>\n\n"
    "👋 Приветствую новых участников в группе.\n"
    "📢 <b>Созыв всех участников:</b> напиши <code>Где все ? [причина]</code> или <code>/all [причина]</code>\n"
    "📊 <code>/stats</code> — статистика группы.\n"
    "🏆 <code>/top</code> — рейтинг самых активных (👑 Король, 🥈 Вице-король...)\n"
    "❓ <code>/faq</code> — частые вопросы группы.\n"
    "🎮 <code>/games</code> или команды: <code>/guess_number</code>, <code>/guess_word</code>, <code>/rps</code>, <code>/quiz</code>, <code>/truth_or_dare</code>, <code>/ball</code>"
)


def split_text(text: str, max_len: int = 3500):
    """Разбивает текст на части, не превышающие лимит Telegram."""
    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            parts.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        parts.append(current.strip())
    return parts


async def call_everyone(message: Message, bot: Bot, reason: str = ""):
    chat_id = message.chat.id
    users_dict = {}

    # 1. Получаем ВСЕХ админов группы напрямую из Telegram (это работает всегда)
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if user.is_bot:
                continue
            users_dict[user.id] = {
                "username": user.username,
                "first_name": user.first_name or "Участник",
                "mention": f"@{user.username}" if user.username else f'<a href="tg://user?id={user.id}">{html.escape(user.first_name or "Участник")}</a>'
            }
            await add_user(user.id, user.username or "", user.first_name or "")
    except Exception as e:
        print(f"Не удалось получить админов: {e}")

    # 2. Добавляем всех из базы данных (тех, кто писал или вступал в группу)
    db_users = await get_all_chat_users(chat_id)
    for u in db_users:
        if u["user_id"] not in users_dict:
            username = (u["username"] or "").strip().lstrip("@")
            mention_text = f"@{username}" if username else f'<a href="tg://user?id={u["user_id"]}">{html.escape(u["first_name"] or "Участник")}</a>'
            users_dict[u["user_id"]] = {
                "username": username,
                "first_name": u["first_name"] or "Участник",
                "mention": mention_text
            }

    if not users_dict:
        await message.answer("Пока нет данных об участниках. Напишите в чат хотя бы одно сообщение, чтобы я запомнил людей!")
        return

    # Формируем упоминания с причиной созыва
    cause_text = reason.strip() if reason.strip() else "Спят 😂 но я позову их сейчас!"
    # Убираем опасные символы для HTML
    cause_safe = html.escape(cause_text)

    header_part1 = f"📢 <b>ОБЩИЙ СОЗЫВ ГРУППЫ!</b>\n📌 <b>Причина:</b> {cause_safe}\n\n👥 Участники:"
    header_part_next = "📣 <b>Продолжаю созыв (все получат уведомление, даже оффлайн):</b>\n"

    mentions = [info["mention"] for info in users_dict.values()]
    total_users = len(mentions)

    # Отправляем пачками по 6 человек в сообщении.
    # Telegram гарантированно отправляет Push-уведомление каждому упомянутому,
    # даже если человек давно не заходил или скрыл статус "был в сети".
    chunk_size = 6
    chunks = [mentions[i:i + chunk_size] for i in range(0, len(mentions), chunk_size)]

    for i, chunk in enumerate(chunks):
        if i == 0:
            text = header_part1 + "\n" + ", ".join(chunk)
        else:
            text = header_part_next + "\n" + ", ".join(chunk)

        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        if i < len(chunks) - 1:
            await asyncio.sleep(0.5)


# Обработчик команды /all с указанием причины
@router.message(Command("all"))
async def cmd_all(message: Message, bot: Bot):
    # Получаем текст после команды как причину
    parts = message.text.split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else ""
    await call_everyone(message, bot, reason=reason)


# Обработчик текста "Где все ? [причина]" или просто "Где все ?"
@router.message(F.text.lower().contains("где все"))
async def msg_where_all(message: Message, bot: Bot):
    original_text = message.text
    # Убираем фразу "Где все" и вопросительные знаки, оставляем всё остальное как причину
    cause = original_text.lower().replace("где все", "").replace("?", "").replace("!", "").strip()
    await call_everyone(message, bot, reason=cause)


# Кнопка FAQ
@router.callback_query(F.data == "faq_where_all")
async def faq_button(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await call_everyone(callback.message, bot, reason="Спят 😂 но я позову их сейчас!")


# Команда /help и фраза "Что ты умеешь"
@router.message(Command("help"))
@router.message(F.text.lower().contains("что ты умеешь"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


# Меню FAQ
@router.message(Command("faq"))
async def cmd_faq(message: Message):
    await message.answer(
        "<b>❓ Часто задаваемые вопросы</b>\n\nВыберите вопрос:",
        reply_markup=faq_keyboard(),
        parse_mode="HTML"
    )
