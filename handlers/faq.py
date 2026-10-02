import re
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
    "Вот что я умею:\n\n"
    "<b>👋 Приветствие:</b>\n"
    "• Встречаю каждого нового участника.\n\n"
    "<b>📢 Созыв участников:</b>\n"
    "• Напиши <code>Где все ? [твоя причина]</code> или <code>/all [твоя причина]</code> — я позову всех участников чата.\n\n"
    "<b>📊 Статистика:</b>\n"
    "• <code>/stats</code> — твоя статистика сообщений.\n"
    "• <code>/top</code> — топ самых активных участников чата.\n\n"
    "<b>❓ FAQ:</b>\n"
    "• <code>/faq</code> — частые вопросы.\n\n"
    "<b>🎮 Мини-игры:</b>\n"
    "• <code>/games</code> — открыть игровое меню"
)


async def execute_call_all(message: Message, bot: Bot, reason: str):
    chat_id = message.chat.id
    all_users = {}

    # 1. Получаем администраторов
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if not user.is_bot:
                all_users[user.id] = {
                    "username": user.username,
                    "first_name": user.first_name or "Участник"
                }
                await add_user(user.id, user.username or "", user.first_name or "Участник")
    except Exception as e:
        print(f"Ошибка получения админов: {e}")

    # 2. Добавляем людей из БД
    db_users = await get_all_chat_users(chat_id)
    for u in db_users:
        if u["user_id"] not in all_users:
            all_users[u["user_id"]] = {
                "username": u["username"],
                "first_name": u["first_name"] or "Участник"
            }

    if not all_users:
        await message.answer("Пока в моей базе нет участников этой группы 🤷")
        return

    # 3. Формируем список упоминаний
    mentions = []
    for uid, info in all_users.items():
        username = (info["username"] or "").strip().lstrip("@")
        first_name = html.escape(info["first_name"])

        if username:
            mentions.append(f"@{username}")
        else:
            mentions.append(f'<a href="tg://user?id={uid}">{first_name}</a>')

    # Очищаем причину (если пусто, ставим дефолт)
    clean_reason = html.escape(reason.strip()) if reason.strip() else "Спят 😂 но я позову их сейчас!"

    # 4. Отправляем пачками по 6–8 человек для гарантированного Push-уведомления
    chunk_size = 7
    chunks = [mentions[i:i + chunk_size] for i in range(0, len(mentions), chunk_size)]

    for index, chunk in enumerate(chunks):
        if index == 0:
            # Сразу пишем фразу-причину без лишних заголовков!
            header = f"📢 <b>{clean_reason}</b>\n\n"
        else:
            header = "📣 <b>Продолжаю созыв:</b>\n"

        text = header + ", ".join(chunk)
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        if index < len(chunks) - 1:
            await asyncio.sleep(0.4)


# Реакция на команду /all <причина>
@router.message(Command("all"))
async def cmd_all(message: Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else ""
    await execute_call_all(message, bot, reason)


# Реакция на "Где все ?" с автоматическим считыванием причины
@router.message(F.text.lower().contains("где все"))
async def msg_where_all_regex(message: Message, bot: Bot):
    text_lower = message.text.lower()
    # Находим, где заканчивается фраза "где все" (с любыми знаками препинания)
    match = re.search(r"где\s+все\s*[?!.,…]*", text_lower)
    if match:
        reason = message.text[match.end():].strip()
    else:
        reason = ""
    await execute_call_all(message, bot, reason)


# Кнопка в /faq
@router.callback_query(F.data == "faq_where_all")
async def faq_where_all_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await execute_call_all(callback.message, bot, "Спят 😂 но я позову их сейчас!")


# Справка по боту
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
    
