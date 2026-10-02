from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import faq_keyboard
from database import get_all_chat_users

router = Router()

HELP_TEXT = (
    "🐻 *Привет! Я помощник бот Sib.Bear.*\n\n"
    "Вот всё, что я умею делать в вашей группе:\n\n"
    "👋 *Приветствие участников:*\n"
    "• Автоматически и тепло встречаю каждого нового участника.\n\n"
    "📊 *Статистика и рейтинги:*\n"
    "• `/stats` — общая статистика группы и количество твоих сообщений\n"
    "• `/top` — рейтинг самых активных за день/неделю/месяц с титулами (👑 Король, 🥈 Вице-король и др.)\n\n"
    "❓ *Частые вопросы (FAQ):*\n"
    "• `/faq` — меню частых вопросов (умею звать всех участников, если чат уснул 😂)\n\n"
    "🎮 *Мини-игры для всей группы:*\n"
    "• `/games` — открыть меню всех 6 игр\n"
    "• `/guess_number` — игра «Угадай число» от 1 до 100\n"
    "• `/guess_word` — игра «Угадай слово» с вариантами\n"
    "• `/rps` — Камень, Ножницы, Бумага\n"
    "• `/quiz` — увлекательная викторина\n"
    "• `/truth_or_dare` — Правда или Действие\n"
    "• `/ball <вопрос>` — магический шар предсказаний\n\n"
    "✨ *Просто выбери нужную команду и отправь её в чат!*"
)


# Срабатывает на команду /help или на текст "что ты умеешь" (в любых вариациях)
@router.message(Command("help"))
@router.message(F.text.lower().contains("что ты умеешь"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    await message.answer(
        "❓ *Часто задаваемые вопросы*\n\nВыберите вопрос:",
        reply_markup=faq_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "faq_where_all")
async def faq_where_all(callback: CallbackQuery):
    await callback.answer()

    users = await get_all_chat_users(callback.message.chat.id)

    if not users:
        await callback.message.answer("Пока никто не писал в группу 🤷")
        return

    mentions = []
    for u in users:
        mentions.append(f"[{u['first_name']}](tg://user?id={u['user_id']})")

    text = "Спят 😂 но я позову их сейчас\n\n" + ", ".join(mentions)
    await callback.message.answer(text, parse_mode="Markdown")
    
