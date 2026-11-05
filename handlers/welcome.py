import logging

from aiogram import Router, F, Bot
from aiogram.types import Message
from database import add_user

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.new_chat_members)
async def welcome_members(message: Message, bot: Bot):
    chat_id = message.chat.id

    for member in message.new_chat_members:
        # Если в группу добавили самого бота
        if member.is_bot and member.id == bot.id:
            await message.answer(
                "Всех Приветствую, я помощник бот Sib.Bear 🐻"
            )
            continue

        # Пропускаем других ботов
        if member.is_bot:
            continue

        # Определяем имя для приветствия
        if member.username:
            display_name = f"@{member.username}"
        else:
            display_name = member.first_name or "Участник"

        # Проверяем, знает ли бот этого участника
        try:
            from database import get_all_chat_users
            known = await get_all_chat_users(chat_id)
            known_ids = {u["user_id"] for u in known}
        except Exception:
            known_ids = set()

        if member.id in known_ids:
            await message.answer(
                f"Sib Рада твоему возвращению, {display_name}! "
                f"Снова вместе 😘🐻"
            )
        else:
            await message.answer(
                f"Sib Приветствует тебя - {display_name}! "
                f"Добро пожаловать 😘"
            )

        # Записываем участника в БД с chat_id
        try:
            await add_user(
                member.id,
                member.username or "",
                member.first_name or "Участник",
            )
        except Exception as e:
            logger.warning("Не удалось записать участника: %s", e)
