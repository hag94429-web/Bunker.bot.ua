import os
import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv


# ===================== CONFIG =====================

MAX_ROUNDS = 7
MIN_PLAYERS = 6
MAX_PLAYERS = 15

CATASTROPHES = [
    "Ядерна війна ☢️",
    "Пандемія мутованого вірусу 🦠",
    "Повстання ШІ 🤖",
    "Супервулкан 🌋",
    "Астероїдна зима 🌑",
    "Радіаційна буря ⚠️",
    "Глобальний голод 🍞",
    "Тотальний блекаут 🌚",
]

BUNKER_ITEMS = [
    "медблок",
    "генератор",
    "радіостанція",
    "фільтри для води",
    "майстерня з інструментами",
    "склад насіння",
    "запас антибіотиків",
    "книга з виживання",
    "сонячні панелі",
]

SEX = ["Чоловік", "Жінка"]
BODY = ["Худорлявий", "Середньої статури", "Міцний", "Спортивний"]
TRAIT = ["Лідерський", "Емпат", "Цинік", "Оптиміст", "Панікер", "Раціональний", "Хитрий", "Чесний"]
PROF = [
    "Лікар", "Хірург", "Медсестра", "Інженер", "Електрик", "Механік", "Повар", "Фермер",
    "Військовий", "Рятувальник", "Психолог", "Вчитель", "Біолог", "Хімік", "Програміст", "Будівельник",
]
HEALTH = ["Здоровий", "Астма", "Діабет", "Слабкий зір", "Гіпертонія", "Після травми", "Імунодефіцит (легкий)"]
HOBBY = ["Риболовля", "Виживання", "Кулінарія", "Спорт", "Шахи", "Медицина", "Ремонт техніки", "Садівництво"]
PHOBIA = ["Клаустрофобія", "Арахнофобія", "Страх висоти", "Страх темряви", "Соціофобія", "Без фобій"]
BIG_INV = ["Портативний генератор", "Медичний набір", "Набір інструментів", "Міні-теплиця", "Рація", "Зброя-муляж"]
BAG = ["Аптечка", "Фільтр води", "Ніж", "Запальничка", "Ліхтарик", "Консерви", "Мотузка", "Набір батарейок"]
EXTRA = ["Знає 3 мови", "Має карту місцевості", "Колишній волонтер", "Вміє шити", "Знає першу допомогу", "Колишній спортсмен"]
SPEC = ["Може вилікувати 1 раз", "Може перекинути 1 голос", "Може врятувати 1 гравця від вильоту", "Може змінити катаклізм (1 раз)"]


def bunker_slots(n_players: int) -> int:
    return n_players // 2


def reveals_per_round(n_players: int) -> List[int]:
    if n_players == 6:
        base = [3, 3, 2]
        return base + [0] * (MAX_ROUNDS - len(base))
    if n_players in (7, 8):
        base = [3, 2, 2] + [1] * (MAX_ROUNDS - 3)
        return base[:MAX_ROUNDS]
    if n_players in (9, 10):
        base = [3, 2, 1] + [1] * (MAX_ROUNDS - 3)
        return base[:MAX_ROUNDS]
    if n_players in (11, 12):
        base = [2, 2, 1] + [1] * (MAX_ROUNDS - 3)
        return base[:MAX_ROUNDS]
    if 13 <= n_players <= 15:
        base = [2, 1, 1] + [1] * (MAX_ROUNDS - 3)
        return base[:MAX_ROUNDS]
    base = [3, 2, 1] + [1] * (MAX_ROUNDS - 3)
    return base[:MAX_ROUNDS]


def build_bunker_desc() -> str:
    size = random.choice(["220 м²", "350 м²", "480 м²", "600 м²"])
    time_need = random.choice(["6 місяців", "1 рік", "2 роки", "3 роки"])
    food = random.choice(["їжі вистачить із запасом", "їжі впритул", "їжі критично мало", "їжі майже немає"])
    items = ", ".join(random.sample(BUNKER_ITEMS, k=3))
    return (
        f"🏚 Бункер:\n"
        f"• Розмір: {size}\n"
        f"• Час перебування: {time_need}\n"
        f"• Їжа: {food}\n"
        f"• В бункері є: {items}\n"
    )


def percent(part: int, whole: int) -> float:
    return 0.0 if whole <= 0 else (part / whole) * 100.0


# ===================== DB =====================

DB_PATH = "bunker.db"


async def db_init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            username TEXT,
            alive INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            chat_id INTEGER,
            user_id INTEGER,
            key TEXT,
            value TEXT,
            revealed INTEGER,
            PRIMARY KEY (chat_id, user_id, key)
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            chat_id INTEGER PRIMARY KEY,
            active INTEGER,
            paused INTEGER,
            host_id INTEGER,
            owner_id INTEGER,
            phase TEXT,
            round_no INTEGER,
            clockwise INTEGER,
            slots INTEGER,
            catastrophe TEXT,
            bunker_desc TEXT,
            pending_elims INTEGER,
            skipped_vote_round1 INTEGER,
            vote_open INTEGER,
            vote_until_ts REAL
        )""")
        await db.commit()


# ===================== GAME =====================

class Phase(str, Enum):
    LOBBY = "lobby"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"
    SPEECHES = "speeches"
    VOTE = "vote"
    JUSTIFY = "justify"
    FINISH = "finish"


CARD_KEYS_ORDER = [
    ("Професія", "profession"),
    ("Стать", "sex"),
    ("Вік", "age"),
    ("Телосложення", "body"),
    ("Риса характеру", "trait"),
    ("Здоров'я", "health"),
    ("Хобі", "hobby"),
    ("Фобія", "phobia"),
    ("Крупний інвентар", "big_inv"),
    ("Рюкзак", "bag"),
    ("Додаткове", "extra"),
    ("Спецздібність", "spec"),
]


def random_card() -> Dict[str, str]:
    return {
        "profession": random.choice(PROF),
        "sex": random.choice(SEX),
        "age": str(random.randint(18, 65)),
        "body": random.choice(BODY),
        "trait": random.choice(TRAIT),
        "health": random.choice(HEALTH),
        "hobby": random.choice(HOBBY),
        "phobia": random.choice(PHOBIA),
        "big_inv": random.choice(BIG_INV),
        "bag": ", ".join(random.sample(BAG, k=2)),
        "extra": random.choice(EXTRA),
        "spec": random.choice(SPEC),
    }


@dataclass
class Player:
    user_id: int
    name: str
    username: str = ""
    alive: bool = True
    skip_speech_next_round: bool = False

    def tag(self) -> str:
        return f"@{self.username}" if self.username else self.name


@dataclass
class Game:
    active: bool = False
    paused: bool = False
    host_id: Optional[int] = None
    owner_id: Optional[int] = None

    phase: Phase = Phase.LOBBY
    round_no: int = 0
    clockwise: bool = True
    order: List[int] = field(default_factory=list)

    catastrophe: str = ""
    bunker_desc: str = ""
    slots: int = 0
    reveal_plan: List[int] = field(default_factory=list)

    pending_elims_this_round: int = 1
    skipped_vote_in_round1: bool = False

    # voting
    vote_open: bool = False
    vote_until_ts: float = 0.0
    votes: Dict[int, int] = field(default_factory=dict)  # voter -> target
    silent_offenders: Set[int] = field(default_factory=set)

    # justify
    justified_this_round: Set[int] = field(default_factory=set)
    justify_candidates: List[int] = field(default_factory=list)

    players: Dict[int, Player] = field(default_factory=dict)

    # timers (tasks)
    timer_task: Optional[asyncio.Task] = None
    stage_task: Optional[asyncio.Task] = None

    def alive_ids(self) -> List[int]:
        return [pid for pid, p in self.players.items() if p.alive]

    def alive_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.alive]

    def alive_list_index(self) -> List[int]:
        return [p.user_id for p in self.alive_players()]

    def roster_text(self, only_alive: bool = True) -> str:
        plist = self.alive_players() if only_alive else list(self.players.values())
        lines = []
        for i, p in enumerate(plist, start=1):
            status = "" if p.alive else " (вибув)"
            lines.append(f"{i}. {p.tag()}{status}")
        return "\n".join(lines) if lines else "—"

    def make_round_order(self):
        alive = self.alive_list_index()
        self.order = alive[:] if self.clockwise else list(reversed(alive))

    def need_finish(self) -> bool:
        return len(self.alive_ids()) <= self.slots


GAMES: Dict[int, Game] = {}


def get_game(chat_id: int) -> Game:
    if chat_id not in GAMES:
        GAMES[chat_id] = Game()
    return GAMES[chat_id]


# ===================== UI =====================

# ✅ ВАЖЛИВО: "Старт" показуємо завжди, але натиснути зможе тільки хост/owner
def kb_lobby() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Приєднатись", callback_data="lobby:join")
    kb.button(text="➖ Вийти", callback_data="lobby:leave")
    kb.button(text="👥 Гравці", callback_data="lobby:players")
    kb.button(text="▶️ Старт", callback_data="lobby:start")
    kb.adjust(2, 2)
    return kb


def kb_admin() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏸ Pause", callback_data="admin:pause")
    kb.button(text="▶️ Resume", callback_data="admin:resume")
    kb.button(text="⏭ Next", callback_data="admin:next")
    kb.button(text="🛑 Stop", callback_data="admin:stop")
    kb.adjust(2, 2)
    return kb


def kb_vote(game: Game) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    alive = game.alive_players()
    for i, p in enumerate(alive, start=1):
        kb.button(text=f"{i}. {p.tag()}", callback_data=f"vote:{p.user_id}")
    kb.adjust(1)
    return kb


def kb_dm_reveal(chat_id: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🃏 Відкрити характеристику", callback_data=f"dm:reveal:{chat_id}")
    return kb


# ===================== BOT =====================

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID_ENV = os.getenv("OWNER_ID", "").strip()

if not TOKEN:
    raise RuntimeError("Немає BOT_TOKEN у .env")
OWNER_ID = int(OWNER_ID_ENV) if OWNER_ID_ENV.isdigit() else None

bot = Bot(TOKEN)
dp = Dispatcher()


def is_owner(user_id: Optional[int]) -> bool:
    return OWNER_ID is not None and user_id == OWNER_ID


def is_host(game: Game, user_id: Optional[int]) -> bool:
    return user_id is not None and game.host_id == user_id


async def ensure_dm_open(user_id: int) -> bool:
    try:
        await bot.send_message(user_id, "✅ Канал для приватних карт відкрито.")
        return True
    except Exception:
        return False


async def deal_cards(chat_id: int, game: Game):
    async with aiosqlite.connect(DB_PATH) as db:
        for pid, p in game.players.items():
            card = random_card()
            for title, key in CARD_KEYS_ORDER:
                value = card[key]
                await db.execute(
                    "INSERT OR REPLACE INTO cards(chat_id,user_id,key,value,revealed) VALUES(?,?,?,?,?)",
                    (chat_id, pid, key, value, 0)
                )
        await db.commit()

    for pid, p in game.players.items():
        try:
            text = (
                "🧾 Твоя картка персонажа (приватно):\n\n"
                "Ти зможеш відкривати характеристики по одній натискаючи кнопку.\n"
                "⚠️ Не показуй іншим усе одразу.\n"
            )
            await bot.send_message(pid, text, reply_markup=kb_dm_reveal(chat_id).as_markup())
        except Exception:
            pass


async def dm_next_reveal(chat_id: int, user_id: int) -> Tuple[bool, str]:
    game = get_game(chat_id)
    if not game.active:
        return False, "Гра вже не активна."
    if user_id not in game.players or not game.players[user_id].alive:
        return False, "Ти не у грі або вже вибув."

    need = game.reveal_plan[game.round_no - 1] if game.round_no >= 1 else 0
    if need <= 0:
        return False, "У цьому раунді відкривати більше не потрібно."

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM cards WHERE chat_id=? AND user_id=? AND revealed=1",
            (chat_id, user_id)
        )
        revealed_total = (await cur.fetchone())[0]

        expected_before = sum(game.reveal_plan[: game.round_no - 1])
        revealed_this_round = max(0, revealed_total - expected_before)

        if revealed_this_round >= need:
            return False, f"Ти вже відкрив {need} характеристик у цьому раунді."

        for title, key in CARD_KEYS_ORDER:
            cur2 = await db.execute(
                "SELECT value, revealed FROM cards WHERE chat_id=? AND user_id=? AND key=?",
                (chat_id, user_id, key)
            )
            row = await cur2.fetchone()
            if row and row[1] == 0:
                value = row[0]
                await db.execute(
                    "UPDATE cards SET revealed=1 WHERE chat_id=? AND user_id=? AND key=?",
                    (chat_id, user_id, key)
                )
                await db.commit()
                msg = f"✅ Відкрито: **{title}** — {value}"
                return True, msg

    return False, "Усі характеристики вже відкриті."


async def post_round_banner(chat_id: int, game: Game):
    await bot.send_message(
        chat_id,
        "☢️ СИРЕНИ. ПАНІКА. ПОПІЛ НА НЕБІ.\n\n"
        f"Катаклізм: {game.catastrophe}\n\n"
        f"{game.bunker_desc}\n"
        f"👁 Місць у бункері: {game.slots} із {len(game.players)}.\n"
        "Ті, хто не потрапить — загинуть.\n\n"
        "Гра почалась. Таймери і голосування — автоматичні.\n",
        reply_markup=kb_admin().as_markup() if (game.owner_id is not None) else None
    )

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == "private":
        await message.answer("Я працюю у групі. Додай мене в чат і введи /new")
        return
    await message.answer(
        "🏚 BUNKER UA BOT (v2)\n\n"
        "Команди:\n"
        "• /new — лобі\n"
        "• /admin — панель (тільки власник)\n"
        "• /status — статус\n"
        "• /pause /resume — тиша (тільки власник)\n"
        "• /stopgame — стоп (тільки власник)\n"
        "\nЛобі керується кнопками після /new."
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    await message.answer("⚙️ Адмін-меню:", reply_markup=kb_admin().as_markup())

@dp.message(Command("new"))
async def cmd_new(message: Message):
    if message.chat.type == "private":
        await message.answer("Створи лобі у групі 🙂")
        return
    game = get_game(message.chat.id)
    game.__dict__.update(Game().__dict__)
    game.owner_id = OWNER_ID
    game.phase = Phase.LOBBY

    game.host_id = message.from_user.id if message.from_user else None

    host_name = message.from_user.full_name if message.from_user else "—"

    await message.answer(
        "🧩 Лобі створено.\n"
        "Натискай кнопки нижче.\n"
        f"👑 Хост: {host_name}\n",
        reply_markup=kb_lobby().as_markup()
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    game = get_game(message.chat.id)
    if not game.active:
        await message.answer("Немає активної гри. /new")
        return
    await message.answer(
        f"📌 Статус:\n"
        f"Раунд: {game.round_no}/{MAX_ROUNDS}\n"
        f"Фаза: {game.phase}\n"
        f"Живі: {len(game.alive_ids())} | Місць: {game.slots}\n"
        f"Потрібно вигнати: {game.pending_elims_this_round}\n\n"
        f"👥 Живі:\n{game.roster_text(True)}"
    )

@dp.message(Command("pause"))
async def cmd_pause(message: Message):
    game = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    game.paused = True
    await message.answer("⏸ Пауза: бот мовчить для всіх. Тільки /resume від власника працює.")

@dp.message(Command("resume"))
async def cmd_resume(message: Message):
    game = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    game.paused = False
    await message.answer("▶️ Відновлено.")

@dp.message(Command("stopgame"))
async def cmd_stopgame(message: Message):
    game = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    game.__dict__.update(Game().__dict__)
    await message.answer("🛑 Гру зупинено. /new щоб почати знову.")

@dp.callback_query(F.data.startswith("lobby:"))
async def lobby_cb(call: CallbackQuery):
    chat_id = call.message.chat.id
    game = get_game(chat_id)

    if game.paused and not is_owner(call.from_user.id):
        await call.answer("Пауза.", show_alert=False)
        return

    action = call.data.split(":")[1]
    u = call.from_user

    if action == "join":
        if game.active:
            await call.answer("Гра вже йде.", show_alert=True)
            return
        if u.id in game.players:
            await call.answer("Ти вже в лобі.", show_alert=False)
            return
        if len(game.players) >= MAX_PLAYERS:
            await call.answer("Максимум 15 гравців.", show_alert=True)
            return
        game.players[u.id] = Player(user_id=u.id, name=u.full_name, username=(u.username or ""))
        await call.answer("✅ Додано!", show_alert=False)
        await call.message.edit_text(
            "🧩 Лобі.\n\n"
            f"Гравців: {len(game.players)}\n"
            f"{game.roster_text(False)}",
            reply_markup=kb_lobby().as_markup()
        )
        return

    if action == "leave":
        if game.active:
            await call.answer("Гра вже йде.", show_alert=True)
            return
        if u.id not in game.players:
            await call.answer("Тебе нема в лобі.", show_alert=False)
            return
        del game.players[u.id]
        await call.answer("❌ Вийшов.", show_alert=False)
        await call.message.edit_text(
            "🧩 Лобі.\n\n"
            f"Гравців: {len(game.players)}\n"
            f"{game.roster_text(False)}",
            reply_markup=kb_lobby().as_markup()
        )
        return

    if action == "players":
        await call.answer("Ок", show_alert=False)
        await call.message.edit_text(
            "🧩 Лобі.\n\n"
            f"Гравців: {len(game.players)}\n"
            f"{game.roster_text(False)}",
            reply_markup=kb_lobby().as_markup()
        )
        return

    if action == "start":
        if game.active:
            await call.answer("Гра вже йде.", show_alert=True)
            return
        if len(game.players) < MIN_PLAYERS:
            await call.answer("Потрібно мінімум 6 гравців.", show_alert=True)
            return

        if not (is_host(game, u.id) or is_owner(u.id)):
            await call.answer("Стартує тільки хост/власник.", show_alert=True)
            return

        missing_dm = []
        for pid in game.players.keys():
            ok = await ensure_dm_open(pid)
            if not ok:
                missing_dm.append(pid)
        if missing_dm:
            await call.message.answer("⚠️ Дехто не відкрив ЛС з ботом. Нехай натиснуть /start у приваті та спробуй знову.")
            await call.answer("Не всі мають ЛС.", show_alert=True)
            return

        game.active = True
        game.phase = Phase.PRESENTATION
        game.round_no = 1
        game.clockwise = True
        game.catastrophe = random.choice(CATASTROPHES)
        game.bunker_desc = build_bunker_desc()
        game.slots = bunker_slots(len(game.players))
        game.reveal_plan = reveals_per_round(len(game.players))
        game.pending_elims_this_round = 1
        game.skipped_vote_in_round1 = False
        game.vote_open = False
        game.votes.clear()
        game.silent_offenders.clear()
        game.justified_this_round.clear()
        game.justify_candidates.clear()

        for p in game.players.values():
            p.alive = True
            p.skip_speech_next_round = False

        game.make_round_order()

        await call.message.edit_text("✅ Гру стартовано.")
        await post_round_banner(chat_id, game)

        await deal_cards(chat_id, game)
        await bot.send_message(chat_id, "📩 Усім гравцям роздано картки в ЛС. Відкривайте характеристики кнопкою в приваті.")

        await start_presentation_stage(chat_id, game)

        await call.answer("Старт!", show_alert=False)
        return

@dp.callback_query(F.data.startswith("admin:"))
async def admin_cb(call: CallbackQuery):
    chat_id = call.message.chat.id
    game = get_game(chat_id)
    if not is_owner(call.from_user.id):
        await call.answer("Тільки власник.", show_alert=True)
        return

    action = call.data.split(":")[1]
    if action == "pause":
        game.paused = True
        await call.answer("Пауза", show_alert=False)
        await call.message.answer("⏸ Пауза увімкнена.")
        return
    if action == "resume":
        game.paused = False
        await call.answer("Відновлено", show_alert=False)
        await call.message.answer("▶️ Відновлено.")
        return
    if action == "stop":
        game.__dict__.update(Game().__dict__)
        await call.answer("Зупинено", show_alert=False)
        await call.message.answer("🛑 Гру зупинено. /new щоб почати.")
        return
    if action == "next":
        await call.answer("Next", show_alert=False)
        await force_next(chat_id, game)
        return

@dp.callback_query(F.data.startswith("dm:reveal:"))
async def dm_reveal_cb(call: CallbackQuery):
    parts = call.data.split(":")
    chat_id = int(parts[2])
    ok, msg = await dm_next_reveal(chat_id, call.from_user.id)
    await call.answer("Готово" if ok else "Не можна", show_alert=False)
    try:
        await call.message.answer(msg, parse_mode="Markdown")
    except Exception:
        await call.message.answer(msg)

async def cancel_tasks(game: Game):
    for t in [game.timer_task, game.stage_task]:
        if t and not t.done():
            t.cancel()
    game.timer_task = None
    game.stage_task = None

async def start_presentation_stage(chat_id: int, game: Game):
    await cancel_tasks(game)
    game.phase = Phase.PRESENTATION
    order_tags = [game.players[pid].tag() for pid in game.order if game.players.get(pid) and game.players[pid].alive]
    need = game.reveal_plan[game.round_no - 1]
    await bot.send_message(
        chat_id,
        f"🎙 Раунд {game.round_no}. Етап 1: ПРЕЗЕНТАЦІЯ.\n"
        f"Кожному — 1 хвилина (авто-таймер).\n"
        f"Відкрий у цьому раунді: {need} характеристик (у ЛС).\n\n"
        f"Порядок: {', '.join(order_tags)}\n"
        "Бот сам переключить етапи.",
    )
    game.stage_task = asyncio.create_task(run_presentation(chat_id, game))

async def run_presentation(chat_id: int, game: Game):
    for pid in list(game.order):
        if not game.active or game.paused:
            return
        p = game.players.get(pid)
        if not p or not p.alive:
            continue
        await bot.send_message(chat_id, f"⏱ {p.tag()}, твоя хвилина презентації! (60с)")
        await asyncio.sleep(60)

    await start_discussion_stage(chat_id, game)

async def start_discussion_stage(chat_id: int, game: Game):
    await cancel_tasks(game)
    game.phase = Phase.DISCUSSION
    await bot.send_message(
        chat_id,
        "💬 Етап 2: КОЛЕКТИВНЕ ОБГОВОРЕННЯ.\n"
        "Тривалість: 60 секунд (авто)."
    )
    game.stage_task = asyncio.create_task(run_discussion(chat_id, game))

async def run_discussion(chat_id: int, game: Game):
    await asyncio.sleep(60)
    if not game.active or game.paused:
        return
    await start_speeches_stage(chat_id, game)

async def start_speeches_stage(chat_id: int, game: Game):
    await cancel_tasks(game)
    game.phase = Phase.SPEECHES
    await bot.send_message(
        chat_id,
        "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
        "Кожному — 30 секунд (авто).\n"
        "Штраф за тишу під час голосування: пропуск промови у наступному раунді."
    )
    game.stage_task = asyncio.create_task(run_speeches(chat_id, game))

async def run_speeches(chat_id: int, game: Game):
    for pid in list(game.order):
        if not game.active or game.paused:
            return
        p = game.players.get(pid)
        if not p or not p.alive:
            continue
        if p.skip_speech_next_round:
            await bot.send_message(chat_id, f"🚫 {p.tag()} пропускає промову (штраф).")
            p.skip_speech_next_round = False
            await asyncio.sleep(2)
            continue
        await bot.send_message(chat_id, f"⏱ {p.tag()}, 30 секунд на промову!")
        await asyncio.sleep(30)

    await open_vote(chat_id, game)

async def open_vote(chat_id: int, game: Game):
    await cancel_tasks(game)
    game.phase = Phase.VOTE
    game.vote_open = True
    game.votes.clear()
    game.silent_offenders.clear()
    game.vote_until_ts = time.time() + 15

    await bot.send_message(
        chat_id,
        "🗳 ГОЛОСУВАННЯ (15 секунд).\n"
        "Тиша! Будь-які повідомлення = штраф.\n"
        "Обери кого вигнати кнопкою:",
        reply_markup=kb_vote(game).as_markup()
    )

    game.stage_task = asyncio.create_task(run_vote_timer(chat_id, game))


async def run_vote_timer(chat_id: int, game: Game):
    await asyncio.sleep(15)
    if not game.active or game.paused:
        return
    if game.vote_open:
        await close_vote(chat_id, game)


async def apply_silence_penalty(game: Game):
    for pid in game.silent_offenders:
        p = game.players.get(pid)
        if p and p.alive:
            p.skip_speech_next_round = True


def count_votes_with_absent_as_self(game: Game) -> Dict[int, int]:
    alive_ids = game.alive_ids()
    counts = {pid: 0 for pid in alive_ids}
    for voter_id in alive_ids:
        if voter_id in game.votes and game.votes[voter_id] in counts:
            counts[game.votes[voter_id]] += 1
        else:
            counts[voter_id] += 1
    return counts


def top_candidates(counts: Dict[int, int]) -> Tuple[List[int], int]:
    if not counts:
        return [], 0
    mx = max(counts.values())
    cands = [pid for pid, c in counts.items() if c == mx]
    return cands, mx

async def close_vote(chat_id: int, game: Game):
    game.vote_open = False
    await apply_silence_penalty(game)

    alive_count = len(game.alive_ids())
    counts = count_votes_with_absent_as_self(game)
    cands, mx = top_candidates(counts)
    mx_pct = percent(mx, alive_count)

    lines = []
    for pid, c in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"{game.players[pid].tag()}: {c}")
    report = "\n".join(lines)

    await bot.send_message(
        chat_id,
        "📊 Голоси зібрано:\n"
        f"{report}\n\n"
        f"Максимум: {mx} голосів ({mx_pct:.1f}%)."
    )

    if len(cands) == 1 and mx_pct >= 70.0:
        await eliminate(chat_id, game, [cands[0]], "70%+ голосів — без виправдання.")
        return

    need_justify = [pid for pid in cands if pid not in game.justified_this_round]
    if need_justify:
        game.phase = Phase.JUSTIFY
        game.justify_candidates = need_justify[:]
        for pid in need_justify:
            game.justified_this_round.add(pid)

        tags = ", ".join(game.players[pid].tag() for pid in need_justify)
        await bot.send_message(
            chat_id,
            "⚖️ ВИПРАВДАННЯ.\n"
            "Кандидати мають 30 секунд.\n"
            "⚠️ Заборонено розкривати характеристики!\n\n"
            f"Кандидати: {tags}\n"
            "Після 30с буде переголосування автоматично."
        )
        await asyncio.sleep(30)
        if not game.active or game.paused:
            return
        await open_vote(chat_id, game)
        return

    if len(cands) >= 2:
        if game.round_no == 1:
            await bot.send_message(chat_id, "⚠️ Рівність після виправдань. У 1 раунді можна без вильоту — переходимо далі.")
            await advance_round(chat_id, game)
            return
        else:
            await eliminate(chat_id, game, cands, "Рівність у 2–7 раунді — вилітають всі з максимумом.")
            return

    if len(cands) == 1:
        await eliminate(chat_id, game, [cands[0]], "Після виправдання — виліт за максимумом.")
        return

async def eliminate(chat_id: int, game: Game, kicked_ids: List[int], reason: str):
    for kid in kicked_ids:
        if kid in game.players:
            game.players[kid].alive = False

    game.pending_elims_this_round -= len(kicked_ids)
    if game.pending_elims_this_round < 0:
        game.pending_elims_this_round = 0

    tags = ", ".join(game.players[k].tag() for k in kicked_ids if k in game.players)

    await bot.send_message(
        chat_id,
        "🚪 Двері бункера скриплять…\n"
        f"Причина: {reason}\n\n"
        f"❌ Вигнано: {tags}\n\n"
        "🕯 Прощальна промова: 15 секунд (авто)."
    )
    await asyncio.sleep(15)

    if game.pending_elims_this_round > 0 and not game.need_finish():
        await bot.send_message(chat_id, f"⚠️ Треба вигнати ще: {game.pending_elims_this_round}. Починаю голосування.")
        await open_vote(chat_id, game)
        return

    if game.need_finish():
        game.phase = Phase.FINISH
        await bot.send_message(
            chat_id,
            "🏁 ФІНАЛ.\n"
            f"Переможці (в бункері):\n{game.roster_text(True)}\n\n"
            "Гру завершено."
        )
        game.active = False
        return

    await advance_round(chat_id, game)

async def advance_round(chat_id: int, game: Game):
    if game.round_no >= MAX_ROUNDS:
        game.phase = Phase.FINISH
        await bot.send_message(chat_id, "⚠️ Досягнуто максимум раундів. Фінал за місцями.")
        await bot.send_message(chat_id, f"Переможці:\n{game.roster_text(True)}")
        game.active = False
        return

    game.round_no += 1
    game.clockwise = not game.clockwise
    game.make_round_order()

    game.votes.clear()
    game.silent_offenders.clear()
    game.justified_this_round.clear()
    game.justify_candidates.clear()

    if game.round_no == 2 and game.skipped_vote_in_round1:
        game.pending_elims_this_round = 2
    else:
        game.pending_elims_this_round = 1

    await bot.send_message(
        chat_id,
        f"🔁 Раунд {game.round_no}.\n"
        f"Напрямок: {'за годинниковою' if game.clockwise else 'проти годинникової'}.\n"
        f"Кожен відкриває: {game.reveal_plan[game.round_no-1]} характеристик (в ЛС)."
    )
    await start_presentation_stage(chat_id, game)

async def force_next(chat_id: int, game: Game):
    if not game.active:
        await bot.send_message(chat_id, "Немає активної гри.")
        return
    if game.phase == Phase.PRESENTATION:
        await start_discussion_stage(chat_id, game)
    elif game.phase == Phase.DISCUSSION:
        await start_speeches_stage(chat_id, game)
    elif game.phase == Phase.SPEECHES:
        await open_vote(chat_id, game)
    elif game.phase == Phase.VOTE:
        await close_vote(chat_id, game)
    else:
        await bot.send_message(chat_id, "Немає наступного етапу.")

@dp.callback_query(F.data.startswith("vote:"))
async def vote_cb(call: CallbackQuery):
    chat_id = call.message.chat.id
    game = get_game(chat_id)

    if game.paused and not is_owner(call.from_user.id):
        await call.answer("Пауза.", show_alert=False)
        return

    if not game.active or not game.vote_open:
        await call.answer("Зараз не голосуємо.", show_alert=False)
        return

    voter = call.from_user.id
    if voter not in game.players or not game.players[voter].alive:
        await call.answer("Лише живі.", show_alert=True)
        return

    target_id = int(call.data.split(":")[1])
    if target_id == voter:
        await call.answer("Сам себе? Ні 😈", show_alert=True)
        return
    if target_id not in game.players or not game.players[target_id].alive:
        await call.answer("Ціль неактивна.", show_alert=True)
        return

    game.votes[voter] = target_id
    await call.answer("✅ Голос зараховано", show_alert=False)

@dp.message(F.text)
async def any_text(message: Message):
    game = get_game(message.chat.id)

    if game.paused and not is_owner(message.from_user.id if message.from_user else None):
        return

    if not game.active:
        return

    if game.vote_open:
        txt = (message.text or "").strip()
        if not txt.startswith("/"):
            u = message.from_user
            if u and u.id in game.players and game.players[u.id].alive:
                game.silent_offenders.add(u.id)

async def main():
    await db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())