from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from database import add_user, log_new_member

router = Router()


@router.chat_member()
async def on_new_member(event: ChatMemberUpdated, bot: Bot):
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    # Сработает только когда пользователь вошёл в группу
    if new_status in ("member", "restricted") and old_status in ("left", "kicked"):
        user = event.new_chat_member.user
        if user.is_bot:
            return

        await add_user(user.id, user.username, user.first_name)
        await log_new_member(event.chat.id, user.id)

        mention = f"[{user.first_name}](tg://user?id={user.id})"
        await bot.send_message(
            event.chat.id,
            f"Sib Приветствует тебя - {mention}! Добро пожаловать 😘",
            parse_mode="Markdown"
        )
        