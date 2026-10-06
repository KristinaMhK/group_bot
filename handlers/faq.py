import asyncio
import hashlib
import html
import logging
import random
import re

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards import faq_keyboard
from database import get_all_chat_users, add_user

logger = logging.getLogger(__name__)

router = Router()


# ======================= КОНСТАНТЫ =======================

# Варианты ответов на "Доброе утро"
MORNING_ANSWERS = (
    "Доброе утречко 🌞",
    "Доброго и прекрасного денёчка 💕✨",
    "Прекрасного и лёгкого денёчка 🌞💕",
)

# Ключевые фразы для созыва. Хранятся в нижнем регистре.
SUMMON_PHRASES = (
    "все в игру",
    "заходим",
)

# Эмодзи для участников. У каждого участника свой стабильный эмодзи.
SUMMON_EMOJIS = (
    "🐻", "🦊", "🐼", "🐯", "🦁",
    "🐸", "🐵", "🐺", "🦄", "🐙",
    "🦅", "🐉", "🔥", "⚡", "🌪️",
    "🌊", "🌵", "🍀", "⭐", "💎",
    "🚀", "🎯", "🛡️", "⚔️", "👑",
    "😂", "😀", "😃", "😄", "😁",
    "😆", "😅", "😭", "😉", "😗",
    "😙", "😚", "😘", "🥰", "😍",
    "🤩", "🥳", "🫠", "🙃", "🙂",
    "🥲", "🥹", "😊", "☺️", "😌",
    "😏", "🤤", "😋", "😛", "🤓",
    "😎", "🥸", "🤡", "💩", "😈",
    "👿", "👻", "💀", "☠️", "🤖",
    "👹", "👺", "☃️", "👽", "👾",
    "🌚", "🌝", "🌞", "🌛", "🌜",
    "😺", "😸", "🙈",
)

HELP_TEXT = (
    "<b>🐻 Привет! Я помощник Sib.Bear.</b>\n\n"
    "Вот что я умею:\n\n"
    "<b>👋 Приветствие:</b>\n"
    "• Встречаю новых участников группы.\n\n"
    "<b>📢 Созыв участников:</b>\n"
    "• Напиши <code>Все в игру</code> или <code>Заходим</code>.\n"
    "• После фразы можно указать причину созыва.\n"
    "• Также можно использовать команду <code>/all причина</code>.\n\n"
    "<b>📊 Статистика:</b>\n"
    "• <code>/stats</code> — статистика сообщений группы.\n"
    "• <code>/top</code> — топ самых активных участников.\n\n"
    "<b>❓ FAQ:</b>\n"
    "• <code>/faq</code> — частые вопросы.\n\n"
    "<b>🎮 Мини-игры:</b>\n"
    "• <code>/games</code> — открыть игровое меню."
)


# ======================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =======================

def get_user_emoji(user_id: int, chat_id: int) -> str:
    """
    Назначает участнику стабильное псевдослучайное эмодзи.
    Для одного и того же участника в группе эмодзи всегда одинаковое.
    """
    value = f"{chat_id}:{user_id}".encode("utf-8")
    number = int(hashlib.sha256(value).hexdigest(), 16)
    return SUMMON_EMOJIS[number % len(SUMMON_EMOJIS)]


def find_summon_phrase(text: str) -> tuple[str, str] | None:
    """
    Ищет фразу созыва в начале сообщения.
    Возвращает кортеж (найденная_фраза, причина) или None, если фразы нет.
    """
    source = (text or "").strip()
    if not source:
        return None

    for phrase in sorted(SUMMON_PHRASES, key=len, reverse=True):
        phrase_pattern = r"\s+".join(
            re.escape(word) for word in phrase.split()
        )
        pattern = rf"^\s*{phrase_pattern}(?=$|\s|[!?.,:;—–-])"
        match = re.match(pattern, source, flags=re.IGNORECASE)

        if match:
            reason = source[match.end():].strip(" \t\r\n.,!?;:—–-")
            return phrase, reason

    return None


def is_summon_message(message: Message) -> bool:
    """Фильтр: сообщение должно начинаться с одной из фраз созыва."""
    return bool(message.text and find_summon_phrase(message.text))


def chunked(items: list[str], size: int) -> list[list[str]]:
    """Делит список на пачки нужного размера."""
    return [items[i:i + size] for i in range(0, len(items), size)]


# ======================= СОЗЫВ УЧАСТНИКОВ =======================

async def execute_call_all(message: Message, bot: Bot, reason: str):
    chat_id = message.chat.id
    all_users: dict[int, dict[str, str | None]] = {}

    # 1. Получаем администраторов группы.
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if user.is_bot:
                continue

            all_users[user.id] = {
                "username": user.username,
                "first_name": user.first_name or "Участник",
            }

            try:
                await add_user(
                    user.id,
                    user.username or "",
                    user.first_name or "Участник",
                )
            except Exception as db_err:
                logger.warning("Не удалось записать админа в БД: %s", db_err)

    except Exception as e:
        logger.warning("Ошибка получения администраторов: %s", e)

    # 2. Добавляем людей, которых бот уже видел в этой группе.
    try:
        db_users = await get_all_chat_users(chat_id)
    except Exception as e:
        logger.exception("Ошибка чтения пользователей из БД: %s", e)
        db_users = []

    for u in db_users:
        if u["user_id"] in all_users:
            continue

        all_users[u["user_id"]] = {
            "username": u.get("username"),
            "first_name": u.get("first_name") or "Участник",
        }

    if not all_users:
        await message.answer(
            "Пока в моей базе нет участников этой группы. "
            "Попросите людей написать в чат, чтобы я их запомнил."
        )
        return

    # 3. Готовим список упоминаний: эмодзи + ник или кликабельное имя.
    mentions: list[str] = []

    for uid, info in all_users.items():
        username_raw = (info.get("username") or "").strip().lstrip("@")
        first_name = html.escape(info.get("first_name") or "Участник")
        emoji = get_user_emoji(uid, chat_id)

        if username_raw:
            person = f"@{html.escape(username_raw)}"
        else:
            person = f'<a href="tg://user?id={uid}">{first_name}</a>'

        mentions.append(f"{emoji} {person}")

    # 4. Готовим причину созыва (если пусто — ставим дефолт).
    raw_reason = (reason or "").strip()
    clean_reason = html.escape(raw_reason) if raw_reason else "Спят 😂 но я позову их сейчас!"

    # 5. Отправляем пачками, чтобы Telegram доставил уведомления всем.
    chunk_size = 7
    chunks = chunked(mentions, chunk_size)

    for index, chunk in enumerate(chunks):
        if index == 0:
            header = f"📢 <b>{clean_reason}</b>\n\n"
        else:
            header = "📣 <b>Продолжаю созыв:</b>\n\n"

        text = header + ", ".join(chunk)

        try:
            await message.answer(
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as send_err:
            logger.exception("Ошибка отправки созыва: %s", send_err)

        if index < len(chunks) - 1:
            await asyncio.sleep(0.4)


# ======================= ОБРАБОТЧИКИ =======================

# Приветствие "Доброе утро"
@router.message(F.text.lower().contains("доброе утро"))
async def reply_good_morning(message: Message):
    response = random.choice(MORNING_ANSWERS)
    await message.reply(response)


# Команда /all причина
@router.message(Command("all"))
async def cmd_all(message: Message, bot: Bot):
    args = (message.text or "").split(maxsplit=1)
    reason = args[1] if len(args) > 1 else ""
    await execute_call_all(message, bot, reason)


# Созыв по ключевым фразам
@router.message(is_summon_message)
async def summon_by_phrase(message: Message, bot: Bot):
    parsed = find_summon_phrase(message.text or "")

    if parsed is None:
        return

    phrase, reason = parsed

    if not reason:
        display_phrase = phrase[0].upper() + phrase[1:]
        reason = f"Собираемся! Сигнал: «{display_phrase}»"

    await execute_call_all(message, bot, reason)


# Кнопка «Где все?» из /faq
@router.callback_query(F.data == "faq_where_all")
async def faq_where_all_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await execute_call_all(
        callback.message,
        bot,
        "Спят 😂 но я позову их сейчас!",
    )


# Справка: /help или фраза «Что ты умеешь»
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
        parse_mode="HTML",
        )
