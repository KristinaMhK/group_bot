import asyncio
import html

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards import faq_keyboard
from database import get_all_chat_users

router = Router()


HELP_TEXT = (
    "<b>🐻 Привет! Я помощник Sib.Bear.</b>\n\n"
    "Вот что я умею:\n\n"

    "<b>👋 Приветствие:</b>\n"
    "• Встречаю новых участников группы.\n\n"

    "<b>📢 Созыв участников:</b>\n"
    "• Напиши <code>Где все ?</code> или <code>/all</code> — "
    "я позову известных мне участников группы.\n\n"

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


def split_mentions(header: str, mentions: list[str], limit: int = 3300):
    """
    Telegram разрешает сообщения до 4096 символов.
    Делим длинный список участников на несколько сообщений.
    """
    parts = []
    current_text = header

    for mention in mentions:
        addition = mention if current_text == header else ", " + mention

        if len(current_text) + len(addition) > limit:
            parts.append(current_text)
            current_text = "<b>📣 Продолжаю звать:</b>\n\n" + mention
        else:
            current_text += addition

    if current_text:
        parts.append(current_text)

    return parts


async def call_everyone(message: Message):
    """Отправляет упоминания известных боту участников."""
    users = await get_all_chat_users(message.chat.id)

    if not users:
        await message.answer(
            "Пока я никого не успел запомнить 🤷\n\n"
            "Попросите участников написать хотя бы одно сообщение в группу."
        )
        return

    mentions = []

    for user in users:
        username = (user["username"] or "").strip().lstrip("@")
        first_name = html.escape(user["first_name"] or "Участник")

        # Если у человека есть @username — показываем его ник
        if username:
            mentions.append(f"@{html.escape(username)}")
        else:
            # Если ника нет — делаем кликабельное упоминание по ID
            mentions.append(
                f'<a href="tg://user?id={user["user_id"]}">{first_name}</a>'
            )

    header = "<b>Спят 😂 но я позову их сейчас:</b>\n\n"
    messages = split_mentions(header, mentions)

    for index, text in enumerate(messages):
        await message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        # Небольшая пауза между сообщениями, если участников много
        if index < len(messages) - 1:
            await asyncio.sleep(0.2)


# Работает на точную фразу:
# Где все?
# Где все ?
# где    все!!!
@router.message(Command("all"))
@router.message(
    F.text.regexp(r"(?i)^\s*где\s+все\s*[?!.,…]*\s*$")
)
async def where_is_everyone(message: Message):
    await call_everyone(message)


# Кнопка «Где все?» из /faq
@router.callback_query(F.data == "faq_where_all")
async def faq_where_all_callback(callback: CallbackQuery):
    await callback.answer()
    await call_everyone(callback.message)


# Команда /help и фраза «Что ты умеешь?»
@router.message(Command("help"))
@router.message(
    F.text.regexp(r"(?i)^\s*что\s+ты\s+умеешь\s*[?!.,…]*\s*$")
)
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    await message.answer(
        "<b>❓ Часто задаваемые вопросы</b>\n\nВыберите вопрос:",
        reply_markup=faq_keyboard(),
        parse_mode="HTML"
    )
    
