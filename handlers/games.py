import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import games_keyboard, rps_keyboard, tod_keyboard

router = Router()

# Хранилище активных игр в чатах {chat_id: {"type": ..., "answer": ...}}
active_games = {}

# ==================== ДАННЫЕ ДЛЯ КРОКОДИЛА ====================
CROCODILE_WORDS = [
    {"word": "компьютер", "description": "Электронный мозг на вашем столе. У него есть мышь, но она не ест сыр, и клавиатура, на которой часто спит кот."},
    {"word": "холодильник", "description": "Белый шкаф на кухне, внутри которого всегда темно, пока не откроешь дверь. Ночью к нему совершаются тайные набеги."},
    {"word": "кофе", "description": "Горячий темный напиток, который превращает вас из сонного зомби в человека по утрам."},
    {"word": "пылесос", "description": "Домашний шумный зверь, который питается исключительно пылью и мелкими вещами, случайно упавшими на пол."},
    {"word": "будильник", "description": "Самый ненавистный гаджет по утрам, который хочется разбить об стену, когда он начинает издавать противные звуки."},
    {"word": "зонт", "description": "Складная портативная крыша на палочке, которую вы всегда забываете дома именно в тот день, когда начинается сильный ливень."},
    {"word": "кошка", "description": "Пушистый хозяин квартиры, который спит 18 часов в сутки, требует еду в 5 утра и презирает ваши попытки потискать его."},
    {"word": "пицца", "description": "Круглое итальянское блюдо, которое доставляют в квадратной коробке, а нарезают треугольниками."},
    {"word": "чемодан", "description": "Пластиковый или тканевый ящик на колесиках, на котором приходится прыгать всей семьей, чтобы он наконец застегнулся перед отпуском."},
    {"word": "телевизор", "description": "Большой черный прямоугольник на стене, который работает фоном и разговаривает сам с собой, пока вы залипаете в телефоне."},
    {"word": "арбуз", "description": "Огромный зеленый шар в полосочку с красной сахарной внутренностью и кучей черных семечек, который все обожают есть в конце лета."},
    {"word": "велосипед", "description": "Двухколесный транспорт, который едет только тогда, когда вы крутите педали, и на котором очень больно учиться кататься в детстве."}
]

QUIZ_QUESTIONS = [
    {"q": "Какая планета самая большая в Солнечной системе?", "options": ["Марс", "Юпитер", "Сатурн", "Нептун"], "answer": 1},
    {"q": "Сколько костей в теле взрослого человека?", "options": ["186", "206", "256", "306"], "answer": 1},
    {"q": "Какой элемент обозначается символом 'O'?", "options": ["Золото", "Осмий", "Кислород", "Олово"], "answer": 2},
    {"q": "В каком году человек впервые побывал на Луне?", "options": ["1965", "1969", "1972", "1959"], "answer": 1},
    {"q": "Какая страна самая большая по площади?", "options": ["Канада", "Китай", "США", "Россия"], "answer": 3},
    {"q": "Сколько цветов в радуге?", "options": ["5", "6", "7", "8"], "answer": 2},
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
    "Напиши следующее сообщение в группу только с помощью эмодзи 😜",
    "Расскажи любую шутку. Если никто не поставит лайк — ещё одну 😂",
    "Напиши приятный комплимент любому участнику чата 💕",
]

BALL_ANSWERS = [
    "Определённо да ✅", "Без сомнений 💯", "Можешь быть уверен 😎", "Скорее всего 👍",
    "Знаки говорят — да 🔮", "Пока не ясно, спроси позже ⏳", "Мой ответ — нет ❌",
    "Весьма сомнительно 😬", "Не рассчитывай на это 💔", "Однозначно нет 🚫"
]

# ==================== МЕНЮ ИГР ====================
@router.message(Command("games"))
async def cmd_games(message: Message):
    await message.answer("🎮 *Игровое меню Sib.Bear*\n\nВыбери игру:", reply_markup=games_keyboard(), parse_mode="Markdown")


# ==================== УГАДАЙ ЧИСЛО ====================
@router.callback_query(F.data == "game_guess_number")
async def start_guess_number_cb(callback: CallbackQuery):
    await callback.answer()
    await _start_guess_number(callback.message)


@router.message(Command("guess_number"))
async def start_guess_number_cmd(message: Message):
    await _start_guess_number(message)


async def _start_guess_number(msg: Message):
    answer = random.randint(1, 100)
    active_games[msg.chat.id] = {"type": "number", "answer": answer}
    await msg.answer("🎯 Я загадал число от <b>1 до 100</b>.\nПишите числа в чат, чтобы угадать!", parse_mode="HTML")


# ==================== ИГРА КРОКОДИЛ (Вместо Угадай Слово) ====================
@router.callback_query(F.data == "game_guess_word")
async def start_crocodile_cb(callback: CallbackQuery):
    await callback.answer()
    await _start_crocodile(callback.message)


@router.message(Command("guess_word"))
@router.message(Command("crocodile"))
async def start_crocodile_cmd(message: Message):
    await _start_crocodile(message)


async def _start_crocodile(msg: Message):
    word_data = random.choice(CROCODILE_WORDS)
    active_games[msg.chat.id] = {"type": "crocodile", "answer": word_data["word"]}
    await msg.answer(
        f"🐊 <b>Игра «Крокодил» началась!</b>\n\n"
        f"Я объясняю слово:\n"
        f"💬 <i>«{word_data['description']}»</i>\n\n"
        f"Пишите ваши догадки (одним словом) прямо в чат группы!",
        parse_mode="HTML"
    )


# ==================== ОБРАБОТЧИК ДЛЯ ИГР В ЧАТЕ (Числа и Крокодил) ====================
@router.message(F.text)
async def chat_games_handler(message: Message):
    chat_id = message.chat.id
    if chat_id not in active_games:
        return

    game = active_games[chat_id]
    user_text = message.text.strip().lower()

    # Проверка для угадывания чисел
    if game["type"] == "number":
        if user_text.isdigit():
            guess = int(user_text)
            answer = game["answer"]
            if guess == answer:
                del active_games[chat_id]
                await message.reply(f"🎉 <b>{message.from_user.first_name}</b> угадал число! Это было <b>{answer}</b>!", parse_mode="HTML")
            elif guess < answer:
                await message.reply("⬆️ Больше!")
            else:
                await message.reply("⬇️ Меньше!")

    # Проверка для Крокодила
    elif game["type"] == "crocodile":
        correct_word = game["answer"].strip().lower()
        if user_text == correct_word:
            del active_games[chat_id]
            await message.reply(
                f"🎉 Поздравляем! <b>{message.from_user.first_name}</b> угадал слово!\n"
                f"🐊 Загаданное слово: <b>{correct_word.upper()}</b>!",
                parse_mode="HTML"
            )


# ==================== КАМЕНЬ НОЖНИЦЫ БУМАГА ====================
@router.callback_query(F.data == "game_rps")
async def start_rps_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("✊✌️🖐 <b>Камень, Ножницы, Бумага!</b>\n\nВыбери свой знак:", reply_markup=rps_keyboard(), parse_mode="HTML")


@router.message(Command("rps"))
async def start_rps_cmd(message: Message):
    await message.answer("✊✌️🖐 <b>Камень, Ножницы, Бумага!</b>\n\nВыбери свой знак:", reply_markup=rps_keyboard(), parse_mode="HTML")


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
    await callback.message.answer(f"Ты: {choices[user_choice]}\nБот: {choices[bot_choice]}\n\n<b>{result}</b>", parse_mode="HTML")


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
    await msg.answer(f"❓ <b>Викторина</b>\n\n{q['q']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.callback_query(F.data.startswith("quiz_"))
async def quiz_answer(callback: CallbackQuery):
    parts = callback.data.split("_")
    correct = int(parts[1])
    chosen = int(parts[2])

    if chosen == correct:
        await callback.answer("🎉 Правильно!", show_alert=True)
        await callback.message.answer(f"✅ <b>{callback.from_user.first_name}</b> ответил правильно!")
    else:
        await callback.answer("❌ Неверно!", show_alert=True)
        await callback.message.answer(f"❌ <b>{callback.from_user.first_name}</b> ошибся!")


# ==================== ПРАВДА ИЛИ ДЕЙСТВИЕ ====================
@router.callback_query(F.data == "game_tod")
async def start_tod_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🎭 <b>Правда или Действие?</b>\n\nВыбирай:", reply_markup=tod_keyboard(), parse_mode="HTML")


@router.message(Command("truth_or_dare"))
async def start_tod_cmd(message: Message):
    await message.answer("🎭 <b>Правда или Действие?</b>\n\nВыбирай:", reply_markup=tod_keyboard(), parse_mode="HTML")


@router.callback_query(F.data.startswith("tod_"))
async def tod_result(callback: CallbackQuery):
    await callback.answer()
    name = callback.from_user.first_name
    if callback.data == "tod_truth":
        q = random.choice(TRUTH_QUESTIONS)
        await callback.message.answer(f"😇 <b>Правда для {name}:</b>\n\n{q}", parse_mode="HTML")
    else:
        d = random.choice(DARE_TASKS)
        await callback.message.answer(f"😈 <b>Действие для {name}:</b>\n\n{d}", parse_mode="HTML")


# ==================== ШАР ПРЕДСКАЗАНИЙ ====================
@router.callback_query(F.data == "game_8ball")
async def ball_from_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("🔮 Задай вопрос командой:\n<code>/ball &lt;твой вопрос&gt;</code>", parse_mode="HTML")


@router.message(Command("ball"))
async def cmd_ball(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔮 Задай вопрос! Например:\n<code>/ball Буду ли я богат?</code>", parse_mode="HTML")
        return

    answer = random.choice(BALL_ANSWERS)
    await message.answer(f"🔮 <b>Вопрос:</b> {args[1]}\n\n🎱 <b>Ответ:</b> {answer}", parse_mode="HTML")

