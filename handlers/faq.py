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
    "• Напиши <code>Где все ?</code> или <code>/all</code> — я позову всех участников группы.\n\n"
    "<b>📊 Статистика:</b>\n"
    "• <code>/stats</code> — статистика группы и твои сообщения.\n"
    "• <code>/top</code> — топ активных за день, неделю и месяц.\n\n"
    "<b>❓ FAQ:</b>\n"
    "• <code>/faq</code> — частые вопросы.\n\n"
    "<b>🎮 Игры:</b>\n"
    "• <code>/games</code> — меню игр.\n"
    "• <code>/guess_number</code> — угадай число.\n"
    "• <code>/guess_word</code> — угадай слово.\n"
    "• <code>/rps</code> — камень, ножницы, бумага.\n"
    "• <code>/quiz</code> — викторина.\n"
    "• <code>/truth_or_dare</code> — правда или действие.\n"
    "• <code>/ball &lt;вопрос&gt;</code> — шар предсказаний."
)


async def call_everyone(message: Message, bot: Bot):
    chat_id = message.chat.id
    all_users = {}  # user_id: {"username": ..., "first_name": ...}

    # 1. Запрашиваем напрямую у Telegram всех администраторов чата (работает всегда на 100%)
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            user = admin.user
            if not user.is_bot:
                all_users[user.id] = {
                    "username": user.username,
                    "first_name": user.first_name or "Участник"
                }
                # Сохраняем в базу данных
                await add_user(user.id, user.username or "", user.first_name or "Участник")
    except Exception as e:
        print(f"Ошибка получения админов: {e}")

    # 2. Добавляем всех участников из базы данных (кто писал сообщения или вступал)
    db_users = await get_all_chat_users(chat_id)
    for u in db_users:
        if u["user_id"] not in all_users:
            all_users[u["user_id"]] = {
                "username": u["username"],
                "first_name": u["first_name"] or "Участник"
            }

    if not all_users:
        await message.answer(
            "Пока никого нет в списке 🤷\n\n"
            "Напишите в группу по одному сообщению, чтобы я всех запомнил!"
        )
        return

    # 3. Формируем список тегов с указанием ника
    mentions = []
    for uid, info in all_users.items():
        username = (info["username"] or "").strip().lstrip("@")
        first_name = html.escape(info["first_name"])

        if username:
            # Если есть ник в Telegram
            mentions.append(f"@{username}")
        else:
            # Если ника нет — тегаем по ID через имя
            mentions.append(f'<a href="tg://user?id={uid}">{first_name}</a>')

    # 4. Отправляем теги пачками по 15 человек (чтобы Telegram не счёл за спам и прислал уведомления всем)
    chunk_size = 15
    chunks = [mentions[i:i + chunk_size] for i in range(0, len(mentions), chunk_size)]

    for index, chunk in enumerate(chunks):
        if index == 0:
            header = "<b>Спят 😂 но я позову их сейчас:</b>\n\n"
        else:
            header = "<b>📣 Продолжаю созыв:</b>\n\n"

        text = header + " ".join(chunk)
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        if index < len(chunks) - 1:
            await asyncio.sleep(0.5)


# Срабатывает на любую фразу со словами "где все" (независимо от регистра и пробелов) или /all
@router.message(Command("all"))
@router.message(F.text.lower().contains("где все"))
async def where_is_everyone(message: Message, bot: Bot):
    await call_everyone(message, bot)


# Кнопка в /faq
@router.callback_query(F.data == "faq_where_all")
async def faq_where_all_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await call_everyone(callback.message, bot)


# Справка
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
