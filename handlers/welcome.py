import logging

from aiogram import Router, F, Bot
from aiogram.types import Message
from database import add_user

logger = logging.getLogger(__name__)

router = Router()


# ======================= ПРИВЕТСТВИЕ =======================

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
                f"Sib Приветствует тебя - {display_name}! "
                f"Добро пожаловать 😘🐻"
            )
        else:
            await message.answer(
                f"Sib Приветствует тебя - {display_name}! "
                f"Добро пожаловать 😘"
            )

        # Записываем участника в БД
        try:
            await add_user(
                member.id,
                member.username or "",
                member.first_name or "Участник",
            )
        except Exception as e:
            logger.warning("Не удалось записать участника: %s", e)


# ======================= ПРОЩАНИЕ =======================

@router.message(F.left_chat_member)
async def farewell_member(message: Message, bot: Bot):
    member = message.left_chat_member

    # Не прощаемся с ботами
    if member.is_bot:
        return

    # Определяем имя
    if member.username:
        display_name = f"@{member.username}"
    else:
        display_name = member.first_name or "Участник"

    # 1. Сообщение в группу
    await message.answer(
        f"{display_name}, покинул чат. До новых встреч 💗"
    )

    # 2. Личное сообщение участнику
    try:
        await bot.send_message(
            member.id,
            "Удачи и до новых встреч 💗"
        )
    except Exception as e:
        # ЛС не дойдёт, если пользователь не запускал бота лично
        logger.info("Не удалось отправить ЛС пользователю %s: %s", member.id, e)
