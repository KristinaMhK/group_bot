from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import faq_keyboard
from database import get_all_chat_users

router = Router()


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

    # Упоминаем всех через невидимую ссылку
    mentions = []
    for u in users:
        mentions.append(f"[{u['first_name']}](tg://user?id={u['user_id']})")

    text = "Спят 😂 но я позову их сейчас\n\n" + ", ".join(mentions)
    await callback.message.answer(text, parse_mode="Markdown")
    