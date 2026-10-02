from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def faq_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤔 Где все?", callback_data="faq_where_all")]
    ])


def games_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Угадай число", callback_data="game_guess_number")],
        [InlineKeyboardButton(text="🐊 Крокодил", callback_data="game_guess_word")],
        [InlineKeyboardButton(text="✊ Камень Ножницы Бумага", callback_data="game_rps")],
        [InlineKeyboardButton(text="❓ Викторина", callback_data="game_quiz")],
        [InlineKeyboardButton(text="🎭 Правда или Действие", callback_data="game_tod")],
        [InlineKeyboardButton(text="🔮 Шар предсказаний", callback_data="game_8ball")],
        [InlineKeyboardButton(text="🚢 Морской бой", callback_data="game_seabattle")],
    ])


def rps_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✊ Камень", callback_data="rps_rock"),
            InlineKeyboardButton(text="✌️ Ножницы", callback_data="rps_scissors"),
            InlineKeyboardButton(text="🖐 Бумага", callback_data="rps_paper"),
        ]
    ])


def tod_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="😇 Правда", callback_data="tod_truth"),
            InlineKeyboardButton(text="😈 Действие", callback_data="tod_dare"),
        ]
    ])


def seabattle_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚓ Присоединиться к бою!", callback_data="sb_join")]
    ])
