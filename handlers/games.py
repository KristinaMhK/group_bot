import random
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from keyboards import games_keyboard, rps_keyboard, tod_keyboard

router = Router()

# Хранилище активных игр в чатах
active_games = {}  # {chat_id: {"type": ..., "answer": ...}}

# ==================== ДАННЫЕ ДЛЯ ИГР ====================

WORDS = [
    {"word": "кошка", "hint": "Это животное, которое мяукает и любит молоко 🐱",
     "options": ["кошка", "собака", "хомяк", "попугай"]},
    {"word": "солнце", "hint": "Оно светит днём и даёт нам тепло ☀️",
     "options": ["луна", "солнце", "звезда", "облако"]},
    {"word": "пицца", "hint": "Итальянское блюдо с сыром и томатами 🍕",
     "options": ["суши", "пицца", "бургер", "паста"]},
    {"word": "гитара", "hint": "Музыкальный инструмент с 6 струнами 🎸",
     "options": ["пианино", "скрипка", "гитара", "барабан"]},
    {"word": "океан", "hint": "Огромное водное пространство на Земле 🌊",
     "options": ["река", "озеро", "океан", "пруд"]},
    {"word": "ракета", "hint": "На ней летают в космос 🚀",
     "options": ["самолёт", "ракета", "вертолёт", "дрон"]},
]

QUIZ_QUESTIONS = [
    {"q": "Какая планета самая большая в Солнечной системе?",
     "options": ["Марс", "Юпитер", "Сатурн", "Нептун"], "answer": 1},
    {"q": "Сколько костей в теле взрослого человека?",
     "options": ["186", "206", "256", "306"], "answer": 1},
    {"q": "Какой элемент обозначается символом 'O'?",
     "options": ["Золото", "Осмий", "Кислород", "Олово"], "answer": 2},
    {"q": "В каком году человек впервые побывал на Луне?",
     "options": ["1965", "1969", "1972", "1959"], "answer": 1},
    {"q": "Какая страна самая большая по площади?",
     "options": ["Канада", "Китай", "США", "Россия"], "answer": 3},
    {"q": "Сколько цветов в радуге?",
     "options": ["5", "6", "7", "8"], "answer": 2},
]

TRUTH_QUESTIONS = [
    "Какой твой самый большой страх? 😱",
    "Какой последний сон тебе запомнился? 💭",
    "Какую самую неловкую вещь ты делал? 🙈",
    "Кого из группы ты бы взял на необитаемый остров? 🏝",
    "Какой твой самый странный талант? 🤪",
    "Если бы ты мог стать невидимым на день, что бы ты сделал? 👻",
    "Какая самая глупая вещь, которую ты гуглил? 🔍",
]

DARE_TASKS = [
    "Отправь голосовое, где ты поёшь песню 🎤",
    "Напиши следующее сообщение только эмодзи 😜",
    "Расскажи шутку. Если никто не засмеётся — ещё одну 😂",
    "Напиши комплимент каждому, кто сейчас онлайн 💕",
    "Отправь самое странное фото из галереи 📸",
    "Напиши сообщение задом наперёд 🔄",
    "Сделай селфи с самым странным лицом и отправь 🤪",
]

BALL_ANSWERS = [
    "Определённо да ✅", "Без сомнений 💯",
    "Можешь быть уверен 😎", "Скорее всего 👍",
    "Знаки говорят — да 🔮", "Пока не ясно, попробуй снова 🤔",
    "Спроси позже ⏳", "Лучше не рассказывать 🤫",
    "Мой ответ — нет ❌", "Весьма сомнительно 😬",
    "Не рассчитывай на это 💔", "Однозначно нет 🚫",
]


# ==================== МЕНЮ ИГР ====================

@router.message(Command("games"))
async def cmd_games(message: Message):
    await message.answer(
        "🎮 *Меню игр*\n\nВыбери игру:",
        reply_markup=games_keyboard(),
        parse_mode="Markdown"
    )


# ==================== УГАДАЙ ЧИСЛО ====================

@router.callback_query(F.data == "game_guess_number")
async def start_guess_number_cb(callback: CallbackQuery):
    await callback.answer()
    answer = random.randint(1, 100)
    active_games[callback.message.chat.id] = {"type": "number", "answer": answer}
    await callback.message.answer(
        "🎯 Я загадал число от *1 до 100*.\nПишите числа в чат, чтобы угадать!",
        parse_mode="Markdown"
    )


@router.message(Command("guess_number"))
async def start_guess_number_cmd(message: Message):
    answer = random.randint(1, 100)
    active_games[message.chat.id] = {"type": "number", "answer": answer}
    await message.answer(
        "🎯 Я загадал число от *1 до 100*.\nПишите числа в чат, чтобы угадать!",
        parse_mode="Markdown"
    )


# Ловит числа в чате, если активна игра
@router.message(F.text.regexp(r"^\d+$"))
async def guess_number_handler(message: Message):
    chat_id = message.chat.id
    if chat_id not in active_games or active_games[chat_id]["type"] != "number":
        return

    guess = int(message.text)
    answer = active_games[chat_id]["answer"]

    if guess == answer:
        del active_games[chat_id]
        await message.answer(
            f"🎉 {message.from_user.first_name} угадал! Это было *{answer}*!",
            parse_mode="Markdown"
        )
    elif guess < answer:
        await message.reply("⬆️ Больше!")
    else:
        await message.reply("⬇️ Меньше!")


# ==================== УГАДАЙ СЛОВО ====================

@router.callback_query(F.data == "game_guess_word")
async def start_guess_word_cb(callback: CallbackQuery):
    await callback.answer()
    await _send_guess_word(callback.message)


@router.message(Command("guess_word"))
async def start_guess_word_cmd(message: Message):
    await _send_guess_word(message)


async def _send_guess_word(msg: Message):
    word_data = random.choice(WORDS)
    options = word_data["options"].copy()
    random.shuffle(options)

    buttons = [[InlineKeyboardButton(text=opt, callback_data=f"gw_{opt}")] for opt in options]

    active_games[msg.chat.id] = {"type": "word", "answer": word_data["word"]}

    await msg.answer(
        f"📝 *Угадай слово!*\n\nПодсказка: {word_data['hint']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("gw_"))
async def guess_word_answer(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in active_games or active_games[chat_id]["type"] != "word":
        await callback.answer("Игра уже завершена", show_alert=True)
        return

    guess = callback.data[3:]
    answer = active_games[chat_id]["answer"]

    if guess == answer:
        del active_games[chat_id]
        await callback.answer("🎉 Правильно!", show_alert=True)
        await callback.message.answer(
            f"🎉 {callback.from_user.first_name} угадал слово — *{answer}*!",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Неверно, попробуй ещё!", show_alert=True)


# ==================== КАМЕНЬ НОЖНИЦЫ БУМАГА ====================

@router.callback_query(F.data == "game_rps")
async def start_rps_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "✊✌️🖐 *Камень, Ножницы, Бумага!*\n\nВыбери:",
        reply_markup=rps_keyboard(), parse_mode="Markdown"
    )


@router.message(Command("rps"))
async def start_rps_cmd(message: Message):
    await message.answer(
        "✊✌️🖐 *Камень, Ножницы, Бумага!*\n\nВыбери:",
        reply_markup=rps_keyboard(), parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("rps_"))
async def rps_result(callback: CallbackQuery):
    choices = {"rock": "✊ Камень", "scissors": "✌️ Ножницы", "paper": "🖐 Бумага"}
    wins = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

    user_choice = callback.data[4:]
    bot_choice = random.choice(["rock", "scissors", "paper"])

    if user_choice == bot_choice:
        result = "🤝 Ничья!"
    elif wins[user_choice] == bot_choice:
        result = "🎉 Ты победил!"
    else:
        result = "😢 Бот победил!"

    await callback.answer()
    await callback.message.answer(
        f"Ты: {choices[user_choice]}\n"
        f"Бот: {choices[bot_choice]}\n\n{result}"
    )


# ==================== ВИКТОРИНА ====================

@router.callback_query(F.data == "game_quiz")
async def start_quiz_cb(callback: CallbackQuery):
    await callback.answer()
    await _send_quiz(callback.message)


@router.message(Command("quiz"))
async def start_quiz_cmd(message: Message):
    await _send_quiz(message)


async def _send_quiz(msg: Message):
    q = random.choice(QUIZ_QUESTIONS)
    buttons = [
        [InlineKeyboardButton(text=opt, callback_data=f"quiz_{q['answer']}_{i}")]
        for i, opt in enumerate(q["options"])
    ]
    await msg.answer(
        f"❓ *Викторина*\n\n{q['q']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("quiz_"))
async def quiz_answer(callback: CallbackQuery):
    parts = callback.data.split("_")
    correct = int(parts[1])
    chosen = int(parts[2])

    if chosen == correct:
        await callback.answer("🎉 Правильно!", show_alert=True)
        await callback.message.answer(f"✅ {callback.from_user.first_name} ответил правильно!")
    else:
        await callback.answer("❌ Неверно!", show_alert=True)
        await callback.message.answer(f"❌ {callback.from_user.first_name} ошибся!")


# ==================== ПРАВДА ИЛИ ДЕЙСТВИЕ ====================

@router.callback_query(F.data == "game_tod")
async def start_tod_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🎭 *Правда или Действие?*\n\nВыбирай!",
        reply_markup=tod_keyboard(), parse_mode="Markdown"
    )


@router.message(Command("truth_or_dare"))
async def start_tod_cmd(message: Message):
    await message.answer(
        "🎭 *Правда или Действие?*\n\nВыбирай!",
        reply_markup=tod_keyboard(), parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("tod_"))
async def tod_result(callback: CallbackQuery):
    await callback.answer()
    name = callback.from_user.first_name
    if callback.data == "tod_truth":
        q = random.choice(TRUTH_QUESTIONS)
        await callback.message.answer(f"😇 *Правда для {name}:*\n\n{q}", parse_mode="Markdown")
    else:
        d = random.choice(DARE_TASKS)
        await callback.message.answer(f"😈 *Действие для {name}:*\n\n{d}", parse_mode="Markdown")


# ==================== ШАР ПРЕДСКАЗАНИЙ ====================

@router.callback_query(F.data == "game_8ball")
async def ball_from_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔮 Задай вопрос командой:\n/ball <твой вопрос>")


@router.message(Command("ball"))
async def cmd_ball(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔮 Задай вопрос! Например:\n/ball Буду ли я богат?")
        return

    answer = random.choice(BALL_ANSWERS)
    await message.answer(
        f"🔮 *Вопрос:* {args[1]}\n\n*Ответ:* {answer}",
        parse_mode="Markdown"
    )
    