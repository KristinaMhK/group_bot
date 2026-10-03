import html
import random
import re

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

from keyboards import games_keyboard, rps_keyboard, tod_keyboard

router = Router()

# Активные игры, требующие текстовых ответов:
# {chat_id: {"type": "number", "answer": ...}}
# {chat_id: {"type": "crocodile", "answer": ...}}
active_games = {}


# ==================== ДАННЫЕ ДЛЯ ИГР ====================

CROCODILE_WORDS = [
    {
        "word": "компьютер",
        "description": "Электронный мозг на вашем столе. У него есть мышь, но она не ест сыр, и клавиатура, на которой часто спит кот.",
    },
    {
        "word": "холодильник",
        "description": "Белый шкаф на кухне, внутри которого всегда темно, пока не откроешь дверь. Ночью к нему совершаются тайные набеги.",
    },
    {
        "word": "кофе",
        "description": "Горячий тёмный напиток, который превращает сонного человека в бодрого по утрам.",
    },
    {
        "word": "пылесос",
        "description": "Домашний шумный помощник, который собирает пыль и мелкие вещи с пола.",
    },
    {
        "word": "будильник",
        "description": "Устройство, которое начинает громко звенеть именно тогда, когда хочется поспать ещё пять минут.",
    },
    {
        "word": "зонт",
        "description": "Складная крыша на палочке, которую часто забывают дома перед дождём.",
    },
    {
        "word": "кошка",
        "description": "Пушистое животное, которое любит спать, просить еду и исследовать коробки.",
    },
    {
        "word": "пицца",
        "description": "Круглое итальянское блюдо в квадратной коробке, которое обычно нарезают треугольниками.",
    },
    {
        "word": "чемодан",
        "description": "Вещь на колёсиках, которую берут с собой в путешествие.",
    },
    {
        "word": "телевизор",
        "description": "Большой экран, на котором можно смотреть фильмы и передачи.",
    },
    {
        "word": "арбуз",
        "description": "Большая зелёная ягода с полосками, красной мякотью и чёрными семечками.",
    },
    {
        "word": "велосипед",
        "description": "Двухколёсный транспорт, который едет, когда крутишь педали.",
    },
]

QUIZ_QUESTIONS = [
    {
        "q": "Какая планета самая большая в Солнечной системе?",
        "options": ["Марс", "Юпитер", "Сатурн", "Нептун"],
        "answer": 1,
    },
    {
        "q": "Сколько костей в теле взрослого человека?",
        "options": ["186", "206", "256", "306"],
        "answer": 1,
    },
    {
        "q": "Какой элемент обозначается символом O?",
        "options": ["Золото", "Осмий", "Кислород", "Олово"],
        "answer": 2,
    },
    {
        "q": "В каком году человек впервые побывал на Луне?",
        "options": ["1965", "1969", "1972", "1959"],
        "answer": 1,
    },
    {
        "q": "Какая страна самая большая по площади?",
        "options": ["Канада", "Китай", "США", "Россия"],
        "answer": 3,
    },
    {
        "q": "Сколько цветов обычно выделяют в радуге?",
        "options": ["5", "6", "7", "8"],
        "answer": 2,
    },
]

TRUTH_QUESTIONS = [
    "Какой твой самый большой страх? 😱",
    "Какой последний сон тебе запомнился? 💭",
    "Какую самую неловкую вещь ты делал в жизни? 🙈",
    "Кого из группы ты бы взял на необитаемый остров? 🏝",
    "Какой твой самый странный талант? 🤪",
]

DARE_TASKS = [
    "Отправь голосовое сообщение, где ты поёшь любую песню 🎤",
    "Напиши следующее сообщение в группу только эмодзи 😜",
    "Расскажи любую шутку 😂",
    "Напиши приятный комплимент участнику чата 💕",
]

BALL_ANSWERS = [
    "Определённо да ✅",
    "Без сомнений 💯",
    "Можешь быть уверен 😎",
    "Скорее всего 👍",
    "Знаки говорят — да 🔮",
    "Пока не ясно, спроси позже ⏳",
    "Мой ответ — нет ❌",
    "Весьма сомнительно 😬",
    "Не рассчитывай на это 💔",
    "Однозначно нет 🚫",
]


# ==================== ОБЩИЕ ФУНКЦИИ ====================

def normalize_guess(text: str) -> str:
    """Убирает пробелы и знаки препинания, чтобы принять, например, «Кошка!»."""
    return re.sub(r"[\W_]+", "", text.casefold())


def is_active_game_input(message: Message) -> bool:
    """
    Фильтр для ответов в играх.
    Не пропускает команды вроде /help или /rps.
    """
    if not message.text or not message.from_user:
        return False

    text = message.text.strip()

    # Команды должны проходить к своим обработчикам.
    if text.startswith("/"):
        return False

    game = active_games.get(message.chat.id)
    if not game:
        return False

    if game["type"] == "number":
        return re.fullmatch(r"[+-]?\d+", text) is not None

    if game["type"] == "crocodile":
        return bool(text)

    return False


# ==================== МЕНЮ ИГР ====================

@router.message(Command("games"))
async def cmd_games(message: Message):
    await message.answer(
        "<b>🎮 Игровое меню Sib.Bear</b>\n\nВыбери игру:",
        reply_markup=games_keyboard(),
        parse_mode="HTML",
    )


# ==================== УГАДАЙ ЧИСЛО ====================

async def start_guess_number(message: Message):
    chat_id = message.chat.id

    if chat_id in active_games:
        await message.answer(
            "В этом чате уже идёт игра. Завершите её или отправьте /stop_game."
        )
        return

    answer = random.randint(1, 100)
    active_games[chat_id] = {
        "type": "number",
        "answer": answer,
    }

    await message.answer(
        "🎯 Я загадал число от <b>1 до 100</b>.\n"
        "Пишите числа в чат, чтобы угадать!",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "game_guess_number")
async def start_guess_number_callback(callback: CallbackQuery):
    await callback.answer()
    await start_guess_number(callback.message)


@router.message(Command("guess_number"))
async def start_guess_number_command(message: Message):
    await start_guess_number(message)


# ==================== КРОКОДИЛ ====================

async def start_crocodile(message: Message):
    chat_id = message.chat.id

    if chat_id in active_games:
        await message.answer(
            "В этом чате уже идёт игра. Завершите её или отправьте /stop_game."
        )
        return

    word_data = random.choice(CROCODILE_WORDS)
    active_games[chat_id] = {
        "type": "crocodile",
        "answer": word_data["word"],
    }

    description = html.escape(word_data["description"])

    await message.answer(
        "🐊 <b>Игра «Крокодил» началась!</b>\n\n"
        f"Я загадал слово и объясняю его:\n"
        f"<i>«{description}»</i>\n\n"
        "Пишите догадки прямо в чат. "
        "Первый, кто угадает, победит!",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "game_guess_word")
async def start_crocodile_callback(callback: CallbackQuery):
    await callback.answer()
    await start_crocodile(callback.message)


@router.message(Command("guess_word"))
@router.message(Command("crocodile"))
async def start_crocodile_command(message: Message):
    await start_crocodile(message)


# ==================== ОБРАБОТЧИК ОТВЕТОВ В ИГРАХ ====================
# Важно: он находится после команд и срабатывает только на подходящий ответ.

@router.message(F.text, is_active_game_input)
async def chat_games_handler(message: Message):
    chat_id = message.chat.id
    game = active_games.get(chat_id)

    if not game or not message.text:
        return

    user_text = message.text.strip()

    if game["type"] == "number":
        guess = int(user_text)

        if guess < 1 or guess > 100:
            await message.reply("Число должно быть от 1 до 100.")
            return

        answer = game["answer"]

        if guess == answer:
            del active_games[chat_id]
            name = html.escape(message.from_user.first_name)
            await message.reply(
                f"🎉 <b>{name}</b> угадал число! Это было <b>{answer}</b>!",
                parse_mode="HTML",
            )
        elif guess < answer:
            await message.reply("⬆️ Моё число больше!")
        else:
            await message.reply("⬇️ Моё число меньше!")

    elif game["type"] == "crocodile":
        answer = game["answer"]

        if normalize_guess(user_text) == normalize_guess(answer):
            del active_games[chat_id]
            name = html.escape(message.from_user.first_name)
            word = html.escape(answer.upper())

            await message.reply(
                f"🎉 Поздравляем, <b>{name}</b> угадал слово!\n"
                f"🐊 Загаданное слово: <b>{word}</b>!",
                parse_mode="HTML",
            )


# ==================== ОСТАНОВКА ИГРЫ ====================

@router.message(Command("stop_game"))
async def stop_game(message: Message):
    if active_games.pop(message.chat.id, None):
        await message.answer("🏁 Игра остановлена.")
    else:
        await message.answer("В этом чате сейчас нет активной игры на угадывание.")


# ==================== КАМЕНЬ, НОЖНИЦЫ, БУМАГА ====================

async def send_rps(message: Message):
    await message.answer(
        "✊✌️🖐 <b>Камень, ножницы, бумага!</b>\n\nВыбери свой знак:",
        reply_markup=rps_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "game_rps")
async def start_rps_callback(callback: CallbackQuery):
    await callback.answer()
    await send_rps(callback.message)


@router.message(Command("rps"))
async def start_rps_command(message: Message):
    await send_rps(message)


@router.callback_query(F.data.startswith("rps_"))
async def rps_result(callback: CallbackQuery):
    choices = {
        "rock": "✊ Камень",
        "scissors": "✌️ Ножницы",
        "paper": "🖐 Бумага",
    }
    wins = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock",
    }

    user_choice = callback.data.removeprefix("rps_")

    if user_choice not in choices:
        await callback.answer("Не удалось распознать выбор.", show_alert=True)
        return

    bot_choice = random.choice(list(choices))

    if user_choice == bot_choice:
        result = "🤝 Ничья!"
    elif wins[user_choice] == bot_choice:
        result = "🎉 Ты победил!"
    else:
        result = "😢 Бот победил!"

    await callback.answer()
    await callback.message.answer(
        f"Ты: {choices[user_choice]}\n"
        f"Бот: {choices[bot_choice]}\n\n"
        f"<b>{result}</b>",
        parse_mode="HTML",
    )


# ==================== ВИКТОРИНА ====================

async def send_quiz(message: Message):
    question = random.choice(QUIZ_QUESTIONS)

    buttons = [
        [
            InlineKeyboardButton(
                text=option,
                callback_data=f"quiz_{question['answer']}_{index}",
            )
        ]
        for index, option in enumerate(question["options"])
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"❓ <b>Викторина</b>\n\n{question['q']}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "game_quiz")
async def start_quiz_callback(callback: CallbackQuery):
    await callback.answer()
    await send_quiz(callback.message)


@router.message(Command("quiz"))
async def start_quiz_command(message: Message):
    await send_quiz(message)


@router.callback_query(F.data.startswith("quiz_"))
async def quiz_answer(callback: CallbackQuery):
    try:
        _, correct_text, chosen_text = callback.data.split("_")
        correct = int(correct_text)
        chosen = int(chosen_text)
    except (ValueError, AttributeError):
        await callback.answer("Не удалось проверить ответ.", show_alert=True)
        return

    if chosen == correct:
        await callback.answer("🎉 Правильно!", show_alert=True)
        await callback.message.answer(
            f"✅ <b>{html.escape(callback.from_user.first_name)}</b> ответил правильно!",
            parse_mode="HTML",
        )
    else:
        await callback.answer("❌ Неверно!", show_alert=True)


# ==================== ПРАВДА ИЛИ ДЕЙСТВИЕ ====================

async def send_truth_or_dare(message: Message):
    await message.answer(
        "🎭 <b>Правда или действие?</b>\n\nВыбирай:",
        reply_markup=tod_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "game_tod")
async def start_tod_callback(callback: CallbackQuery):
    await callback.answer()
    await send_truth_or_dare(callback.message)


@router.message(Command("truth_or_dare"))
async def start_tod_command(message: Message):
    await send_truth_or_dare(message)


@router.callback_query(F.data.startswith("tod_"))
async def tod_result(callback: CallbackQuery):
    name = html.escape(callback.from_user.first_name)

    if callback.data == "tod_truth":
        await callback.answer()
        question = random.choice(TRUTH_QUESTIONS)
        await callback.message.answer(
            f"😇 <b>Правда для {name}:</b>\n\n{question}",
            parse_mode="HTML",
        )
    elif callback.data == "tod_dare":
        await callback.answer()
        task = random.choice(DARE_TASKS)
        await callback.message.answer(
            f"😈 <b>Действие для {name}:</b>\n\n{task}",
            parse_mode="HTML",
        )
    else:
        await callback.answer("Не удалось распознать выбор.", show_alert=True)


# ==================== ШАР ПРЕДСКАЗАНИЙ ====================

@router.callback_query(F.data == "game_8ball")
async def ball_from_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🔮 Задай вопрос командой:\n"
        "<code>/ball Буду ли я богат?</code>",
        parse_mode="HTML",
    )


@router.message(Command("ball"))
async def cmd_ball(message: Message):
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "🔮 Задай вопрос. Например:\n"
            "<code>/ball Буду ли я богат?</code>",
            parse_mode="HTML",
        )
        return

    question = html.escape(parts[1])
    answer = random.choice(BALL_ANSWERS)

    await message.answer(
        f"🔮 <b>Вопрос:</b> {question}\n\n"
        f"🎱 <b>Ответ:</b> {answer}",
        parse_mode="HTML",
    )
