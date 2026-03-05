import os
import json
import asyncio
import random
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    ChatMemberAdministrator,
    ChatMemberOwner,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

SETTINGS_FILE = Path("settings.json")

DEFAULT_SETTINGS = {
    "t_turn": 60,           
    "t_vote": 15,         
    "t_register": 120,      
    "t_warning": 5,         
    "t_discussion": 60,    
    "t_briefing": 20,      

    
    "anonymous_vote": True,         
    "show_cards_on_elim_default": False,  
    "min_players": 6,
    "max_players": 15,
    "slots_mode": "half_floor",     
}

def _load_all_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_all_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_chat_settings(chat_id: int) -> dict:
    all_s = _load_all_settings()
    s = all_s.get(str(chat_id), {})
    merged = DEFAULT_SETTINGS.copy()
    merged.update(s)
    return merged

def set_chat_settings(chat_id: int, new_settings: dict) -> None:
    all_s = _load_all_settings()
    all_s[str(chat_id)] = new_settings
    _save_all_settings(all_s)


MAX_ROUNDS = 7

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
SPEC = ["Може вилікувати 1 раз", "Може перекинути 1 голос", "Може врятувати 1 гравця", "Може змінити катаклізм (1 раз)"]

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

def bunker_slots(n_players: int, slots_mode: str) -> int:
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

class Phase(str, Enum):
    LOBBY = "lobby"
    BRIEFING = "briefing"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"
    SPEECHES = "speeches"
    VOTE = "vote"
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

    phase: Phase = Phase.LOBBY
    round_no: int = 0
    clockwise: bool = True
    order: List[int] = field(default_factory=list)

    host_id: Optional[int] = None

    catastrophe: str = ""
    bunker_desc: str = ""
    slots: int = 0
    reveal_plan: List[int] = field(default_factory=list)

    lobby_open: bool = True
    lobby_message_id: Optional[int] = None

    timer_task: Optional[asyncio.Task] = None

    vote_open: bool = False
    votes: Dict[int, int] = field(default_factory=dict)  
    silent_offenders: Set[int] = field(default_factory=set)

    cards: Dict[int, Dict[str, str]] = field(default_factory=dict)
    revealed_total: Dict[int, int] = field(default_factory=dict)

    last_elim_id: Optional[int] = None

    players: Dict[int, Player] = field(default_factory=dict)

    settings: dict = field(default_factory=dict)

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

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")
if not TOKEN:
    raise RuntimeError("Немає BOT_TOKEN у .env")
if OWNER_ID <= 0:
    raise RuntimeError("Немає OWNER_ID у .env або він некоректний")

bot = Bot(TOKEN)
dp = Dispatcher()

def get_game(chat_id: int) -> Game:
    if chat_id not in GAMES:
        g = Game()
        g.settings = get_chat_settings(chat_id)
        GAMES[chat_id] = g
    return GAMES[chat_id]

def is_owner(user_id: Optional[int]) -> bool:
    return user_id is not None and user_id == OWNER_ID

async def is_admin_or_owner(chat_id: int, user_id: int) -> bool:
    if is_owner(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception:
        return False

def blocked_by_pause_for_message(g: Game, message: Message) -> bool:
    if not g.paused:
        return False
    uid = message.from_user.id if message.from_user else None
    if is_owner(uid) and (message.text or "").strip().startswith("/resume"):
        return False
    return True

def blocked_by_pause_for_callback(g: Game, call: CallbackQuery) -> bool:
    if not g.paused:
        return False
    uid = call.from_user.id
    return not is_owner(uid)

async def cancel_timer(g: Game):
    if g.timer_task and not g.timer_task.done():
        g.timer_task.cancel()
    g.timer_task = None

def kb_lobby() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Приєднатись", callback_data="lobby:join")
    kb.adjust(1)
    return kb.as_markup()

def kb_vote_private(chat_id: int, g: Game) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, p in enumerate(g.alive_players(), start=1):
        kb.button(text=f"{i}. {p.tag()}", callback_data=f"vote:{chat_id}:{p.user_id}")
    kb.adjust(1)
    return kb.as_markup()

def kb_dm_reveal(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🃏 Відкрити характеристику", callback_data=f"dm:reveal:{chat_id}")
    kb.adjust(1)
    return kb.as_markup()

def kb_reveal_elim(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Так, показати", callback_data=f"elimreveal:yes:{user_id}")
    kb.button(text="❌ Ні, не показувати", callback_data=f"elimreveal:no:{user_id}")
    kb.adjust(1)
    return kb.as_markup()

def lobby_text(g: Game) -> str:
    s = g.settings
    return (
        "🧩 Лобі.\n\n"
        f"Статус: {'відкрите ✅' if g.lobby_open else 'закрите ⛔'}\n"
        f"Гравців: {len(g.players)}\n"
        f"{g.roster_text(only_alive=False)}\n\n"
        "Кнопка: ➕ Приєднатись\n\n"
        f"⏱ Реєстрація: {s.get('t_register', 120)}с | "
        f"Ознайомлення: {s.get('t_briefing', 20)}с | "
        f"Обговорення: {s.get('t_discussion', 60)}с | "
        f"Голосування: {s.get('t_vote', 15)}с\n\n"
    )

async def update_lobby(chat_id: int, g: Game):
    if g.lobby_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=g.lobby_message_id,
                text=lobby_text(g),
                reply_markup=kb_lobby()
            )
            return
        except Exception:
            pass
    msg = await bot.send_message(chat_id, lobby_text(g), reply_markup=kb_lobby())
    g.lobby_message_id = msg.message_id

def kb_settings_main(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏱ Таймери", callback_data=f"set:{chat_id}:timers")
    kb.button(text="📜 Загальні правила", callback_data=f"set:{chat_id}:rules")
    kb.button(text="✅ Готово (зберегти)", callback_data=f"set:{chat_id}:save")
    kb.adjust(1)
    return kb.as_markup()

def kb_settings_timers(chat_id: int, s: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    kb.button(text=f"🎙 Хід: {s['t_turn']}с", callback_data="noop")
    kb.button(text="−10", callback_data=f"set:{chat_id}:t_turn:-10")
    kb.button(text="−5", callback_data=f"set:{chat_id}:t_turn:-5")
    kb.button(text="+5", callback_data=f"set:{chat_id}:t_turn:+5")
    kb.button(text="+10", callback_data=f"set:{chat_id}:t_turn:+10")

    kb.button(text=f"🗳 Голосування: {s['t_vote']}с", callback_data="noop")
    kb.button(text="−10", callback_data=f"set:{chat_id}:t_vote:-10")
    kb.button(text="−5", callback_data=f"set:{chat_id}:t_vote:-5")
    kb.button(text="+5", callback_data=f"set:{chat_id}:t_vote:+5")
    kb.button(text="+10", callback_data=f"set:{chat_id}:t_vote:+10")

    kb.button(text=f"🧩 Реєстрація: {s['t_register']}с", callback_data="noop")
    kb.button(text="−30", callback_data=f"set:{chat_id}:t_register:-30")
    kb.button(text="−10", callback_data=f"set:{chat_id}:t_register:-10")
    kb.button(text="+10", callback_data=f"set:{chat_id}:t_register:+10")
    kb.button(text="+30", callback_data=f"set:{chat_id}:t_register:+30")

    kb.button(text=f"⚠️ Попередження: {s['t_warning']}с", callback_data="noop")
    kb.button(text="−2", callback_data=f"set:{chat_id}:t_warning:-2")
    kb.button(text="−1", callback_data=f"set:{chat_id}:t_warning:-1")
    kb.button(text="+1", callback_data=f"set:{chat_id}:t_warning:+1")
    kb.button(text="+2", callback_data=f"set:{chat_id}:t_warning:+2")

    kb.button(text=f"💬 Обговорення: {s['t_discussion']}с", callback_data="noop")
    kb.button(text="−10", callback_data=f"set:{chat_id}:t_discussion:-10")
    kb.button(text="−5", callback_data=f"set:{chat_id}:t_discussion:-5")
    kb.button(text="+5", callback_data=f"set:{chat_id}:t_discussion:+5")
    kb.button(text="+10", callback_data=f"set:{chat_id}:t_discussion:+10")

    kb.button(text=f"👀 Ознайомлення: {s['t_briefing']}с", callback_data="noop")
    kb.button(text="−10", callback_data=f"set:{chat_id}:t_briefing:-10")
    kb.button(text="−5", callback_data=f"set:{chat_id}:t_briefing:-5")
    kb.button(text="+5", callback_data=f"set:{chat_id}:t_briefing:+5")
    kb.button(text="+10", callback_data=f"set:{chat_id}:t_briefing:+10")

    kb.button(text="⬅️ Назад", callback_data=f"set:{chat_id}:back")
    kb.adjust(1, 4, 1, 4, 1, 4, 1, 4, 1, 4, 1, 4, 1)
    return kb.as_markup()

def kb_settings_rules(chat_id: int, s: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    av = "Так" if s.get("anonymous_vote", True) else "Ні"
    sc = "Так" if s.get("show_cards_on_elim_default", False) else "Ні"

    kb.button(text=f"🕶 Анонімність голосу: {av}", callback_data=f"set:{chat_id}:toggle:anonymous_vote")
    kb.button(text=f"🃏 Картки після вильоту (дефолт): {sc}", callback_data=f"set:{chat_id}:toggle:show_cards_on_elim_default")

    kb.button(text=f"👥 Мін гравців: {s.get('min_players', 6)}", callback_data="noop")
    kb.button(text="−1", callback_data=f"set:{chat_id}:min_players:-1")
    kb.button(text="+1", callback_data=f"set:{chat_id}:min_players:+1")

    kb.button(text=f"👥 Макс гравців: {s.get('max_players', 15)}", callback_data="noop")
    kb.button(text="−1", callback_data=f"set:{chat_id}:max_players:-1")
    kb.button(text="+1", callback_data=f"set:{chat_id}:max_players:+1")

    kb.button(text="⬅️ Назад", callback_data=f"set:{chat_id}:back")
    kb.adjust(1, 1, 1, 2, 1, 2, 1)
    return kb.as_markup()

RULES_TEXT = (
    "📜 Загальні правила (коротко)\n\n"
    "• Картки гравцям надсилаються в приват, відкриття кнопкою.\n"
    "• Після презентацій — авто-обговорення за таймером.\n"
    "• Голосування: в ПП кнопками, авто-таймер.\n"
    "• Хто не проголосував — голос проти себе.\n"
    "• 70%+ за одного — виліт без виправдання.\n"
    "• Інакше — виправдання і переголосування.\n"
    "• Після вильоту можна показати повний набір карток (за рішенням OWNER/адмінів).\n"
)

async def ensure_dm_open(user_id: int) -> bool:
    try:
        await bot.send_message(user_id, "✅ Приват відкрито. Тепер я можу слати тобі картки.")
        return True
    except Exception:
        return False

async def deal_cards(chat_id: int, g: Game):
    g.cards.clear()
    g.revealed_total.clear()

    for pid in g.players.keys():
        g.cards[pid] = random_card()
        g.revealed_total[pid] = 0

    for pid in g.players.keys():
        try:
            await bot.send_message(
                pid,
                "🧾 Твоя картка персонажа (приватно).\n"
                "Натискай кнопку нижче, щоб відкривати характеристики.",
                reply_markup=kb_dm_reveal(chat_id)
            )
        except Exception:
            pass

def next_unrevealed(g: Game, user_id: int) -> Optional[Tuple[str, str]]:
    total = g.revealed_total.get(user_id, 0)
    if total >= len(CARD_KEYS_ORDER):
        return None
    return CARD_KEYS_ORDER[total]

def full_cards_text(g: Game, user_id: int) -> str:
    cards = g.cards.get(user_id, {})
    if not cards or user_id not in g.players:
        return "🃏 Картки відсутні."
    lines = [f"🃏 Повний набір карток: {g.players[user_id].tag()}"]
    for title, key in CARD_KEYS_ORDER:
        lines.append(f"• {title}: {cards.get(key, '—')}")
    return "\n".join(lines)

async def run_timer_with_warning(chat_id: int, seconds: int, warn: int, warn_text: str) -> None:
    if warn >= seconds or warn <= 0:
        await asyncio.sleep(max(0, seconds))
        return
    await asyncio.sleep(max(0, seconds - warn))
    await bot.send_message(chat_id, warn_text)
    await asyncio.sleep(max(0, warn))

async def start_register_timer(chat_id: int, g: Game):
    await cancel_timer(g)
    sec = int(g.settings.get("t_register", 120))
    warn = int(g.settings.get("t_warning", 5))

    async def _task():
        await run_timer_with_warning(chat_id, sec, warn, f"⚠️ До кінця реєстрації {warn} сек!")
        if g.active or g.paused:
            return
        g.lobby_open = False
        await bot.send_message(chat_id, "⛔ Реєстрацію закрито.")
        await update_lobby(chat_id, g)

    g.timer_task = asyncio.create_task(_task())

async def start_briefing_timer(chat_id: int, g: Game):
    await cancel_timer(g)
    sec = int(g.settings.get("t_briefing", 20))
    warn = int(g.settings.get("t_warning", 5))

    async def _task():
        await bot.send_message(chat_id, f"👀 Ознайомлення: {sec} сек.")
        await run_timer_with_warning(chat_id, sec, warn, f"⚠️ До кінця ознайомлення {warn} сек!")
        if not g.active or g.paused:
            return
        await start_presentation(chat_id, g)

    g.timer_task = asyncio.create_task(_task())

async def start_discussion_timer(chat_id: int, g: Game):
    await cancel_timer(g)
    sec = int(g.settings.get("t_discussion", 60))
    warn = int(g.settings.get("t_warning", 5))

    async def _task():
        await run_timer_with_warning(chat_id, sec, warn, f"⚠️ До кінця обговорення {warn} сек!")
        if not g.active or g.paused:
            return
        g.phase = Phase.SPEECHES
        await bot.send_message(
            chat_id,
            "⏱ Обговорення завершено.\n"
            "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
            "Кожному по 30 секунд (ви самі тримаєте час).\n"
            "Після виступів — /openvote"
        )

    g.timer_task = asyncio.create_task(_task())

async def start_vote_timer(chat_id: int, g: Game):
    await cancel_timer(g)
    sec = int(g.settings.get("t_vote", 15))
    warn = int(g.settings.get("t_warning", 5))

    async def _task():
        await run_timer_with_warning(chat_id, sec, warn, f"⚠️ До кінця голосування {warn} сек!")
        if not g.active or g.paused:
            return
        if g.vote_open:
            await close_vote_internal(chat_id, g, forced_by_timer=True)

    g.timer_task = asyncio.create_task(_task())

async def apply_silence_penalty(g: Game):
    for pid in g.silent_offenders:
        p = g.players.get(pid)
        if p and p.alive:
            p.skip_speech_next_round = True

def count_votes_with_absent_as_self(g: Game) -> Dict[int, int]:
    alive_ids = g.alive_ids()
    counts: Dict[int, int] = {pid: 0 for pid in alive_ids}
    for voter_id in alive_ids:
        if voter_id in g.votes and g.votes[voter_id] in counts:
            counts[g.votes[voter_id]] += 1
        else:
            counts[voter_id] += 1
    return counts

def top_candidates(counts: Dict[int, int]) -> Tuple[List[int], int]:
    if not counts:
        return [], 0
    mx = max(counts.values())
    cands = [pid for pid, c in counts.items() if c == mx]
    return cands, mx

async def start_presentation(chat_id: int, g: Game):
    g.phase = Phase.PRESENTATION
    order_tags = [g.players[pid].tag() for pid in g.order if g.players.get(pid) and g.players[pid].alive]
    need = g.reveal_plan[g.round_no - 1]
    await bot.send_message(
        chat_id,
        f"🎙 Раунд {g.round_no}. Етап 1: ПРЕЗЕНТАЦІЯ.\n"
        f"Кожен відкриває в ЛС і озвучує: {need} характеристик.\n\n"
        f"Порядок: {', '.join(order_tags)}\n\n"
        "Коли всі виступили — /next"
    )

async def post_intro(chat_id: int, g: Game):
    await bot.send_message(
        chat_id,
        "☢️ СИРЕНИ. ПАНІКА. ПОПІЛ НА НЕБІ.\n\n"
        f"Катаклізм: {g.catastrophe}\n\n"
        f"{g.bunker_desc}\n"
        f"👁 Місць у бункері: {g.slots} із {len(g.players)}.\n\n"
        "📩 Картки роздано в ЛС."
    )
@dp.message(Command("start"))
async def cmd_start(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    if message.chat.type == "private":
        await message.answer("✅ Готово. Тепер я можу писати тобі в ЛС. Повернись у групу 🙂")
        return

    await message.answer(
        "🏚 BUNKER UA BOT\n\n"
        "Команди:\n"
        "• /new — лобі\n"
        "• /players — гравці\n"
        "• /leave — вийти\n"
        "• /startgame — старт\n"
        "• /next — наступний етап\n"
        "• /openvote — голосування (кнопки в ПП)\n"
        "• /closevote — закрити голосування\n"
        "• /settings — налаштування (OWNER/адмін → меню в ПП)\n"
        "• /pause, /resume (OWNER)\n"
        "• /end — завершити\n"
    )

@dp.message(Command("new"))
async def cmd_new(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if message.chat.type == "private":
        await message.answer("Створи лобі у групі 🙂")
        return

    settings = get_chat_settings(message.chat.id)
    GAMES[message.chat.id] = Game()
    g = get_game(message.chat.id)
    g.settings = settings

    g.lobby_open = True
    await update_lobby(message.chat.id, g)
    await start_register_timer(message.chat.id, g)

@dp.message(Command("players"))
async def cmd_players(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if message.chat.type == "private":
        await message.answer("Ця команда працює у групі.")
        return
    await message.answer("👥 Гравці:\n" + g.roster_text(only_alive=False))

@dp.message(Command("leave"))
async def cmd_leave(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if message.chat.type == "private":
        await message.answer("Ця команда працює у групі.")
        return
    if g.active:
        await message.answer("Гра вже стартувала — вийти не можна.")
        return

    u = message.from_user
    if not u:
        return
    if u.id not in g.players:
        await message.answer("Тебе немає в лобі. Натисни «➕ Приєднатись».")
        return

    tag = g.players[u.id].tag()
    del g.players[u.id]
    await message.answer(f"❌ {tag} вийшов. Гравців: {len(g.players)}")
    await update_lobby(message.chat.id, g)

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    if message.chat.type == "private":
        await message.answer("⚙️ Відкрий /settings у групі, і я надішлю меню в ПП.")
        return

    if g.active:
        await message.answer("⛔ Налаштування можна змінювати тільки коли гри немає.\nЗаверши гру командою /end.")
        return

    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return
    if not await is_admin_or_owner(message.chat.id, uid):
        await message.answer("⛔ Налаштування може відкривати тільки OWNER або адмін чату.")
        return

    g.settings = get_chat_settings(message.chat.id)

    try:
        await bot.send_message(
            uid,
            f"⚙️ Налаштування для чату: {message.chat.title or message.chat.id}",
            reply_markup=kb_settings_main(message.chat.id),
        )
        await message.answer("✅ Меню налаштувань надіслав(ла) тобі в ПП.")
    except Exception:
        await message.answer("⚠️ Не можу написати в ПП. Відкрий бота в приваті: /start і повтори /settings.")

@dp.message(Command("pause"))
async def cmd_pause(message: Message):
    g = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    g.paused = True
    await cancel_timer(g)
    await message.answer("⏸ Пауза: бот мовчить для всіх. Тільки OWNER може /resume.")

@dp.message(Command("resume"))
async def cmd_resume(message: Message):
    g = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    g.paused = False
    await message.answer("▶️ Відновлено.")

@dp.message(Command("end"))
async def cmd_end(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    await cancel_timer(g)
    settings = get_chat_settings(message.chat.id)
    GAMES[message.chat.id] = Game()
    g = get_game(message.chat.id)
    g.settings = settings
    await message.answer("🏁 Гру завершено. /new щоб почати знову.")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if not g.active:
        await message.answer("Немає активної гри. /new → «➕ Приєднатись» → /startgame")
        return
    await message.answer(
        f"📌 Стан:\n"
        f"Раунд: {g.round_no}/{MAX_ROUNDS}\n"
        f"Фаза: {g.phase}\n"
        f"Живі: {len(g.alive_ids())} | Місць: {g.slots}\n"
        f"Голосування: {'відкрите' if g.vote_open else 'закрите'}"
    )

@dp.message(Command("startgame"))
async def cmd_startgame(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if message.chat.type == "private":
        await message.answer("Стартуй гру в групі 🙂")
        return
    if g.active:
        await message.answer("Гра вже йде.")
        return

    g.lobby_open = False
    await cancel_timer(g)

    s = g.settings
    min_p = int(s.get("min_players", 6))
    max_p = int(s.get("max_players", 15))

    if len(g.players) < min_p:
        await message.answer(f"Потрібно мінімум {min_p} гравців.")
        return
    if len(g.players) > max_p:
        await message.answer(f"Забагато гравців. Максимум {max_p}.")
        return

    u = message.from_user
    if not u:
        return
    g.host_id = u.id

    missing = []
    for pid in list(g.players.keys()):
        ok = await ensure_dm_open(pid)
        if not ok:
            missing.append(pid)
    if missing:
        await message.answer("⚠️ Дехто не відкрив ЛС. Нехай натиснуть /start у приваті з ботом і повтори /startgame.")
        return

    g.active = True
    g.round_no = 1
    g.clockwise = True

    g.catastrophe = random.choice(CATASTROPHES)
    g.bunker_desc = build_bunker_desc()
    g.slots = bunker_slots(len(g.players), s.get("slots_mode", "half_floor"))
    g.reveal_plan = reveals_per_round(len(g.players))

    for p in g.players.values():
        p.alive = True
        p.skip_speech_next_round = False

    g.votes.clear()
    g.silent_offenders.clear()
    g.vote_open = False

    g.make_round_order()

    await post_intro(message.chat.id, g)
    await deal_cards(message.chat.id, g)

    g.phase = Phase.BRIEFING
    await update_lobby(message.chat.id, g)
    await start_briefing_timer(message.chat.id, g)

@dp.message(Command("next"))
async def cmd_next(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if not g.active:
        await message.answer("Гра не стартувала.")
        return

    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return
    if not (uid == g.host_id or is_owner(uid)):
        await message.answer("Тільки хост або OWNER може /next.")
        return

    if g.need_finish():
        g.phase = Phase.FINISH
        await bot.send_message(message.chat.id, f"🏁 ФІНАЛ.\nПереможці:\n{g.roster_text(True)}")
        g.active = False
        return

    if g.phase == Phase.PRESENTATION:
        g.phase = Phase.DISCUSSION
        sec = int(g.settings.get("t_discussion", 60))
        await bot.send_message(message.chat.id, f"💬 Обговорення: {sec} сек (авто).")
        await start_discussion_timer(message.chat.id, g)
        return

    if g.phase == Phase.DISCUSSION:
        await cancel_timer(g)
        g.phase = Phase.SPEECHES
        await bot.send_message(
            message.chat.id,
            "⏭ Обговорення завершено.\n"
            "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
            "Кожному по 30 секунд.\n"
            "Після виступів — /openvote"
        )
        return

    if g.phase in (Phase.BRIEFING, Phase.LOBBY):
        await start_presentation(message.chat.id, g)
        return

    await message.answer("Зараз /next не потрібен. /status")

@dp.message(Command("openvote"))
async def cmd_openvote(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if not g.active:
        await message.answer("Гра не стартувала.")
        return

    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return
    if not (uid == g.host_id or is_owner(uid)):
        await message.answer("Відкрити голосування може тільки хост або OWNER.")
        return
    if g.vote_open:
        await message.answer("Голосування вже відкрите.")
        return

    await cancel_timer(g)

    g.phase = Phase.VOTE
    g.vote_open = True
    g.votes.clear()
    g.silent_offenders.clear()

    sec = int(g.settings.get("t_vote", 15))
    await bot.send_message(
        message.chat.id,
        f"🗳 ГОЛОСУВАННЯ ({sec} сек, авто).\n"
        "Голосуємо в ПП (бот надіслав кнопки кожному).\n"
        "У чаті — тиша."
    )

    failed = []
    for pid in g.alive_ids():
        try:
            await bot.send_message(
                pid,
                f"🗳 Голосування у чаті: {message.chat.title or message.chat.id}\n"
                f"Час: {sec} сек.\n"
                f"Обери, за кого голосуєш 👇",
                reply_markup=kb_vote_private(message.chat.id, g)
            )
        except Exception:
            failed.append(pid)

    if failed:
        tags = ", ".join(g.players[x].tag() for x in failed if x in g.players)
        await bot.send_message(message.chat.id, f"⚠️ Не можу написати в ПП: {tags}\nНехай відкриють бота в приваті: /start")

    await start_vote_timer(message.chat.id, g)

@dp.message(Command("closevote"))
async def cmd_closevote(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if not g.active:
        await message.answer("Гра не стартувала.")
        return

    uid = message.from_user.id if message.from_user else None
    if uid is None:
        return
    if not (uid == g.host_id or is_owner(uid)):
        await message.answer("Закривати голосування може тільки хост або OWNER.")
        return
    if not g.vote_open:
        await message.answer("Немає відкритого голосування.")
        return

    await cancel_timer(g)
    await close_vote_internal(message.chat.id, g, forced_by_timer=False)

@dp.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()

@dp.callback_query(F.data == "lobby:join")
async def cb_join(call: CallbackQuery):
    if call.message is None:
        return
    g = get_game(call.message.chat.id)
    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if call.message.chat.type == "private":
        await call.answer("Гра працює у групі 🙂", show_alert=True)
        return

    if g.active:
        await call.answer("Гра вже йде.", show_alert=True)
        return

    if not g.lobby_open:
        await call.answer("Реєстрація закрита ⛔", show_alert=True)
        return

    u = call.from_user
    if u.id in g.players:
        await call.answer("Ти вже в лобі ✅", show_alert=False)
        return

    max_p = int(g.settings.get("max_players", 15))
    if len(g.players) >= max_p:
        await call.answer(f"Максимум {max_p} гравців.", show_alert=True)
        return

    g.players[u.id] = Player(user_id=u.id, name=u.full_name, username=(u.username or ""))
    await call.answer("✅ Додано", show_alert=False)
    await update_lobby(call.message.chat.id, g)

@dp.callback_query(F.data.startswith("dm:reveal:"))
async def cb_dm_reveal(call: CallbackQuery):
    if call.message is None:
        return
    chat_id = int(call.data.split(":")[2])
    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return
    if not g.active:
        await call.answer("Гри немає.", show_alert=True)
        return

    uid = call.from_user.id
    if uid not in g.players or not g.players[uid].alive:
        await call.answer("Ти не у грі.", show_alert=True)
        return

    nxt = next_unrevealed(g, uid)
    if not nxt:
        await call.answer("Все відкрито ✅", show_alert=False)
        await call.message.answer("Усі характеристики вже відкриті.")
        return

    title, key = nxt
    value = g.cards[uid][key]
    g.revealed_total[uid] = g.revealed_total.get(uid, 0) + 1

    await call.answer("✅", show_alert=False)
    await call.message.answer(f"✅ Відкрито: {title} — {value}")

@dp.callback_query(F.data.startswith("vote:"))
async def cb_vote(call: CallbackQuery):
    if call.message is None:
        return

    parts = call.data.split(":")  
    if len(parts) < 3:
        await call.answer("Помилка голосу.", show_alert=True)
        return

    chat_id = int(parts[1])
    target_id = int(parts[2])
    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return
    if not g.active or not g.vote_open:
        await call.answer("Зараз немає відкритого голосування.", show_alert=True)
        return

    voter_id = call.from_user.id
    if voter_id not in g.players or not g.players[voter_id].alive:
        await call.answer("Голосують лише живі гравці.", show_alert=True)
        return

    if target_id not in g.players or not g.players[target_id].alive:
        await call.answer("Цей гравець вже не в грі.", show_alert=True)
        return
    if target_id == voter_id:
        await call.answer("Сам за себе не можна 😈", show_alert=True)
        return

    g.votes[voter_id] = target_id
    target_tag = g.players[target_id].tag()

    await call.answer("✅ Зараховано", show_alert=False)
    try:
        await call.message.answer(f"✅ Ти проголосував за {target_tag}")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("elimreveal:"))
async def cb_elimreveal(call: CallbackQuery):
    if call.message is None:
        return
    chat_id = call.message.chat.id
    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return

    uid = call.from_user.id
    if not await is_admin_or_owner(chat_id, uid):
        await call.answer("⛔ Тільки OWNER або адмін чату", show_alert=True)
        return

    parts = call.data.split(":")
    action = parts[1]
    target_id = int(parts[2])

    if action == "yes":
        await call.message.edit_text("✅ Показую картки.")
        await bot.send_message(chat_id, full_cards_text(g, target_id))
        await call.answer()
        return

    if action == "no":
        await call.message.edit_text("❌ Картки не показуємо.")
        await call.answer()
        return

    await call.answer()

@dp.callback_query(F.data.startswith("set:"))
async def cb_settings(call: CallbackQuery):
    if call.message is None:
        return

    parts = call.data.split(":")

    if len(parts) < 3:
        await call.answer("Помилка", show_alert=True)
        return

    chat_id = int(parts[1])
    action = parts[2]

    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if g.active:
        await call.answer("⛔ Під час гри налаштування змінювати не можна.", show_alert=True)
        return

    uid = call.from_user.id
    if not await is_admin_or_owner(chat_id, uid):
        await call.answer("⛔ Тільки OWNER або адмін чату", show_alert=True)
        return

    s = g.settings if g.settings else get_chat_settings(chat_id)

    if action == "timers":
        await call.message.edit_text("⏱ Таймери", reply_markup=kb_settings_timers(chat_id, s))
        await call.answer()
        return

    if action == "rules":
        await call.message.edit_text(RULES_TEXT, reply_markup=kb_settings_rules(chat_id, s))
        await call.answer()
        return

    if action == "back":
        await call.message.edit_text("⚙️ Налаштування", reply_markup=kb_settings_main(chat_id))
        await call.answer()
        return

    if action == "save":
        set_chat_settings(chat_id, s)
        g.settings = s
        await call.answer("✅ Збережено!", show_alert=False)
        await call.message.edit_text("✅ Налаштування збережені.", reply_markup=kb_settings_main(chat_id))
        return

    if action == "toggle" and len(parts) >= 4:
        key = parts[3]
        if key == "anonymous_vote":
            s["anonymous_vote"] = not bool(s.get("anonymous_vote", True))
        elif key == "show_cards_on_elim_default":
            s["show_cards_on_elim_default"] = not bool(s.get("show_cards_on_elim_default", False))
        g.settings = s
        await call.message.edit_reply_markup(reply_markup=kb_settings_rules(chat_id, s))
        await call.answer("✅")
        return

    if len(parts) >= 5:
        key = parts[3]
        try:
            delta = int(parts[4].replace("+", ""))
        except Exception:
            await call.answer("Помилка", show_alert=True)
            return

        if key not in s:
            await call.answer("Невідомий параметр", show_alert=True)
            return

        newv = int(s.get(key, DEFAULT_SETTINGS.get(key, 0))) + delta

        if key.startswith("t_"):
            newv = max(5, min(600, newv))
        if key in ("min_players", "max_players"):
            newv = max(2, min(30, newv))
            if key == "min_players":
                newv = min(newv, int(s.get("max_players", 15)))
            if key == "max_players":
                newv = max(newv, int(s.get("min_players", 6)))

        s[key] = newv
        g.settings = s

        if key in ("min_players", "max_players"):
            await call.message.edit_reply_markup(reply_markup=kb_settings_rules(chat_id, s))
        else:
            await call.message.edit_reply_markup(reply_markup=kb_settings_timers(chat_id, s))
        await call.answer(f"✅ {newv}", show_alert=False)
        return

    await call.answer()

@dp.message(F.text)
async def any_text(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if not g.active:
        return

    if message.chat.type == "private":
        return

    if g.vote_open:
        txt = (message.text or "").strip()
        if not txt.startswith("/"):
            u = message.from_user
            if u and u.id in g.players and g.players[u.id].alive:
                g.silent_offenders.add(u.id)
                try:
                    await message.reply("⚠️ Тиша під час голосування! Штраф у наступному раунді.")
                except Exception:
                    pass

async def close_vote_internal(chat_id: int, g: Game, forced_by_timer: bool):
    g.vote_open = False
    await apply_silence_penalty(g)

    alive_count = len(g.alive_ids())
    counts = count_votes_with_absent_as_self(g)
    cands, mx = top_candidates(counts)
    mx_pct = percent(mx, alive_count)

    report_lines = [f"{g.players[pid].tag()}: {c}" for pid, c in sorted(counts.items(), key=lambda x: -x[1])]
    report = "\n".join(report_lines)

    await bot.send_message(
        chat_id,
        "📊 Голоси зібрано.\n"
        + ("(авто-таймер)\n" if forced_by_timer else "")
        + f"{report}\n\n"
        f"Максимум: {mx} голосів ({mx_pct:.1f}%)."
    )

    if len(cands) == 1 and mx_pct >= 70.0:
        await eliminate(chat_id, g, [cands[0]], "70%+ голосів — без виправдання.")
        return

    await bot.send_message(
        chat_id,
        "⚖️ Виправдання (30 сек). Потім переголосування.\n"
        "Відкрий знову: /openvote"
    )

async def eliminate(chat_id: int, g: Game, kicked_ids: List[int], reason: str):
    for kid in kicked_ids:
        if kid in g.players:
            g.players[kid].alive = False

    tags = ", ".join(g.players[k].tag() for k in kicked_ids if k in g.players)
    await bot.send_message(
        chat_id,
        "🚪 Двері бункера скриплять…\n"
        f"Причина: {reason}\n\n"
        f"❌ Вигнано: {tags}\n"
    )

    g.last_elim_id = kicked_ids[0] if kicked_ids else None
    if g.last_elim_id is not None:
        default_show = bool(g.settings.get("show_cards_on_elim_default", False))
        if default_show:
            await bot.send_message(chat_id, full_cards_text(g, g.last_elim_id))
        else:
            await bot.send_message(
                chat_id,
                "🔎 Показати повний набір карток вигнаного гравця?",
                reply_markup=kb_reveal_elim(g.last_elim_id)
            )

    if g.need_finish() or g.round_no >= MAX_ROUNDS:
        g.phase = Phase.FINISH
        await bot.send_message(chat_id, f"🏁 ФІНАЛ.\nПереможці:\n{g.roster_text(True)}")
        g.active = False
        return

    g.round_no += 1
    g.clockwise = not g.clockwise
    g.make_round_order()
    g.votes.clear()
    g.silent_offenders.clear()

    g.phase = Phase.BRIEFING
    await start_briefing_timer(chat_id, g)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())