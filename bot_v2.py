import os
import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

MAX_ROUNDS = 7
MIN_PLAYERS = 6

DISCUSSION_SECONDS = 60
VOTE_SECONDS = 15

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
    "Лікар", "Хірург", "Медсестра", "Інженер", "Електрик", "Механік", "Кухар", "Фермер",
    "Військовий", "Рятувальник", "Психолог", "Вчитель", "Біолог", "Хімік", "Програміст", "Будівельник",
]
HEALTH = ["Здоровий", "Астма", "Діабет", "Слабкий зір", "Гіпертонія", "Після травми", "Імунодефіцит (легкий)"]
HOBBY = ["Риболовля", "Виживання", "Кулінарія", "Спорт", "Шахи", "Медицина", "Ремонт техніки", "Садівництво"]
PHOBIA = ["Клаустрофобія", "Арахнофобія", "Страх висоти", "Страх темряви", "Соціофобія", "Без фобій"]
BIG_INV = ["Портативний генератор", "Медичний набір", "Набір інструментів", "Міні-теплиця", "Рація", "Запаси палива"]
BAG = ["Аптечка", "Фільтр води", "Ніж", "Запальничка", "Ліхтарик", "Консерви", "Мотузка", "Батарейки"]
EXTRA = ["Знає 3 мови", "Має карту місцевості", "Колишній волонтер", "Вміє шити", "Знає першу допомогу", "Колишній спортсмен"]
SPEC = ["Може вилікувати 1 раз", "Може перекинути 1 голос", "Може врятувати 1 гравця від вильоту", "Може змінити катаклізм (1 раз)"]

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

class Phase(str, Enum):
    LOBBY = "lobby"
    ROUND_START = "round_start"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"
    SPEECHES = "speeches"
    VOTE = "vote"
    JUSTIFY = "justify"
    FINISH = "finish"

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

    vote_open: bool = False
    votes: Dict[int, int] = field(default_factory=dict)  # voter -> target
    silent_offenders: Set[int] = field(default_factory=set)

    justified_this_round: Set[int] = field(default_factory=set)
    justify_candidates: List[int] = field(default_factory=list)

    cards: Dict[int, Dict[str, str]] = field(default_factory=dict)
    revealed_total: Dict[int, int] = field(default_factory=dict)  # скільки всього відкрив у приваті

    lobby_message_id: Optional[int] = None

    timer_task: Optional[asyncio.Task] = None

    players: Dict[int, Player] = field(default_factory=dict)

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

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID_ENV = (os.getenv("OWNER_ID") or "").strip()
OWNER_ID = int(OWNER_ID_ENV) if OWNER_ID_ENV.isdigit() else None

if not TOKEN:
    raise RuntimeError("Немає BOT_TOKEN у .env")

bot = Bot(TOKEN)
dp = Dispatcher()

def is_owner(user_id: Optional[int]) -> bool:
    return OWNER_ID is not None and user_id == OWNER_ID

def is_host(game: Game, user_id: Optional[int]) -> bool:
    return user_id is not None and game.host_id == user_id

def blocked_by_pause_for_message(game: Game, message: Message) -> bool:

    if not game.paused:
        return False
    uid = message.from_user.id if message.from_user else None
    if is_owner(uid) and (message.text or "").strip().startswith("/resume"):
        return False

    if is_owner(uid) and (message.text or "").strip().startswith("/"):

        return True
    return True

def blocked_by_pause_for_callback(game: Game, call: CallbackQuery) -> bool:
    if not game.paused:
        return False
    uid = call.from_user.id if call.from_user else None
    return not is_owner(uid)

async def cancel_timer(game: Game):
    if game.timer_task and not game.timer_task.done():
        game.timer_task.cancel()
    game.timer_task = None

def kb_lobby() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Приєднатись", callback_data="lobby:join")
    kb.adjust(1)
    return kb.as_markup()

def kb_vote(game: Game) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    alive = game.alive_players()
    for i, p in enumerate(alive, start=1):
        kb.button(text=f"{i}. {p.tag()}", callback_data=f"vote:{p.user_id}")
    kb.adjust(1)
    return kb.as_markup()

def kb_dm_reveal(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🃏 Відкрити характеристику", callback_data=f"dm:reveal:{chat_id}")
    kb.adjust(1)
    return kb.as_markup()

def lobby_text(game: Game) -> str:
    return (
        "🧩 Лобі.\n\n"
        f"Гравців: {len(game.players)}\n"
        f"{game.roster_text(only_alive=False)}\n\n"
    )

async def update_lobby(chat_id: int, game: Game):
    if game.lobby_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.lobby_message_id,
                text=lobby_text(game),
                reply_markup=kb_lobby(),
            )
            return
        except Exception:
            pass

    msg = await bot.send_message(chat_id, lobby_text(game), reply_markup=kb_lobby())
    game.lobby_message_id = msg.message_id


async def ensure_dm_open(user_id: int) -> bool:
    try:
        await bot.send_message(user_id, "✅ Приват відкрито. Під час гри я надішлю тобі картку.")
        return True
    except Exception:
        return False


async def deal_cards(chat_id: int, game: Game):
    game.cards.clear()
    game.revealed_total.clear()

    for pid in game.players.keys():
        game.cards[pid] = random_card()
        game.revealed_total[pid] = 0

    for pid in game.players.keys():
        try:
            await bot.send_message(
                pid,
                "🧾 Твоя картка персонажа (приватно).\n\n"
                "Натискай кнопку, щоб відкрити характеристику.\n"
                "⚠️ Відкривай рівно стільки, скільки потрібно у раунді.",
                reply_markup=kb_dm_reveal(chat_id)
            )
        except Exception:
            pass

def can_reveal_in_round(game: Game, user_id: int) -> Tuple[bool, str]:
    need = game.reveal_plan[game.round_no - 1] if game.round_no >= 1 else 0
    if need <= 0:
        return False, "У цьому раунді відкривати характеристики не потрібно."

    already_should_have = sum(game.reveal_plan[: game.round_no - 1])
    total = game.revealed_total.get(user_id, 0)
    revealed_this_round = max(0, total - already_should_have)
    if revealed_this_round >= need:
        return False, f"Ти вже відкрив {need} характеристик у цьому раунді."
    return True, ""

def next_unrevealed(game: Game, user_id: int) -> Optional[Tuple[str, str]]:
    total = game.revealed_total.get(user_id, 0)
    if total >= len(CARD_KEYS_ORDER):
        return None
    return CARD_KEYS_ORDER[total] 

async def post_intro(chat_id: int, game: Game):
    await bot.send_message(
        chat_id,
        "☢️ СИРЕНИ. ПАНІКА. ПОПІЛ НА НЕБІ.\n\n"
        f"Катаклізм: {game.catastrophe}\n\n"
        f"{game.bunker_desc}\n"
        f"👁 Місць у бункері: {game.slots} із {len(game.players)}.\n"
        "Ті, хто не потрапить — загинуть.\n\n"
        "📩 Картки роздано в ЛС."
    )

async def apply_silence_penalty(game: Game):
    for pid in game.silent_offenders:
        p = game.players.get(pid)
        if p and p.alive:
            p.skip_speech_next_round = True

def count_votes_with_absent_as_self(game: Game) -> Dict[int, int]:
    alive_ids = game.alive_ids()
    counts: Dict[int, int] = {pid: 0 for pid in alive_ids}

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

async def start_discussion_timer(chat_id: int, game: Game):
    await cancel_timer(game)
    game.timer_task = asyncio.create_task(_discussion_timer(chat_id, game))

async def _discussion_timer(chat_id: int, game: Game):
    await asyncio.sleep(DISCUSSION_SECONDS)
    if not game.active or game.paused:
        return

    game.phase = Phase.SPEECHES
    await bot.send_message(
        chat_id,
        "⏱ 1 хв обговорення минула.\n"
        "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
        "Кожному по 30 секунд у тому ж порядку.\n"
        "Після виступів — /openvote"
    )

async def start_vote_timer(chat_id: int, game: Game):
    await cancel_timer(game)
    game.timer_task = asyncio.create_task(_vote_timer(chat_id, game))

async def _vote_timer(chat_id: int, game: Game):
    await asyncio.sleep(VOTE_SECONDS)
    if not game.active or game.paused:
        return
    if game.vote_open:

        await close_vote_internal(chat_id, game, forced_by_timer=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    if message.chat.type == "private":
        await message.answer("✅ Готово. Тепер я можу писати тобі в ЛС. Повернись у групу 🙂")
        return

    await message.answer(
        "🏚 BUNKER UA BOT\n\n"
        "• /new — створити лобі\n"
        "• /players — гравці\n"
        "• /leave — вийти\n"
        "• /startgame — старт\n"
        "• /next — рух етапів (хост)\n"
        "• /openvote — голосування (хост)\n"
        "• /closevote — закрити (хост)\n"
        "• /force_next — примусово перескочити етап (хост/OWNER)\n"
        "• /pause, /resume (OWNER)\n"
        "• /end — завершити гру\n"
    )

@dp.message(Command("new"))
async def cmd_new(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    if message.chat.type == "private":
        await message.answer("Створи лобі у групі 🙂")
        return

    game.__dict__.update(Game().__dict__)
    game.owner_id = OWNER_ID
    await update_lobby(message.chat.id, game)

@dp.message(Command("players"))
async def cmd_players(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    if message.chat.type == "private":
        await message.answer("Ця команда працює у групі.")
        return
    await message.answer("👥 Гравці:\n" + game.roster_text(only_alive=False))

@dp.message(Command("leave"))
async def cmd_leave(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    if message.chat.type == "private":
        await message.answer("Ця команда працює у групі.")
        return

    if game.active:
        await message.answer("Гра вже стартувала — вийти не можна.")
        return

    u = message.from_user
    if not u:
        return

    if u.id not in game.players:
        await message.answer("Тебе немає в лобі. Натисни «➕ Приєднатись».")
        return

    tag = game.players[u.id].tag()
    del game.players[u.id]
    await message.answer(f"❌ {tag} вийшов. Гравців: {len(game.players)}")
    await update_lobby(message.chat.id, game)

@dp.message(Command("startgame"))
async def cmd_startgame(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    if message.chat.type == "private":
        await message.answer("Стартуй гру в групі 🙂")
        return

    if game.active:
        await message.answer("Гра вже йде.")
        return

    if len(game.players) < MIN_PLAYERS:
        await message.answer(f"Потрібно мінімум {MIN_PLAYERS} гравців.")
        return

    u = message.from_user
    if not u:
        return

    if game.host_id is None:
        game.host_id = u.id

    if not (is_host(game, u.id) or is_owner(u.id)):
        await message.answer("Стартувати може тільки хост або OWNER.")
        return

    missing = []
    for pid in list(game.players.keys()):
        ok = await ensure_dm_open(pid)
        if not ok:
            missing.append(pid)
    if missing:
        await message.answer("⚠️ Дехто не відкрив ЛС. Нехай натиснуть /start у приваті з ботом і повтори /startgame.")
        return

    game.active = True
    game.catastrophe = random.choice(CATASTROPHES)
    game.bunker_desc = build_bunker_desc()
    game.slots = bunker_slots(len(game.players))
    game.reveal_plan = reveals_per_round(len(game.players))

    game.round_no = 1
    game.clockwise = True
    game.pending_elims_this_round = 1
    game.skipped_vote_in_round1 = False

    for p in game.players.values():
        p.alive = True
        p.skip_speech_next_round = False

    game.votes.clear()
    game.silent_offenders.clear()
    game.justified_this_round.clear()
    game.justify_candidates.clear()
    game.vote_open = False

    game.make_round_order()
    game.phase = Phase.ROUND_START

    await post_intro(message.chat.id, game)
    await deal_cards(message.chat.id, game)

    await message.answer(
        f"Раунд 1.\n"
        f"Напрямок: за годинниковою.\n"
        f"Кожен відкриває у ЛС і озвучує: {game.reveal_plan[0]} характеристик (включно з професією).\n\n"
        "Починаємо етапи: /next"
    )

@dp.message(Command("pause"))
async def cmd_pause(message: Message):
    game = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    game.paused = True
    await cancel_timer(game)
    await message.answer("⏸ Пауза: бот мовчить для всіх. Тільки OWNER може /resume.")

@dp.message(Command("resume"))
async def cmd_resume(message: Message):
    game = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    game.paused = False
    await message.answer("▶️ Відновлено.")

@dp.message(Command("end"))
async def cmd_end(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    await cancel_timer(game)
    game.__dict__.update(Game().__dict__)
    await message.answer("🏁 Гру завершено. /new щоб почати знову.")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    if not game.active:
        await message.answer("Немає активної гри. /new → кнопка «Приєднатись» → /startgame")
        return

    await message.answer(
        f"📌 Стан гри:\n"
        f"Раунд: {game.round_no}/{MAX_ROUNDS}\n"
        f"Фаза: {game.phase}\n"
        f"Живі: {len(game.alive_ids())} | Місць: {game.slots}\n"
        f"Голосування відкрите: {'так' if game.vote_open else 'ні'}\n\n"
        f"👥 Живі:\n{game.roster_text(True)}"
    )

@dp.message(Command("force_next"))
async def cmd_force_next(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    u = message.from_user
    if not u:
        return
    if not game.active:
        await message.answer("Немає активної гри.")
        return
    if not (is_host(game, u.id) or is_owner(u.id)):
        await message.answer("Тільки хост/OWNER може /force_next.")
        return

    await cancel_timer(game)

    if game.phase == Phase.PRESENTATION:
        game.phase = Phase.DISCUSSION
        await message.answer("💬 Етап 2: КОЛЕКТИВНЕ ОБГОВОРЕННЯ (60с, авто).")
        await start_discussion_timer(message.chat.id, game)
        return

    if game.phase == Phase.DISCUSSION:
        game.phase = Phase.SPEECHES
        await message.answer(
            "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
            "Кожному по 30 секунд.\n"
            "Після виступів — /openvote"
        )
        return

    if game.phase == Phase.SPEECHES:
        await message.answer("Відкривай голосування: /openvote")
        return

    if game.phase == Phase.VOTE:
        await close_vote_internal(message.chat.id, game, forced_by_timer=False)
        return

    await message.answer("Нема куди перескочити з цього етапу.")

@dp.message(Command("next"))
async def cmd_next(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    u = message.from_user
    if not u:
        return
    if not game.active:
        await message.answer("Гра не стартувала.")
        return
    if not (is_host(game, u.id) or is_owner(u.id)):
        await message.answer("Тільки хост/OWNER може /next.")
        return

    if game.need_finish():
        game.phase = Phase.FINISH
        await message.answer(f"🏁 ФІНАЛ.\nПереможці:\n{game.roster_text(True)}")
        game.active = False
        return

    if game.phase in (Phase.ROUND_START, Phase.PRESENTATION):
        game.phase = Phase.PRESENTATION
        order_tags = [game.players[pid].tag() for pid in game.order if game.players.get(pid) and game.players[pid].alive]
        need = game.reveal_plan[game.round_no - 1]
        await message.answer(
            f"🎙 Раунд {game.round_no}. Етап 1: ПРЕЗЕНТАЦІЯ.\n"
            "Кожному — 1 хвилина (ви самі контролюєте).\n"
            f"У цьому раунді відкрий у ЛС і озвуч: {need} характеристик.\n\n"
            f"Порядок: {', '.join(order_tags)}\n\n"
            "Коли всі виступили — /next"
        )
        return

    if game.phase == Phase.DISCUSSION:

        await cancel_timer(game)
        game.phase = Phase.SPEECHES
        await message.answer(
            "⏭ Обговорення завершено раніше.\n"
            "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
            "Кожному по 30 секунд.\n"
            "Після виступів — /openvote"
        )
        return

    if game.phase == Phase.PRESENTATION:
        game.phase = Phase.DISCUSSION
        await message.answer(f"💬 Етап 2: КОЛЕКТИВНЕ ОБГОВОРЕННЯ.\n{DISCUSSION_SECONDS} секунд (авто).")
        await start_discussion_timer(message.chat.id, game)
        return

    if game.phase == Phase.SPEECHES:
        await message.answer("Після промов відкрий голосування: /openvote")
        return

    if game.phase == Phase.VOTE:
        await message.answer("Голосування вже йде. Воно закриється автоматично або /closevote.")
        return

    await message.answer("Немає наступного етапу. /status")

@dp.message(Command("openvote"))
async def cmd_openvote(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    u = message.from_user
    if not u:
        return
    if not game.active:
        await message.answer("Гра не стартувала.")
        return
    if not (is_host(game, u.id) or is_owner(u.id)):
        await message.answer("Відкрити голосування може тільки хост/OWNER.")
        return
    if game.vote_open:
        await message.answer("Голосування вже відкрите.")
        return

    await cancel_timer(game)

    game.phase = Phase.VOTE
    game.vote_open = True
    game.votes.clear()
    game.silent_offenders.clear()

    await message.answer(
        f"🗳 ГОЛОСУВАННЯ ({VOTE_SECONDS} сек, авто).\n"
        "Тиша! Будь-які повідомлення = штраф.\n"
        "Натисни кнопку, щоб проголосувати 👇",
        reply_markup=kb_vote(game)
    )

    await start_vote_timer(message.chat.id, game)

@dp.message(Command("closevote"))
async def cmd_closevote(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return

    u = message.from_user
    if not u:
        return
    if not game.active:
        await message.answer("Гра не стартувала.")
        return
    if not (is_host(game, u.id) or is_owner(u.id)):
        await message.answer("Закривати голосування може тільки хост/OWNER.")
        return
    if not game.vote_open:
        await message.answer("Немає відкритого голосування.")
        return

    await cancel_timer(game)
    await close_vote_internal(message.chat.id, game, forced_by_timer=False)

@dp.callback_query(F.data == "lobby:join")
async def cb_join(call: CallbackQuery):
    if call.message is None:
        return
    game = get_game(call.message.chat.id)
    if blocked_by_pause_for_callback(game, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if call.message.chat.type == "private":
        await call.answer("Гра працює у групі 🙂", show_alert=True)
        return

    if game.active:
        await call.answer("Гра вже йде.", show_alert=True)
        return

    u = call.from_user
    if u.id in game.players:
        await call.answer("Ти вже в лобі ✅", show_alert=False)
        return

    game.players[u.id] = Player(user_id=u.id, name=u.full_name, username=(u.username or ""))
    await call.answer("✅ Додано", show_alert=False)
    await update_lobby(call.message.chat.id, game)

@dp.callback_query(F.data.startswith("dm:reveal:"))
async def cb_dm_reveal(call: CallbackQuery):
    if call.message is None:
        return

    chat_id = int(call.data.split(":")[2])
    game = get_game(chat_id)

    if blocked_by_pause_for_callback(game, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if not game.active:
        await call.answer("Гри немає.", show_alert=True)
        return

    uid = call.from_user.id
    if uid not in game.players or not game.players[uid].alive:
        await call.answer("Ти не у грі.", show_alert=True)
        return

    ok, reason = can_reveal_in_round(game, uid)
    if not ok:
        await call.answer("Не можна", show_alert=False)
        await call.message.answer(reason)
        return

    nxt = next_unrevealed(game, uid)
    if not nxt:
        await call.answer("Все відкрито", show_alert=False)
        await call.message.answer("Усі характеристики вже відкриті.")
        return

    title, key = nxt
    value = game.cards[uid][key]
    game.revealed_total[uid] = game.revealed_total.get(uid, 0) + 1

    await call.answer("✅", show_alert=False)
    await call.message.answer(f"✅ Відкрито: {title} — {value}")

@dp.callback_query(F.data.startswith("vote:"))
async def cb_vote(call: CallbackQuery):
    if call.message is None:
        return
    game = get_game(call.message.chat.id)

    if blocked_by_pause_for_callback(game, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if not game.active or not game.vote_open:
        await call.answer("Зараз немає відкритого голосування.", show_alert=True)
        return

    voter_id = call.from_user.id
    if voter_id not in game.players or not game.players[voter_id].alive:
        await call.answer("Голосують лише живі гравці.", show_alert=True)
        return

    try:
        target_id = int(call.data.split(":")[1])
    except Exception:
        await call.answer("Помилка голосу.", show_alert=True)
        return

    if target_id not in game.players or not game.players[target_id].alive:
        await call.answer("Цей гравець вже не в грі.", show_alert=True)
        return

    if target_id == voter_id:
        await call.answer("Сам за себе не можна 😈", show_alert=True)
        return

    game.votes[voter_id] = target_id
    target_tag = game.players[target_id].tag()
    await call.answer(f"✅ Ти проголосував за {target_tag}", show_alert=False)

@dp.message(F.text)
async def any_text(message: Message):
    game = get_game(message.chat.id)
    if blocked_by_pause_for_message(game, message):
        return
    if not game.active:
        return

    if game.vote_open:
        txt = (message.text or "").strip()
        if not txt.startswith("/"):
            u = message.from_user
            if u and u.id in game.players and game.players[u.id].alive:
                game.silent_offenders.add(u.id)

                try:
                    await message.reply("⚠️ Тиша під час голосування! Штраф у наступному раунді.")
                except Exception:
                    pass

async def close_vote_internal(chat_id: int, game: Game, forced_by_timer: bool):
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
        "📊 Голоси зібрано.\n"
        + ("(авто-таймер)\n" if forced_by_timer else "")
        + f"{report}\n\n"
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
            f"Кандидати: {tags}\n\n"
            "Після виправдань — /openvote (переголосування)"
        )
        return

    if len(cands) >= 2:
        if game.round_no == 1:
            await bot.send_message(chat_id, "⚠️ Рівність у 1 раунді — можна без вильоту. Йдемо далі.")
            await advance_round(chat_id, game)
            return
        await eliminate(chat_id, game, cands, "Рівність у 2–7 раунді — вилітають всі з максимумом.")
        return

    if len(cands) == 1:
        await eliminate(chat_id, game, [cands[0]], "Після виправдання — виліт за максимумом.")
        return

async def eliminate(chat_id: int, game: Game, kicked_ids: List[int], reason: str):
    for kid in kicked_ids:
        if kid in game.players:
            game.players[kid].alive = False

    tags = ", ".join(game.players[k].tag() for k in kicked_ids if k in game.players)

    await bot.send_message(
        chat_id,
        "🚪 Двері бункера скриплять…\n"
        f"Причина: {reason}\n\n"
        f"❌ Вигнано: {tags}\n\n"
        "🕯 Прощальна промова: 15 секунд."
    )

    if game.need_finish():
        game.phase = Phase.FINISH
        await bot.send_message(chat_id, f"🏁 ФІНАЛ.\nПереможці:\n{game.roster_text(True)}")
        game.active = False
        return

    await advance_round(chat_id, game)

async def advance_round(chat_id: int, game: Game):
    if game.round_no >= MAX_ROUNDS:
        game.phase = Phase.FINISH
        await bot.send_message(chat_id, "⚠️ Максимум раундів. Фінал за місцями.")
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

    await bot.send_message(
        chat_id,
        f"🔁 Раунд {game.round_no}.\n"
        f"Напрямок: {'за годинниковою' if game.clockwise else 'проти годинникової'}.\n"
        f"Кожен відкриває у ЛС і озвучує: {game.reveal_plan[game.round_no-1]} характеристик.\n\n"
        "Починаємо: /next"
    )

    game.phase = Phase.ROUND_START

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())