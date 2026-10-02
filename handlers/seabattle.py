"""
🚢 Морской бой — два игрока, расстановка в ЛС, стрельба в группе.

Поле 7×7  (A‑G, 1‑7).
Корабли: 1×3, 2×2, 3×1 (итого 10 палуб).

Расстановка: игрок пишет боту В ЛИЧКУ координаты в формате:
  А1 А2 А3      — трёхпалубный
  Б5 В5         — двухпалубный №1
  Г2 Д2         — двухпалубный №2
  Е7            — однопалубный №1
  Ж4            — однопалубный №2
  Г6            — однопалубный №3

Стрельба: игрок пишет координату В ГРУППЕ, например  В3
"""

import copy
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import seabattle_join_keyboard

router = Router()

# ================== КОНСТАНТЫ ==================

BOARD_SIZE = 7

# Буквы для столбцов (русские)
COL_LETTERS = ["А", "Б", "В", "Г", "Д", "Е", "Ж"]

# Альтернативные написания (англ. раскладка и варианты)
LETTER_MAP = {
    "А": 0, "A": 0,
    "Б": 1, "B": 1,
    "В": 2,
    "Г": 3, "G": 3,
    "Д": 4, "D": 4,
    "Е": 5, "E": 5,
    "Ж": 6,
}

# Какие корабли нужно расставить
SHIP_SIZES = [3, 2, 2, 1, 1, 1]
TOTAL_DECKS = sum(SHIP_SIZES)   # 10

# Символы для отрисовки
WATER = "🟦"
SHIP = "🟩"
HIT = "🟥"
MISS = "⬜"
HIDDEN = "🟦"

# ================== ХРАНИЛИЩЕ ИГР ==================

# Лобби (ожидание второго игрока)
# {chat_id: {"player1": user_id, "msg_id": message_id}}
lobbies = {}

# Активные игры
# {chat_id: SeaBattleGame}
games = {}

# Расстановка кораблей (пока игрок ставит в ЛС)
# {user_id: SetupSession}
setup_sessions = {}


# ================== КЛАССЫ ==================

class PlayerBoard:
    """Доска одного игрока."""

    def __init__(self):
        # 0=вода, 1=корабль, 2=попадание, 3=промах
        self.board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.ships_cells = set()       # клетки с кораблями
        self.hits = set()              # клетки с попаданиями
        self.misses = set()            # клетки с промахами
        self.ships = []                # список кораблей [{cells}, {cells}, ...]

    def place_ship(self, cells: list[tuple[int, int]]) -> str | None:
        """Ставит корабль. Возвращает текст ошибки или None."""
        size = len(cells)

        # Проверяем, что клетки идут в ряд
        rows = sorted(set(r for r, c in cells))
        cols = sorted(set(c for r, c in cells))

        if len(rows) > 1 and len(cols) > 1:
            return "Корабль должен быть горизонтальным или вертикальным (не по диагонали)!"

        if len(rows) == 1:
            if cols != list(range(min(cols), min(cols) + size)):
                return "Клетки корабля должны идти подряд без пропусков!"
        else:
            if rows != list(range(min(rows), min(rows) + size)):
                return "Клетки корабля должны идти подряд без пропусков!"

        # Проверяем границы
        for r, c in cells:
            if r < 0 or r >= BOARD_SIZE or c < 0 or c >= BOARD_SIZE:
                return "Координаты выходят за пределы поля!"

        # Проверяем, что не пересекаются и не касаются других кораблей
        for r, c in cells:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                        if (nr, nc) in self.ships_cells and (nr, nc) not in cells:
                            return "Корабли не должны касаться друг друга (даже по диагонали)!"

        # Ставим
        cell_set = set()
        for r, c in cells:
            self.board[r][c] = 1
            self.ships_cells.add((r, c))
            cell_set.add((r, c))

        self.ships.append(cell_set)
        return None

    def shoot(self, r: int, c: int) -> str:
        """Стреляет в клетку. Возвращает: 'miss', 'hit', 'kill', 'already'."""
        if (r, c) in self.hits or (r, c) in self.misses:
            return "already"

        if (r, c) in self.ships_cells:
            self.hits.add((r, c))
            self.board[r][c] = 2
            # Проверяем, убит ли корабль
            for ship in self.ships:
                if (r, c) in ship:
                    if ship.issubset(self.hits):
                        return "kill"
                    return "hit"
            return "hit"
        else:
            self.misses.add((r, c))
            self.board[r][c] = 3
            return "miss"

    def all_sunk(self) -> bool:
        return self.ships_cells == self.hits

    def render_own(self) -> str:
        """Показывает свою доску (видны свои корабли)."""
        header = "    " + "  ".join(COL_LETTERS[:BOARD_SIZE])
        lines = [header]
        for r in range(BOARD_SIZE):
            row_str = f" {r + 1}  "
            for c in range(BOARD_SIZE):
                val = self.board[r][c]
                if val == 0:
                    row_str += WATER + " "
                elif val == 1:
                    row_str += SHIP + " "
                elif val == 2:
                    row_str += HIT + " "
                elif val == 3:
                    row_str += MISS + " "
            lines.append(row_str)
        return "\n".join(lines)

    def render_enemy(self) -> str:
        """Показывает доску врага (корабли скрыты)."""
        header = "    " + "  ".join(COL_LETTERS[:BOARD_SIZE])
        lines = [header]
        for r in range(BOARD_SIZE):
            row_str = f" {r + 1}  "
            for c in range(BOARD_SIZE):
                val = self.board[r][c]
                if val == 0 or val == 1:
                    row_str += HIDDEN + " "
                elif val == 2:
                    row_str += HIT + " "
                elif val == 3:
                    row_str += MISS + " "
            lines.append(row_str)
        return "\n".join(lines)


class SetupSession:
    """Сессия расстановки кораблей в ЛС."""

    def __init__(self, user_id: int, chat_id: int):
        self.user_id = user_id
        self.chat_id = chat_id
        self.board = PlayerBoard()
        self.ships_to_place = list(SHIP_SIZES)  # [3, 2, 2, 1, 1, 1]
        self.current_index = 0

    def current_ship_size(self) -> int | None:
        if self.current_index >= len(self.ships_to_place):
            return None
        return self.ships_to_place[self.current_index]

    def is_done(self) -> bool:
        return self.current_index >= len(self.ships_to_place)


class SeaBattleGame:
    """Активная игра в группе."""

    def __init__(self, chat_id: int, p1_id: int, p2_id: int,
                 p1_name: str, p2_name: str,
                 p1_board: PlayerBoard, p2_board: PlayerBoard):
        self.chat_id = chat_id
        self.players = {p1_id: p1_name, p2_id: p2_name}
        self.boards = {p1_id: p1_board, p2_id: p2_board}   # Своя доска
        self.targets = {p1_id: p2_board, p2_id: p1_board}   # Доска противника
        self.turn = p1_id                                     # Кто сейчас ходит
        self.p1_id = p1_id
        self.p2_id = p2_id

    def switch_turn(self):
        if self.turn == self.p1_id:
            self.turn = self.p2_id
        else:
            self.turn = self.p1_id


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

def parse_coord(text: str) -> tuple[int, int] | None:
    """Парсит 'А1' / 'Б5' / 'в3' в (row, col). Возвращает None при ошибке."""
    text = text.strip().upper()
    if len(text) < 2 or len(text) > 2:
        return None

    letter = text[0]
    digit = text[1]

    if letter not in LETTER_MAP:
        return None
    if not digit.isdigit():
        return None

    col = LETTER_MAP[letter]
    row = int(digit) - 1

    if row < 0 or row >= BOARD_SIZE or col < 0 or col >= BOARD_SIZE:
        return None

    return (row, col)


def parse_cells(text: str) -> list[tuple[int, int]] | None:
    """Парсит 'А1 А2 А3' в [(0,0), (0,1), (0,2)]."""
    parts = text.strip().split()
    cells = []
    for p in parts:
        coord = parse_coord(p)
        if coord is None:
            return None
        cells.append(coord)
    return cells if cells else None


def coord_to_text(r: int, c: int) -> str:
    return f"{COL_LETTERS[c]}{r + 1}"


def ships_description() -> str:
    return (
        "Расставьте корабли на поле <b>7×7</b> (столбцы А–Ж, строки 1–7).\n\n"
        "Флот:\n"
        "• 1 корабль на <b>3 клетки</b> (трёхпалубный)\n"
        "• 2 корабля на <b>2 клетки</b> (двухпалубные)\n"
        "• 3 корабля на <b>1 клетку</b> (однопалубные)\n\n"
        "Корабли не должны касаться друг друга (даже по диагонали).\n\n"
        "<b>Формат ввода:</b> отправьте координаты клеток корабля через пробел.\n"
        "Пример для трёхпалубного: <code>А1 А2 А3</code>\n"
        "Пример для однопалубного: <code>Г5</code>"
    )


# ================== СТАРТ ИГРЫ В ГРУППЕ ==================

@router.message(Command("seabattle"))
async def cmd_seabattle(message: Message):
    chat_id = message.chat.id

    if chat_id in games:
        await message.answer("⚓ В этом чате уже идёт морской бой! Дождитесь окончания.")
        return

    if chat_id in lobbies:
        await message.answer("⚓ Набор игроков уже начат! Нажмите кнопку ниже, чтобы присоединиться.")
        return

    user = message.from_user
    lobbies[chat_id] = {"player1": user.id, "player1_name": user.first_name}

    await message.answer(
        f"🚢 <b>Морской бой!</b>\n\n"
        f"⚓ <b>{user.first_name}</b> ищет соперника!\n\n"
        f"Нажмите кнопку ниже, чтобы вступить в бой.\n\n"
        f"<i>⚠️ Убедитесь, что вы написали боту в ЛС хотя бы раз "
        f"(откройте @{(await message.bot.get_me()).username} и нажмите Start), "
        f"иначе бот не сможет отправить вам сообщение для расстановки кораблей.</i>",
        reply_markup=seabattle_join_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "game_seabattle")
async def start_seabattle_from_menu(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.message.chat.id

    if chat_id in games:
        await callback.message.answer("⚓ В этом чате уже идёт морской бой!")
        return

    if chat_id in lobbies:
        await callback.message.answer("⚓ Набор уже начат! Нажмите кнопку ниже.")
        return

    user = callback.from_user
    lobbies[chat_id] = {"player1": user.id, "player1_name": user.first_name}

    await callback.message.answer(
        f"🚢 <b>Морской бой!</b>\n\n"
        f"⚓ <b>{user.first_name}</b> ищет соперника!\n\n"
        f"Нажмите кнопку ниже, чтобы вступить в бой.\n\n"
        f"<i>⚠️ Убедитесь, что вы написали боту в ЛС хотя бы раз "
        f"(откройте бота и нажмите Start).</i>",
        reply_markup=seabattle_join_keyboard(),
        parse_mode="HTML"
    )


# ================== ПРИСОЕДИНЕНИЕ ==================

@router.callback_query(F.data == "sb_join")
async def sb_join(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    chat_id = callback.message.chat.id
    user = callback.from_user

    if chat_id not in lobbies:
        await callback.message.answer("Лобби не найдено. Начните новую игру: /seabattle")
        return

    lobby = lobbies[chat_id]

    if user.id == lobby["player1"]:
        await callback.answer("Вы уже в игре! Ждём второго игрока.", show_alert=True)
        return

    # Второй игрок присоединился
    p1_id = lobby["player1"]
    p1_name = lobby["player1_name"]
    p2_id = user.id
    p2_name = user.first_name

    del lobbies[chat_id]

    # Создаём сессии расстановки для обоих
    setup_sessions[p1_id] = SetupSession(p1_id, chat_id)
    setup_sessions[p2_id] = SetupSession(p2_id, chat_id)

    await callback.message.answer(
        f"⚔️ <b>Бой принят!</b>\n\n"
        f"🔴 Игрок 1: <b>{p1_name}</b>\n"
        f"🔵 Игрок 2: <b>{p2_name}</b>\n\n"
        f"📩 Я отправил каждому сообщение в ЛС для расстановки кораблей.\n"
        f"Как только оба расставят — бой начнётся здесь, в группе!",
        parse_mode="HTML"
    )

    # Отправляем каждому в ЛС инструкцию
    ship_text = ships_description()
    for pid, pname in [(p1_id, p1_name), (p2_id, p2_name)]:
        session = setup_sessions[pid]
        size = session.current_ship_size()
        try:
            await bot.send_message(
                pid,
                f"🚢 <b>Морской бой — Расстановка кораблей</b>\n\n"
                f"{ship_text}\n\n"
                f"🎯 Сейчас поставьте корабль на <b>{size} клетки</b>.\n\n"
                f"{session.board.render_own()}",
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.answer(
                f"❌ Не могу написать игроку <b>{pname}</b> в ЛС!\n"
                f"Пожалуйста, откройте бота в личке и нажмите <b>Start</b>, затем начните заново: /seabattle",
                parse_mode="HTML"
            )
            # Отменяем
            setup_sessions.pop(p1_id, None)
            setup_sessions.pop(p2_id, None)
            return


# ================== РАССТАНОВКА КОРАБЛЕЙ В ЛС ==================

@router.message(F.chat.type == "private")
async def private_message_handler(message: Message, bot: Bot):
    user_id = message.from_user.id

    if user_id not in setup_sessions:
        return

    session = setup_sessions[user_id]

    if session.is_done():
        await message.answer("✅ Вы уже расставили все корабли! Ждём второго игрока.")
        return

    size = session.current_ship_size()

    # Парсим координаты
    cells = parse_cells(message.text)
    if cells is None:
        await message.answer(
            f"❌ Не могу распознать координаты.\n"
            f"Введите <b>{size}</b> координат через пробел.\n"
            f"Пример: <code>{'  '.join(f'{COL_LETTERS[i]}1' for i in range(size))}</code>",
            parse_mode="HTML"
        )
        return

    if len(cells) != size:
        await message.answer(
            f"❌ Сейчас нужен корабль на <b>{size}</b> клеток, а вы ввели {len(cells)}.",
            parse_mode="HTML"
        )
        return

    # Ставим корабль
    error = session.board.place_ship(cells)
    if error:
        await message.answer(f"❌ {error}\nПопробуйте ещё раз.", parse_mode="HTML")
        return

    session.current_index += 1
    placed_text = ", ".join(coord_to_text(r, c) for r, c in cells)

    if session.is_done():
        await message.answer(
            f"✅ Корабль ({placed_text}) установлен!\n\n"
            f"🎉 <b>Все корабли расставлены!</b> Ждём второго игрока...\n\n"
            f"Ваше поле:\n{session.board.render_own()}",
            parse_mode="HTML"
        )

        # Проверяем, оба ли готовы
        await check_both_ready(session.chat_id, bot)
    else:
        next_size = session.current_ship_size()
        remaining = session.ships_to_place[session.current_index:]
        remaining_text = ", ".join(str(s) for s in remaining)

        await message.answer(
            f"✅ Корабль ({placed_text}) установлен!\n\n"
            f"Осталось поставить: [{remaining_text}]\n"
            f"🎯 Поставьте корабль на <b>{next_size}</b> клеток.\n\n"
            f"Ваше поле:\n{session.board.render_own()}",
            parse_mode="HTML"
        )


async def check_both_ready(chat_id: int, bot: Bot):
    """Проверяет, оба ли игрока расставили корабли."""
    # Ищем обе сессии для этого чата
    players = [uid for uid, s in setup_sessions.items() if s.chat_id == chat_id]

    if len(players) < 2:
        return

    sessions = [setup_sessions[p] for p in players]

    if not all(s.is_done() for s in sessions):
        return  # Кто-то ещё не закончил

    # Оба готовы — создаём игру!
    p1_id = players[0]
    p2_id = players[1]
    p1_board = setup_sessions[p1_id].board
    p2_board = setup_sessions[p2_id].board

    # Имена из бота
    try:
        p1_chat = await bot.get_chat(p1_id)
        p1_name = p1_chat.first_name or "Игрок 1"
    except Exception:
        p1_name = "Игрок 1"
    try:
        p2_chat = await bot.get_chat(p2_id)
        p2_name = p2_chat.first_name or "Игрок 2"
    except Exception:
        p2_name = "Игрок 2"

    game = SeaBattleGame(chat_id, p1_id, p2_id, p1_name, p2_name, p1_board, p2_board)
    games[chat_id] = game

    # Чистим сессии расстановки
    del setup_sessions[p1_id]
    del setup_sessions[p2_id]

    await bot.send_message(
        chat_id,
        f"⚔️ <b>Морской бой начинается!</b>\n\n"
        f"🔴 {p1_name} vs 🔵 {p2_name}\n\n"
        f"Первым стреляет: <b>{p1_name}</b>\n\n"
        f"Пишите координаты выстрела прямо в чат (например: <code>В3</code>)",
        parse_mode="HTML"
    )


# ================== СТРЕЛЬБА В ГРУППЕ ==================

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_shot_handler(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id not in games:
        return

    game = games[chat_id]

    # Проверяем, что пишет участник игры
    if user_id not in game.players:
        return

    # Проверяем, что это его ход
    if user_id != game.turn:
        return

    # Парсим координату
    coord = parse_coord(message.text)
    if coord is None:
        return  # Не координата — игнорируем

    r, c = coord
    target_board = game.targets[user_id]
    result = target_board.shoot(r, c)

    shooter_name = game.players[user_id]
    opponent_id = game.p1_id if user_id == game.p2_id else game.p2_id
    opponent_name = game.players[opponent_id]
    cell_name = coord_to_text(r, c)

    if result == "already":
        await message.reply("🔁 Вы уже стреляли в эту клетку! Выберите другую.")
        return

    elif result == "miss":
        await message.reply(
            f"💨 <b>{shooter_name}</b> стреляет в <b>{cell_name}</b> — Мимо!\n\n"
            f"Теперь ходит: <b>{opponent_name}</b>\n\n"
            f"Поле {opponent_name}:\n{target_board.render_enemy()}",
            parse_mode="HTML"
        )
        game.switch_turn()

    elif result == "hit":
        await message.reply(
            f"🔥 <b>{shooter_name}</b> стреляет в <b>{cell_name}</b> — Попадание!\n\n"
            f"🎯 <b>{shooter_name}</b> стреляет ещё раз!\n\n"
            f"Поле {opponent_name}:\n{target_board.render_enemy()}",
            parse_mode="HTML"
        )
        # При попадании ход не переходит!

    elif result == "kill":
        if target_board.all_sunk():
            # Победа!
            await message.reply(
                f"💥 <b>{shooter_name}</b> стреляет в <b>{cell_name}</b> — Убил!\n\n"
                f"🏆🏆🏆 <b>{shooter_name} ПОБЕДИЛ!</b> 🏆🏆🏆\n\n"
                f"Все корабли {opponent_name} потоплены!\n\n"
                f"Поле {opponent_name}:\n{target_board.render_enemy()}",
                parse_mode="HTML"
            )
            del games[chat_id]
        else:
            await message.reply(
                f"💥 <b>{shooter_name}</b> стреляет в <b>{cell_name}</b> — Корабль потоплен!\n\n"
                f"🎯 <b>{shooter_name}</b> стреляет ещё раз!\n\n"
                f"Поле {opponent_name}:\n{target_board.render_enemy()}",
                parse_mode="HTML"
            )
            # При убийстве ход тоже не переходит!


# ================== ОТМЕНА ИГРЫ ==================

@router.message(Command("cancel_battle"))
async def cmd_cancel_battle(message: Message):
    chat_id = message.chat.id

    cancelled = False
    if chat_id in lobbies:
        del lobbies[chat_id]
        cancelled = True

    if chat_id in games:
        del games[chat_id]
        cancelled = True

    # Чистим сессии расстановки для этого чата
    to_del = [uid for uid, s in setup_sessions.items() if s.chat_id == chat_id]
    for uid in to_del:
        del setup_sessions[uid]

    if cancelled or to_del:
        await message.answer("🏳️ Морской бой отменён!")
    else:
        await message.answer("Сейчас нет активных морских боёв в этом чате.")

GAME_URL = "https://kristinamhk.github.io/seabattle-game/"


@router.message(Command("play_seabattle"))
async def send_html_game(message: Message):
    await message.answer_game(game_short_name="seabattle")


@router.callback_query(F.game_short_name == "seabattle")
async def open_html_game(callback: CallbackQuery):
    url = f"{GAME_URL}?user_id={callback.from_user.id}"
    await callback.answer(url=url)
