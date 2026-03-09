import os
import json
import time
import asyncio
import random
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
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
USERS_FILE = Path("users.json")

DEFAULT_SETTINGS = {
    "t_turn": 60,
    "t_vote": 15,
    "t_register": 120,
    "t_warning": 5,
    "t_discussion": 60,
    "t_briefing": 20,
    "t_accuse": 25,
    "t_justify": 30,
    "t_exile_pause": 5,

    "anonymous_vote": True,
    "show_cards_on_elim_default": False,

    "min_players": 6,
    "max_players": 15,
    "slots_mode": "half_floor",

    "penalty_for_silence": True,
    "penalty_for_talk_during_vote": True,
}

DEFAULT_USER = {
    "name": "",
    "username": "",
    "money": 100,
    "xp": 0,
    "level": 1,
    "wins": 0,
    "games": 0,
    "spec": [],
    "daily_ts": 0,
    "ref_by": 0,
    "refs": 0,
}

SHOP = {
    "double_vote": 50,
    "cancel_vote": 40,
    "shield": 70,
    "revote": 60,
}

SPEC_NAMES = {
    "double_vote": "Подвійний голос",
    "cancel_vote": "Скасування голосу",
    "shield": "Щит",
    "revote": "Переголосування",
}

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
CARD_TITLES = {key: title for title, key in CARD_KEYS_ORDER}

AI_HOST_INTRO = [
    "🎙 Ведучий: Сирени вже виють. Світ, який ви знали, закінчився. Починаємо боротьбу за місце в бункері.",
    "🎙 Ведучий: За цими дверима — шанс на життя. Але місць вистачить не всім. Гра починається.",
    "🎙 Ведучий: Сьогодні кожен із вас має довести, що саме він заслуговує вижити.",
]

AI_HOST_PRESENT = [
    "🎙 Ведучий: До слова запрошується {tag}. У тебе {sec} секунд, щоб переконати інших.",
    "🎙 Ведучий: {tag}, твій вихід. Час показати, чому бункер не може без тебе обійтись. {sec} секунд.",
    "🎙 Ведучий: Увага на {tag}. Саме зараз вирішується твоє місце серед тих, хто виживе. {sec} секунд.",
]

AI_HOST_PRESENT_END = [
    "🎙 Ведучий: Час вичерпано. Наступний гравець.",
    "🎙 Ведучий: Досить. Рішення будуть приймати інші. Продовжуємо.",
    "🎙 Ведучий: Хід завершено. Переходимо далі.",
]

AI_HOST_DISCUSS = [
    "🎙 Ведучий: Усі карти на столі. Тепер час сумнівів, тиску й холодного розрахунку.",
    "🎙 Ведучий: Починається обговорення. Саме тут народжуються союзи й вироки.",
    "🎙 Ведучий: Ви почули одне одного. Тепер вирішіть, хто тягне групу вниз.",
]

AI_HOST_ACCUSE = [
    "🎙 Ведучий: Останній шанс озвучити підозри. Назвіть тих, кого не бачите в бункері.",
    "🎙 Ведучий: Починається коротка фаза обвинувачень. Говоріть прямо.",
    "🎙 Ведучий: Настав момент назвати зайвих.",
]

AI_HOST_VOTE = [
    "🎙 Ведучий: Голосування відкрито. Один вибір може перекреслити чиєсь майбутнє.",
    "🎙 Ведучий: Час говорити закінчився. Тепер вирішують голоси.",
    "🎙 Ведучий: Натискайте кнопки. Саме зараз визначається, хто залишиться за дверима.",
]

AI_HOST_JUSTIFY = [
    "🎙 Ведучий: У кандидатів на вигнання ще є кілька секунд, щоб урятувати себе.",
    "🎙 Ведучий: Це останній шанс змінити думку групи. Починається виправдання.",
    "🎙 Ведучий: Ті, кого майже вигнали, зараз можуть сказати найважливіші слова у грі.",
]

AI_HOST_EXILE = [
    "🎙 Ведучий: Рішення прийнято. Двері бункера відчиняються лише для обраних.",
    "🎙 Ведучий: Підрахунок завершено. Хтось зараз залишиться по той бік дверей.",
    "🎙 Ведучий: Бункер не пробачає слабкості. Час дізнатися, хто вибуває.",
]

AI_HOST_SILENCE_PENALTY = [
    "⚠️ Ведучий: {tag} мовчав занадто довго. Система відкриває характеристику замість нього.",
    "⚠️ Ведучий: {tag} не скористався своїм шансом. Втручання системи неминуче.",
]

AI_HOST_TALK_PENALTY = [
    "⚠️ Ведучий: {tag} порушив тишу під час голосування. Це матиме наслідки.",
    "⚠️ Ведучий: Правила порушено. {tag} отримує штраф за балачки під час голосування.",
]

RULES_TEXT = (
    "📜 Режим «як у Бункері»\n\n"
    "• Виступи йдуть по одному гравцю.\n"
    "• Тільки поточний гравець може відкривати характеристики.\n"
    "• Якщо він не відкрив нічого — бот сам відкриє характеристику.\n"
    "• Якщо відкрив потрібну кількість — хід одразу переходить далі.\n"
    "• Після презентацій: обговорення → обвинувачення → голосування.\n"
    "• 70%+ за одного — виліт без виправдання.\n"
    "• Інакше: виправдання → переголосування → вигнання.\n"
    "• За балачки під час голосування і пасивність дається штраф.\n"
)

def ai_line(pool: List[str], **kwargs) -> str:
    return random.choice(pool).format(**kwargs)

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

def load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_users(data: dict) -> None:
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def calc_level(xp: int) -> int:
    level = 1
    while xp >= level * 100:
        level += 1
    return level

def get_user(user_id: int) -> dict:
    users = load_users()
    uid = str(user_id)

    if uid not in users:
        users[uid] = DEFAULT_USER.copy()
        save_users(users)

    user = users[uid]

    for k, v in DEFAULT_USER.items():
        if k not in user:
            user[k] = v if not isinstance(v, list) else []

    user["level"] = calc_level(int(user.get("xp", 0)))
    users[uid] = user
    save_users(users)
    return user

def update_user(user_id: int, user_data: dict) -> None:
    users = load_users()
    user_data["level"] = calc_level(int(user_data.get("xp", 0)))
    users[str(user_id)] = user_data
    save_users(users)

def add_money(user_id: int, amount: int) -> dict:
    user = get_user(user_id)
    user["money"] = max(0, int(user.get("money", 0)) + amount)
    update_user(user_id, user)
    return user

def add_xp(user_id: int, amount: int) -> dict:
    user = get_user(user_id)
    user["xp"] = max(0, int(user.get("xp", 0)) + amount)
    user["level"] = calc_level(user["xp"])
    update_user(user_id, user)
    return user

def add_win(user_id: int) -> dict:
    user = get_user(user_id)
    user["wins"] = int(user.get("wins", 0)) + 1
    update_user(user_id, user)
    return user

def add_game(user_id: int) -> dict:
    user = get_user(user_id)
    user["games"] = int(user.get("games", 0)) + 1
    update_user(user_id, user)
    return user

def touch_user_profile(user_id: int, full_name: str = "", username: str = "") -> dict:
    user = get_user(user_id)
    if full_name:
        user["name"] = full_name
    if username is not None:
        user["username"] = username
    update_user(user_id, user)
    return user

def pretty_user_name(user_data: dict, uid: int) -> str:
    username = (user_data.get("username") or "").strip()
    name = (user_data.get("name") or "").strip()

    if username:
        return f"@{username}"
    if name:
        return name
    return f"Гравець {uid}"

def build_stats_text() -> str:
    users = load_users()

    if not users:
        return (
            "📊 Статистика бота\n\n"
            "👥 Усього користувачів: 0\n"
            "🎮 Грали хоча б раз: 0\n"
            "🕹 Усього ігор: 0\n"
            "🏆 Усього перемог: 0\n"
            "💰 Монет у системі: 0\n"
            "⭐ XP у системі: 0\n"
            "🧬 Куплених Spec: 0"
        )

    total_users = len(users)
    played_users = sum(1 for u in users.values() if int(u.get("games", 0)) > 0)
    total_games = sum(int(u.get("games", 0)) for u in users.values())
    total_wins = sum(int(u.get("wins", 0)) for u in users.values())
    total_money = sum(int(u.get("money", 0)) for u in users.values())
    total_xp = sum(int(u.get("xp", 0)) for u in users.values())
    total_specs = sum(len(u.get("spec", [])) for u in users.values())

    return (
        "📊 Статистика бота\n\n"
        f"👥 Усього користувачів: {total_users}\n"
        f"🎮 Грали хоча б раз: {played_users}\n"
        f"🕹 Усього ігор: {total_games}\n"
        f"🏆 Усього перемог: {total_wins}\n"
        f"💰 Монет у системі: {total_money}\n"
        f"⭐ XP у системі: {total_xp}\n"
        f"🧬 Куплених Spec: {total_specs}"
    )

def build_top_text() -> str:
    users = load_users()

    if not users:
        return "🏆 Топ поки порожній."

    rating = []
    for uid, data in users.items():
        wins = int(data.get("wins", 0))
        level = int(data.get("level", calc_level(int(data.get("xp", 0)))))
        money = int(data.get("money", 0))
        rating.append((int(uid), data, wins, level, money))

    rating.sort(key=lambda x: (-x[2], -x[3], -x[4]))

    medals = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
    }

    lines = ["🏆 Топ гравців Bunker\n"]

    for i, (uid, data, wins, level, money) in enumerate(rating[:10], start=1):
        medal = medals.get(i, f"{i}.")
        name = pretty_user_name(data, uid)
        lines.append(
            f"{medal} {name}\n"
            f"   🏆 Перемог: {wins}\n"
            f"   📈 Рівень: {level}\n"
            f"   💰 Монети: {money}\n"
        )

    return "\n".join(lines)

def build_ref_text(user_id: int, bot_username: str) -> str:
    user = get_user(user_id)
    return (
        "👥 Реферальна система\n\n"
        "Запроси друзів та отримуй нагороди!\n\n"
        f"🔗 Твоє посилання:\nhttps://t.me/{bot_username}?start={user_id}\n\n"
        "🎁 Нагорода:\n"
        "+50 монет за кожного друга\n\n"
        f"👤 Запрошено: {int(user.get('refs', 0))}"
    )

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

def profile_text(user_id: int, tg_name: str) -> str:
    user = get_user(user_id)
    xp = int(user["xp"])
    level = int(user["level"])
    need = level * 100
    return (
        f"👤 Профіль: {tg_name}\n\n"
        f"💰 Монети: {user['money']}\n"
        f"⭐ XP: {xp}/{need}\n"
        f"📈 Рівень: {level}\n"
        f"🏆 Перемог: {user['wins']}\n"
        f"🎮 Ігор: {user['games']}\n"
        f"🧬 Spec: {len(user['spec'])}"
    )

def shop_text(user_id: int) -> str:
    user = get_user(user_id)
    lines = [f"🏪 Магазин\n\n💰 Баланс: {user['money']}\n"]
    for key, price in SHOP.items():
        lines.append(f"• {SPEC_NAMES.get(key, key)} — {price}💰")
    return "\n".join(lines)

def spec_text(user_id: int) -> str:
    user = get_user(user_id)
    if not user["spec"]:
        return "🧬 Твої Spec:\n\nПоки що порожньо."
    return "🧬 Твої Spec:\n\n" + "\n".join(
        f"{i + 1}. {SPEC_NAMES.get(item, item)}"
        for i, item in enumerate(user["spec"])
    )

class Phase(str, Enum):
    LOBBY = "lobby"
    BRIEFING = "briefing"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"
    ACCUSE = "accuse"
    VOTE = "vote"
    JUSTIFY = "justify"
    REVOTE = "revote"
    FINISH = "finish"

@dataclass
class Player:
    user_id: int
    name: str
    username: str = ""
    alive: bool = True

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
    presentation_run_id: int = 0

    vote_open: bool = False
    votes: Dict[int, int] = field(default_factory=dict)
    silent_offenders: Set[int] = field(default_factory=set)

    cards: Dict[int, Dict[str, str]] = field(default_factory=dict)
    revealed_total: Dict[int, int] = field(default_factory=dict)
    revealed_by_round: Dict[int, Dict[int, Set[str]]] = field(default_factory=dict)

    last_elim_id: Optional[int] = None

    players: Dict[int, Player] = field(default_factory=dict)
    settings: dict = field(default_factory=dict)

    vote_kind: str = "main"
    vote_targets: List[int] = field(default_factory=list)
    justify_candidates: List[int] = field(default_factory=list)

    current_speaker_index: int = 0
    current_speaker_id: Optional[int] = None
    round_reveal_limit: int = 0

    penalties_next_round_reveal_minus: Dict[int, int] = field(default_factory=dict)
    penalty_round_applied: Set[int] = field(default_factory=set)
    talk_vote_penalties: Set[int] = field(default_factory=set)

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
SETTINGS_SESSIONS: Dict[int, int] = {}
VOTE_SESSIONS: Dict[int, int] = {}

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

def player_round_limit(g: Game, user_id: int) -> int:
    base_limit = g.reveal_plan[g.round_no - 1] if 0 < g.round_no <= len(g.reveal_plan) else 1
    minus = g.penalties_next_round_reveal_minus.get(user_id, 0)
    return max(1, base_limit - minus)

def kb_lobby() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Приєднатись", callback_data="lobby:join")
    kb.adjust(1)
    return kb.as_markup()

def kb_vote(chat_id: int, g: Game, voter_id: Optional[int] = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    if g.vote_targets:
        targets = [pid for pid in g.vote_targets if pid in g.players and g.players[pid].alive]
    else:
        targets = g.alive_ids()

    for pid in targets:
        if voter_id is not None and pid == voter_id:
            continue
        p = g.players[pid]
        kb.button(text=p.tag(), callback_data=f"vote:{chat_id}:{pid}")

    kb.adjust(1)
    return kb.as_markup()

def kb_dm_reveal_menu(chat_id: int, user_id: int, g: Game) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    round_map = g.revealed_by_round.setdefault(g.round_no, {})
    opened = round_map.setdefault(user_id, set())
    limit = player_round_limit(g, user_id)
    is_current = user_id == g.current_speaker_id and g.phase == Phase.PRESENTATION

    all_prev_opened: Set[str] = set()
    for rnd_map in g.revealed_by_round.values():
        all_prev_opened.update(rnd_map.get(user_id, set()))

    for title, key in CARD_KEYS_ORDER:
        mark = "✅ " if key in opened else ""
        disabled = (not is_current) or (key in all_prev_opened) or (len(opened) >= limit)
        text = f"{mark}{title}"
        cb = "noop" if disabled else f"revealpick:{chat_id}:{key}"
        kb.button(text=text, callback_data=cb)

    kb.adjust(2)
    return kb.as_markup()

def kb_reveal_elim(target_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Так, показати", callback_data=f"elimreveal:yes:{target_id}")
    kb.button(text="❌ Ні, не показувати", callback_data=f"elimreveal:no:{target_id}")
    kb.adjust(1)
    return kb.as_markup()

def kb_settings_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏱ Таймери", callback_data="set:timers")
    kb.button(text="📜 Загальні правила", callback_data="set:rules")
    kb.button(text="✅ Готово (зберегти)", callback_data="set:save")
    kb.adjust(1)
    return kb.as_markup()

def kb_settings_timers(s: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    rows = [
        ("🎙 Хід", "t_turn", 10, 5),
        ("🗳 Голосування", "t_vote", 10, 5),
        ("🧩 Реєстрація", "t_register", 30, 10),
        ("⚠️ Попередження", "t_warning", 2, 1),
        ("💬 Обговорення", "t_discussion", 10, 5),
        ("👀 Ознайомлення", "t_briefing", 10, 5),
        ("📣 Обвинувачення", "t_accuse", 10, 5),
        ("⚖️ Виправдання", "t_justify", 10, 5),
        ("🚪 Пауза перед вигнанням", "t_exile_pause", 2, 1),
    ]

    for label, key, big, small in rows:
        kb.button(text=f"{label}: {s[key]}с", callback_data="noop")
        kb.button(text=f"−{big}", callback_data=f"set:{key}:-{big}")
        kb.button(text=f"−{small}", callback_data=f"set:{key}:-{small}")
        kb.button(text=f"+{small}", callback_data=f"set:{key}:+{small}")
        kb.button(text=f"+{big}", callback_data=f"set:{key}:+{big}")

    kb.button(text="⬅️ Назад", callback_data="set:back")
    kb.adjust(1, 4, 1, 4, 1, 4, 1, 4, 1, 4, 1, 4, 1, 4, 1, 4, 1)
    return kb.as_markup()

def kb_settings_rules(s: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    av = "Так" if s.get("anonymous_vote", True) else "Ні"
    sc = "Так" if s.get("show_cards_on_elim_default", False) else "Ні"
    ps = "Так" if s.get("penalty_for_silence", True) else "Ні"
    pt = "Так" if s.get("penalty_for_talk_during_vote", True) else "Ні"

    kb.button(text=f"🕶 Анонімність голосу: {av}", callback_data="set:toggle:anonymous_vote")
    kb.button(text=f"🃏 Картки після вильоту (дефолт): {sc}", callback_data="set:toggle:show_cards_on_elim_default")
    kb.button(text=f"🤐 Штраф за пасивність: {ps}", callback_data="set:toggle:penalty_for_silence")
    kb.button(text=f"🔇 Штраф за балачки: {pt}", callback_data="set:toggle:penalty_for_talk_during_vote")

    kb.button(text=f"👥 Мін гравців: {s.get('min_players', 6)}", callback_data="noop")
    kb.button(text="−1", callback_data="set:min_players:-1")
    kb.button(text="+1", callback_data="set:min_players:+1")

    kb.button(text=f"👥 Макс гравців: {s.get('max_players', 15)}", callback_data="noop")
    kb.button(text="−1", callback_data="set:max_players:-1")
    kb.button(text="+1", callback_data="set:max_players:+1")

    kb.button(text="⬅️ Назад", callback_data="set:back")
    kb.adjust(1, 1, 1, 1, 1, 2, 1, 2, 1)
    return kb.as_markup()

def kb_profile() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🧬 Spec", callback_data="eco:spec")
    kb.button(text="🏪 Магазин", callback_data="eco:shop")
    kb.button(text="🏆 Топ", callback_data="eco:top")
    kb.adjust(1)
    return kb.as_markup()

def kb_shop() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, price in SHOP.items():
        kb.button(text=f"{SPEC_NAMES.get(key, key)} — {price}💰", callback_data=f"shop:buy:{key}")
    kb.adjust(1)
    return kb.as_markup()

def kb_spec(user_id: int) -> InlineKeyboardMarkup:
    user = get_user(user_id)
    kb = InlineKeyboardBuilder()

    if user.get("spec"):
        for i, item in enumerate(user["spec"]):
            kb.button(
                text=f"Використати: {SPEC_NAMES.get(item, item)}",
                callback_data=f"spec:use:{i}"
            )
    else:
        kb.button(text="Немає Spec", callback_data="noop")

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
        f"Хід: {s.get('t_turn', 60)}с | "
        f"Обговорення: {s.get('t_discussion', 60)}с | "
        f"Обвинувачення: {s.get('t_accuse', 25)}с | "
        f"Голосування: {s.get('t_vote', 15)}с"
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

async def ensure_dm_open(user_id: int) -> bool:
    try:
        await bot.send_message(user_id, "✅ Приват відкрито. Тепер я можу надсилати тобі картки.")
        return True
    except Exception:
        return False

async def deal_cards(chat_id: int, g: Game):
    g.cards.clear()
    g.revealed_total.clear()
    g.revealed_by_round.clear()

    for pid in g.players.keys():
        g.cards[pid] = random_card()
        g.revealed_total[pid] = 0

    for pid in g.players.keys():
        try:
            await bot.send_message(
                pid,
                "🧾 Твоя картка персонажа.\n"
                "Характеристики відкриваються кнопками.\n"
                "Під час презентації активний тільки поточний гравець.",
                reply_markup=kb_dm_reveal_menu(chat_id, pid, g)
            )
        except Exception:
            pass

def full_cards_text(g: Game, user_id: int) -> str:
    cards = g.cards.get(user_id, {})
    if not cards:
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

def opened_count_in_round(g: Game, user_id: int) -> int:
    return len(g.revealed_by_round.setdefault(g.round_no, {}).setdefault(user_id, set()))

def remaining_unopened_keys(g: Game, user_id: int) -> List[Tuple[str, str]]:
    all_opened: Set[str] = set()
    for rnd_map in g.revealed_by_round.values():
        all_opened.update(rnd_map.get(user_id, set()))

    result = []
    for title, key in CARD_KEYS_ORDER:
        if key not in all_opened:
            result.append((title, key))
    return result

async def auto_reveal_if_needed(chat_id: int, g: Game, user_id: int) -> bool:
    need = player_round_limit(g, user_id)
    current = opened_count_in_round(g, user_id)
    if current >= need:
        return False

    left = remaining_unopened_keys(g, user_id)
    if not left:
        return False

    title, key = random.choice(left)
    value = g.cards[user_id][key]
    g.revealed_by_round.setdefault(g.round_no, {}).setdefault(user_id, set()).add(key)
    g.revealed_total[user_id] = g.revealed_total.get(user_id, 0) + 1

    await bot.send_message(chat_id, ai_line(AI_HOST_SILENCE_PENALTY, tag=g.players[user_id].tag()))
    await bot.send_message(chat_id, f"🤖 Система відкриває автоматично:\n• {title}: {value}")
    return True

async def refresh_all_dm_menus(chat_id: int, g: Game):
    for pid in g.players.keys():
        try:
            await bot.send_message(
                pid,
                "🔄 Оновлення кнопок характеристик.",
                reply_markup=kb_dm_reveal_menu(chat_id, pid, g)
            )
        except Exception:
            pass

async def reward_all_players_for_game(g: Game):
    for pid in g.players.keys():
        add_game(pid)
        add_xp(pid, 20)

async def reward_winners(g: Game):
    for pid in g.alive_ids():
        add_win(pid)
        add_xp(pid, 50)
        add_money(pid, 50)

async def start_round_flow(chat_id: int, g: Game):
    if not g.active or g.paused:
        return

    g.phase = Phase.BRIEFING
    await cancel_timer(g)

    g.current_speaker_index = 0
    g.current_speaker_id = None
    g.presentation_run_id += 1

    base_limit = g.reveal_plan[g.round_no - 1] if 0 < g.round_no <= len(g.reveal_plan) else 1
    g.round_reveal_limit = max(1, base_limit)

    brief = int(g.settings.get("t_briefing", 20))
    warn = int(g.settings.get("t_warning", 5))

    await bot.send_message(chat_id, ai_line(AI_HOST_INTRO))
    await bot.send_message(
        chat_id,
        f"👀 Раунд {g.round_no}/{MAX_ROUNDS}\n"
        f"Ознайомлення: {brief} сек.\n"
        f"Базово кожен відкриває {g.round_reveal_limit} характеристик."
    )
    await run_timer_with_warning(chat_id, brief, warn, f"⚠️ До кінця ознайомлення {warn} сек!")

    if not g.active or g.paused:
        return

    await start_presentation_phase(chat_id, g)

async def start_presentation_phase(chat_id: int, g: Game):
    g.phase = Phase.PRESENTATION
    g.make_round_order()
    g.current_speaker_index = 0

    await bot.send_message(
        chat_id,
        "🎙 Починається презентація.\n"
        "Гравці виступають по одному. Тільки поточний гравець може відкривати характеристики."
    )

    await advance_to_next_speaker(chat_id, g)

async def advance_to_next_speaker(chat_id: int, g: Game):
    my_run_id = g.presentation_run_id
    alive_order = [pid for pid in g.order if pid in g.players and g.players[pid].alive]

    if g.current_speaker_index >= len(alive_order):
        g.current_speaker_id = None
        await start_discussion_phase(chat_id, g)
        return

    pid = alive_order[g.current_speaker_index]
    g.current_speaker_id = pid

    turn_sec = int(g.settings.get("t_turn", 60))
    warn = int(g.settings.get("t_warning", 5))
    tag = g.players[pid].tag()
    limit = player_round_limit(g, pid)

    if g.penalties_next_round_reveal_minus.get(pid, 0) > 0:
        g.penalty_round_applied.add(pid)

    await bot.send_message(chat_id, ai_line(AI_HOST_PRESENT, tag=tag, sec=turn_sec))
    if g.penalties_next_round_reveal_minus.get(pid, 0) > 0:
        await bot.send_message(chat_id, f"⚠️ {tag} має штраф цього раунду: відкриває лише {limit} характеристик.")

    await refresh_all_dm_menus(chat_id, g)

    try:
        await bot.send_message(
            pid,
            f"🎙 Твій хід.\n"
            f"У тебе {turn_sec} сек.\n"
            f"У цьому раунді відкрий {limit} характеристик.",
            reply_markup=kb_dm_reveal_menu(chat_id, pid, g)
        )
    except Exception:
        pass

    await run_timer_with_warning(chat_id, turn_sec, warn, f"⚠️ {tag}, залишилось {warn} сек!")

    if not g.active or g.paused or g.phase != Phase.PRESENTATION:
        return
    if my_run_id != g.presentation_run_id:
        return
    if g.current_speaker_id != pid:
        return

    auto_used = await auto_reveal_if_needed(chat_id, g, pid)

    if auto_used and g.settings.get("penalty_for_silence", True):
        g.penalties_next_round_reveal_minus[pid] = max(g.penalties_next_round_reveal_minus.get(pid, 0), 1)
        await bot.send_message(
            chat_id,
            f"⚠️ {tag} отримує штраф за пасивність.\n"
            "У наступному раунді він відкриє на 1 характеристику менше."
        )

    await bot.send_message(chat_id, ai_line(AI_HOST_PRESENT_END))
    g.current_speaker_index += 1
    await advance_to_next_speaker(chat_id, g)

async def start_discussion_phase(chat_id: int, g: Game):
    g.phase = Phase.DISCUSSION
    sec = int(g.settings.get("t_discussion", 60))
    warn = int(g.settings.get("t_warning", 5))

    await bot.send_message(chat_id, ai_line(AI_HOST_DISCUSS))
    await bot.send_message(chat_id, f"💬 Етап обговорення. У вас {sec} сек.")
    await run_timer_with_warning(chat_id, sec, warn, f"⚠️ До кінця обговорення {warn} сек!")

    if not g.active or g.paused:
        return

    await start_accuse_phase(chat_id, g)

async def start_accuse_phase(chat_id: int, g: Game):
    g.phase = Phase.ACCUSE
    sec = int(g.settings.get("t_accuse", 25))
    warn = int(g.settings.get("t_warning", 5))

    await bot.send_message(chat_id, ai_line(AI_HOST_ACCUSE))
    await bot.send_message(chat_id, f"📣 Етап обвинувачень. У вас {sec} сек.")
    await run_timer_with_warning(chat_id, sec, warn, f"⚠️ До кінця обвинувачень {warn} сек!")

    if not g.active or g.paused:
        return

    await auto_open_vote(chat_id, g, kind="main")

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

async def auto_open_vote(chat_id: int, g: Game, kind: str = "main"):
    g.phase = Phase.VOTE if kind == "main" else Phase.REVOTE
    g.vote_open = True
    g.votes.clear()
    g.silent_offenders.clear()
    g.vote_kind = kind

    if kind == "main":
        g.vote_targets = g.alive_ids()
        await bot.send_message(chat_id, ai_line(AI_HOST_VOTE))
        await bot.send_message(chat_id, f"🗳 Етап голосування. {g.settings.get('t_vote', 15)} сек.")
    else:
        g.vote_targets = g.justify_candidates[:]
        await bot.send_message(chat_id, "🗳 Переголосування. Голосуйте лише за кандидатів з виправдання.")

    for pid in g.alive_ids():
        VOTE_SESSIONS[pid] = chat_id
        try:
            await bot.send_message(
                pid,
                "🗳 Обери кандидата:",
                reply_markup=kb_vote(chat_id, g, voter_id=pid)
            )
        except Exception:
            pass

    await start_vote_timer(chat_id, g)

def top_candidates(counts: Dict[int, int]) -> Tuple[List[int], int]:
    if not counts:
        return [], 0
    mx = max(counts.values())
    cands = [pid for pid, c in counts.items() if c == mx]
    return cands, mx

async def auto_justify_phase(chat_id: int, g: Game):
    g.phase = Phase.JUSTIFY
    sec = int(g.settings.get("t_justify", 30))
    warn = int(g.settings.get("t_warning", 5))

    if not g.justify_candidates:
        await auto_open_vote(chat_id, g, kind="main")
        return

    tags = ", ".join(g.players[pid].tag() for pid in g.justify_candidates if pid in g.players)
    await bot.send_message(chat_id, ai_line(AI_HOST_JUSTIFY))
    await bot.send_message(chat_id, f"⚖️ На межі вигнання: {tags}")

    for pid in g.justify_candidates:
        if not g.active or g.paused or not g.players[pid].alive:
            return
        tag = g.players[pid].tag()
        await bot.send_message(chat_id, f"⚖️ {tag} має {sec} сек на виправдання.")
        await run_timer_with_warning(chat_id, sec, warn, f"⚠️ {tag}, залишилось {warn} сек!")

    if not g.active or g.paused:
        return

    await auto_open_vote(chat_id, g, kind="revote")

async def close_vote_internal(chat_id: int, g: Game, forced_by_timer: bool):
    g.vote_open = False

    alive_ids = g.alive_ids()
    allowed_targets = set(g.vote_targets if g.vote_targets else alive_ids)

    counts: Dict[int, int] = {
        pid: 0 for pid in allowed_targets
        if pid in g.players and g.players[pid].alive
    }

    for voter_id in alive_ids:
        target = g.votes.get(voter_id)
        if target in counts:
            counts[target] += 1
        else:
            if g.vote_kind == "main" and voter_id in counts:
                counts[voter_id] += 1

    if not counts:
        await bot.send_message(chat_id, "❌ Немає коректних голосів.")
        return

    cands, mx = top_candidates(counts)
    total_voters = len(alive_ids)
    mx_pct = percent(mx, total_voters)

    report_lines = [f"{g.players[pid].tag()}: {c}" for pid, c in sorted(counts.items(), key=lambda x: -x[1])]
    report = "\n".join(report_lines)

    await bot.send_message(
        chat_id,
        "📊 Результати голосування:\n"
        + ("(авто-таймер)\n" if forced_by_timer else "")
        + f"{report}\n\n"
        f"Максимум: {mx} голосів ({mx_pct:.1f}%)."
    )

    if g.settings.get("penalty_for_talk_during_vote", True):
        for uid in g.talk_vote_penalties:
            if uid in g.players and g.players[uid].alive:
                g.penalties_next_round_reveal_minus[uid] = max(g.penalties_next_round_reveal_minus.get(uid, 0), 1)

        if g.talk_vote_penalties:
            tags = ", ".join(g.players[uid].tag() for uid in g.talk_vote_penalties if uid in g.players)
            await bot.send_message(
                chat_id,
                f"⚠️ Штраф за порушення тиші в наступному раунді отримують:\n{tags}\n"
                "Вони відкриють на 1 характеристику менше."
            )

    if g.vote_kind == "main":
        if len(cands) == 1 and mx_pct >= 70.0:
            await bot.send_message(chat_id, "⚠️ 70%+ за одного кандидата. Виправдання не буде.")
            await bot.send_message(chat_id, "🚪 Етап вигнання.")
            await eliminate(chat_id, g, [cands[0]], "70%+ голосів")
            return

        g.justify_candidates = cands[:]
        await auto_justify_phase(chat_id, g)
        return

    if g.vote_kind == "revote":
        await bot.send_message(chat_id, ai_line(AI_HOST_EXILE))
        await bot.send_message(chat_id, "🚪 Етап вигнання.")
        await asyncio.sleep(int(g.settings.get("t_exile_pause", 5)))
        await eliminate(chat_id, g, cands, "Рішення після переголосування")
        return

async def eliminate(chat_id: int, g: Game, kicked_ids: List[int], reason: str):
    kicked_ids = [kid for kid in kicked_ids if kid in g.players and g.players[kid].alive]

    for kid in kicked_ids:
        g.players[kid].alive = False

    tags = ", ".join(g.players[k].tag() for k in kicked_ids)
    await bot.send_message(
        chat_id,
        "🚪 Двері бункера скриплять…\n"
        f"Причина: {reason}\n\n"
        f"❌ Вигнано: {tags}"
    )

    if kicked_ids:
        g.last_elim_id = kicked_ids[0]

    if kicked_ids:
        default_show = bool(g.settings.get("show_cards_on_elim_default", False))
        if default_show:
            for kid in kicked_ids:
                await bot.send_message(chat_id, full_cards_text(g, kid))
        else:
            for kid in kicked_ids:
                await bot.send_message(
                    chat_id,
                    f"🔎 Показати повний набір карток {g.players[kid].tag()}?",
                    reply_markup=kb_reveal_elim(kid)
                )

    if g.need_finish() or g.round_no >= MAX_ROUNDS:
        g.phase = Phase.FINISH
        await reward_all_players_for_game(g)
        await reward_winners(g)
        await bot.send_message(
            chat_id,
            f"🏁 ФІНАЛ.\nПереможці:\n{g.roster_text(True)}\n\n"
            "🎁 Нагороди:\n"
            "• +20 XP за гру всім учасникам\n"
            "• +50 XP за перемогу\n"
            "• +50💰 за перемогу"
        )
        g.active = False
        return

    g.round_no += 1
    g.clockwise = not g.clockwise
    g.make_round_order()

    g.votes.clear()
    g.silent_offenders.clear()
    g.vote_targets.clear()
    g.justify_candidates.clear()
    g.vote_kind = "main"
    g.current_speaker_index = 0
    g.current_speaker_id = None
    g.round_reveal_limit = 0
    g.presentation_run_id += 1

    for uid in list(g.penalty_round_applied):
        g.penalties_next_round_reveal_minus[uid] = 0
    g.penalty_round_applied.clear()
    g.talk_vote_penalties.clear()

    await start_round_flow(chat_id, g)


async def post_intro(chat_id: int, g: Game):
    await bot.send_message(
        chat_id,
        f"{ai_line(AI_HOST_INTRO)}\n\n"
        f"☢️ Катаклізм: {g.catastrophe}\n\n"
        f"{g.bunker_desc}\n"
        f"👁 Місць у бункері: {g.slots} із {len(g.players)}.\n\n"
        "📩 Картки роздано в ЛС."
    )

@dp.message(CommandStart())
async def cmd_start(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    text = message.text or ""
    parts = text.split(maxsplit=1)
    ref_code = parts[1].strip() if len(parts) > 1 else ""

    if u and ref_code.isdigit():
        ref_id = int(ref_code)
        me = get_user(u.id)

        if ref_id != u.id and int(me.get("ref_by", 0)) == 0:
            users = load_users()

            if str(ref_id) not in users:
                users[str(ref_id)] = DEFAULT_USER.copy()

            me["ref_by"] = ref_id
            users[str(u.id)] = me

            ref_user = users.get(str(ref_id), DEFAULT_USER.copy())
            ref_user["refs"] = int(ref_user.get("refs", 0)) + 1
            ref_user["money"] = int(ref_user.get("money", 0)) + 50
            users[str(ref_id)] = ref_user

            save_users(users)

            try:
                await bot.send_message(
                    ref_id,
                    f"🎉 Новий реферал!\n\n"
                    f"👤 Користувач: {u.full_name}\n"
                    f"💰 Нагорода: +50 монет"
                )
            except Exception:
                pass

    if message.chat.type == "private":
        await message.answer("✅ Приват активовано. Повернись у групу.")
        return

    await message.answer(
        "🏚 BUNKER UA BOT\n\n"
        "Команди:\n"
        "• /new — створити лобі\n"
        "• /players — список гравців\n"
        "• /leave — вийти з лобі\n"
        "• /startgame — старт гри\n"
        "• /status — стан гри\n"
        "• /profile — профіль\n"
        "• /shop — магазин\n"
        "• /spec — мої Spec\n"
        "• /daily — щоденний бонус\n"
        "• /top — топ гравців\n"
        "• /ref — реферальна система\n"
        "• /stats — статистика бота\n"
        "• /next — форс наступного етапу\n"
        "• /openvote — форс відкрити голосування\n"
        "• /closevote — форс закрити голосування\n"
        "• /settings — налаштування\n"
        "• /pause, /resume — пауза/відновлення (OWNER)\n"
        "• /end — завершити гру"
    )

@dp.message(Command("new"))
async def cmd_new(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

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

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if message.chat.type == "private":
        await message.answer("Ця команда працює у групі.")
        return
    await message.answer("👥 Гравці:\n" + g.roster_text(only_alive=False))

@dp.message(Command("leave"))
async def cmd_leave(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if message.chat.type == "private":
        await message.answer("Ця команда працює у групі.")
        return
    if g.active:
        await message.answer("Гра вже стартувала — вийти не можна.")
        return

    if not u:
        return
    if u.id not in g.players:
        await message.answer("Тебе немає в лобі.")
        return

    tag = g.players[u.id].tag()
    del g.players[u.id]
    await message.answer(f"❌ {tag} вийшов. Гравців: {len(g.players)}")
    await update_lobby(message.chat.id, g)

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    u = message.from_user
    if not u:
        return
    touch_user_profile(u.id, u.full_name, u.username or "")
    await message.answer(profile_text(u.id, u.full_name), reply_markup=kb_profile())

@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    u = message.from_user
    if not u:
        return
    touch_user_profile(u.id, u.full_name, u.username or "")
    await message.answer(shop_text(u.id), reply_markup=kb_shop())

@dp.message(Command("spec"))
async def cmd_spec(message: Message):
    u = message.from_user
    if not u:
        return
    touch_user_profile(u.id, u.full_name, u.username or "")
    await message.answer(spec_text(u.id), reply_markup=kb_spec(u.id))

@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    u = message.from_user
    if not u:
        return

    touch_user_profile(u.id, u.full_name, u.username or "")
    user = get_user(u.id)
    now_ts = int(time.time())

    last_ts = int(user.get("daily_ts", 0))
    cooldown = 60 * 60 * 24

    if now_ts - last_ts < cooldown:
        left = cooldown - (now_ts - last_ts)
        hours = left // 3600
        mins = (left % 3600) // 60
        await message.answer(f"⏳ Daily уже забрано.\nСпробуй через {hours}г {mins}хв.")
        return

    user["daily_ts"] = now_ts
    user["money"] = int(user.get("money", 0)) + 25
    update_user(u.id, user)

    await message.answer("🎁 Daily бонус: +25💰")

@dp.message(Command("top"))
async def cmd_top(message: Message):
    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")
    await message.answer(build_top_text())

@dp.message(Command("ref"))
async def cmd_ref(message: Message):
    u = message.from_user
    if not u:
        return

    touch_user_profile(u.id, u.full_name, u.username or "")
    me = await bot.get_me()
    bot_username = me.username or "your_bot"

    await message.answer(build_ref_text(u.id, bot_username))

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id if message.from_user else None

    if not is_owner(user_id):
        await message.answer("⛔ Тільки для OWNER")
        return

    await message.answer(build_stats_text())

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    uid = message.from_user.id if message.from_user else None
    if uid:
        touch_user_profile(uid, message.from_user.full_name, message.from_user.username or "")

    if message.chat.type == "private":
        await message.answer("⚙️ Налаштування відкриваються командою /settings у групі.")
        return
    if g.active:
        await message.answer("⛔ Налаштування можна змінювати тільки коли гри немає.")
        return

    if uid is None:
        return
    if not await is_admin_or_owner(message.chat.id, uid):
        await message.answer("⛔ Тільки OWNER або адмін чату.")
        return

    g.settings = get_chat_settings(message.chat.id)
    SETTINGS_SESSIONS[uid] = message.chat.id

    try:
        await bot.send_message(uid, "⚙️ Налаштування", reply_markup=kb_settings_main())
        await message.answer("✅ Налаштування відправив у ПП.")
    except Exception:
        await message.answer("⚠️ Відкрий ПП з ботом через /start, потім повтори /settings.")

@dp.message(Command("pause"))
async def cmd_pause(message: Message):
    g = get_game(message.chat.id)
    if not is_owner(message.from_user.id if message.from_user else None):
        return
    g.paused = True
    await cancel_timer(g)
    await message.answer("⏸ Бот поставлено на паузу.")

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

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

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

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if not g.active:
        await message.answer("Немає активної гри.")
        return

    speaker = g.players[g.current_speaker_id].tag() if g.current_speaker_id in g.players else "—"

    await message.answer(
        f"📌 Стан гри:\n"
        f"Раунд: {g.round_no}/{MAX_ROUNDS}\n"
        f"Фаза: {g.phase}\n"
        f"Поточний гравець: {speaker}\n"
        f"Живі: {len(g.alive_ids())} | Місць: {g.slots}\n"
        f"Голосування: {'відкрите' if g.vote_open else 'закрите'}"
    )

@dp.message(Command("startgame"))
async def cmd_startgame(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if message.chat.type == "private":
        await message.answer("Стартуй гру у групі.")
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

    if not u:
        return
    g.host_id = u.id

    missing = []
    for pid in list(g.players.keys()):
        ok = await ensure_dm_open(pid)
        if not ok:
            missing.append(pid)

    if missing:
        await message.answer("⚠️ Дехто не відкрив ЛС. Нехай натиснуть /start у ПП і повтори /startgame.")
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
        get_user(p.user_id)

    g.votes.clear()
    g.silent_offenders.clear()
    g.vote_open = False
    g.vote_kind = "main"
    g.vote_targets.clear()
    g.justify_candidates.clear()
    g.current_speaker_index = 0
    g.current_speaker_id = None
    g.round_reveal_limit = 0
    g.presentation_run_id = 0
    g.penalties_next_round_reveal_minus.clear()
    g.penalty_round_applied.clear()
    g.talk_vote_penalties.clear()

    g.make_round_order()

    await post_intro(message.chat.id, g)
    await deal_cards(message.chat.id, g)
    await start_round_flow(message.chat.id, g)

@dp.message(Command("next"))
async def cmd_next(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    uid = u.id if u else None
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if uid is None or not (uid == g.host_id or is_owner(uid)):
        await message.answer("Тільки хост або OWNER може форсити фазу.")
        return

    if not g.active:
        await message.answer("Гра не стартувала.")
        return

    await cancel_timer(g)

    if g.phase == Phase.PRESENTATION:
        if g.current_speaker_id in g.players:
            await auto_reveal_if_needed(message.chat.id, g, g.current_speaker_id)
        g.presentation_run_id += 1
        g.current_speaker_index += 1
        g.current_speaker_id = None
        await advance_to_next_speaker(message.chat.id, g)
        return

    if g.phase == Phase.BRIEFING:
        await start_presentation_phase(message.chat.id, g)
        return

    if g.phase == Phase.DISCUSSION:
        await start_accuse_phase(message.chat.id, g)
        return

    if g.phase == Phase.ACCUSE:
        await auto_open_vote(message.chat.id, g, kind="main")
        return

    if g.phase == Phase.JUSTIFY:
        await auto_open_vote(message.chat.id, g, kind="revote")
        return

    await message.answer("Зараз /next не потрібен.")

@dp.message(Command("openvote"))
async def cmd_openvote(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    uid = u.id if u else None
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if not g.active:
        await message.answer("Гра не стартувала.")
        return

    if uid is None or not (uid == g.host_id or is_owner(uid)):
        await message.answer("Відкрити голосування може тільки хост або OWNER.")
        return

    await cancel_timer(g)
    await auto_open_vote(message.chat.id, g, kind="main")

@dp.message(Command("closevote"))
async def cmd_closevote(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return

    u = message.from_user
    uid = u.id if u else None
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if not g.active:
        await message.answer("Гра не стартувала.")
        return

    if uid is None or not (uid == g.host_id or is_owner(uid)):
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

@dp.callback_query(F.data == "eco:shop")
async def cb_eco_shop(call: CallbackQuery):
    uid = call.from_user.id
    touch_user_profile(uid, call.from_user.full_name, call.from_user.username or "")
    if call.message:
        await call.message.edit_text(shop_text(uid), reply_markup=kb_shop())
    await call.answer()

@dp.callback_query(F.data == "eco:spec")
async def cb_eco_spec(call: CallbackQuery):
    uid = call.from_user.id
    touch_user_profile(uid, call.from_user.full_name, call.from_user.username or "")
    if call.message:
        await call.message.edit_text(spec_text(uid), reply_markup=kb_spec(uid))
    await call.answer()

@dp.callback_query(F.data == "eco:top")
async def cb_eco_top(call: CallbackQuery):
    if call.from_user:
        touch_user_profile(call.from_user.id, call.from_user.full_name, call.from_user.username or "")
    if call.message:
        await call.message.edit_text(build_top_text())
    await call.answer()

@dp.callback_query(F.data.startswith("shop:buy:"))
async def cb_shop_buy(call: CallbackQuery):
    uid = call.from_user.id
    touch_user_profile(uid, call.from_user.full_name, call.from_user.username or "")
    spec_name = call.data.split(":")[2]

    if spec_name not in SHOP:
        await call.answer("Невідомий товар", show_alert=True)
        return

    user = get_user(uid)
    price = SHOP[spec_name]

    if int(user["money"]) < price:
        await call.answer("Недостатньо монет 💸", show_alert=True)
        return

    user["money"] -= price
    user["spec"].append(spec_name)
    update_user(uid, user)

    if call.message:
        await call.message.edit_text(
            f"✅ Куплено: {SPEC_NAMES.get(spec_name, spec_name)}\n\n" + shop_text(uid),
            reply_markup=kb_shop()
        )

    await call.answer("Покупка успішна ✅")

@dp.callback_query(F.data.startswith("spec:use:"))
async def cb_spec_use(call: CallbackQuery):
    uid = call.from_user.id
    touch_user_profile(uid, call.from_user.full_name, call.from_user.username or "")

    try:
        idx = int(call.data.split(":")[2])
    except Exception:
        await call.answer("Помилка", show_alert=True)
        return

    user = get_user(uid)
    specs = user.get("spec", [])

    if idx < 0 or idx >= len(specs):
        await call.answer("Spec не знайдено", show_alert=True)
        return

    used_item = specs.pop(idx)
    user["spec"] = specs
    update_user(uid, user)

    if call.message:
        await call.message.edit_text(
            f"🧬 Використано: {SPEC_NAMES.get(used_item, used_item)}\n\n" + spec_text(uid),
            reply_markup=kb_spec(uid)
        )

    await call.answer(f"Використано {SPEC_NAMES.get(used_item, used_item)} ✅")

@dp.callback_query(F.data == "lobby:join")
async def cb_join(call: CallbackQuery):
    if call.message is None:
        return
    g = get_game(call.message.chat.id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if call.message.chat.type == "private":
        await call.answer("Гра працює у групі.", show_alert=True)
        return

    if g.active:
        await call.answer("Гра вже йде.", show_alert=True)
        return

    if not g.lobby_open:
        await call.answer("Реєстрація закрита.", show_alert=True)
        return

    u = call.from_user
    touch_user_profile(u.id, u.full_name, u.username or "")

    if u.id in g.players:
        await call.answer("Ти вже в лобі.", show_alert=False)
        return

    max_p = int(g.settings.get("max_players", 15))
    if len(g.players) >= max_p:
        await call.answer(f"Максимум {max_p} гравців.", show_alert=True)
        return

    g.players[u.id] = Player(user_id=u.id, name=u.full_name, username=(u.username or ""))
    await call.answer("✅ Додано", show_alert=False)
    await update_lobby(call.message.chat.id, g)

@dp.callback_query(F.data.startswith("revealpick:"))
async def cb_reveal_pick(call: CallbackQuery):
    if call.message is None:
        return

    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Помилка кнопки", show_alert=True)
        return

    chat_id = int(parts[1])
    key = parts[2]
    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return

    if not g.active:
        await call.answer("Гри немає.", show_alert=True)
        return

    if g.phase != Phase.PRESENTATION:
        await call.answer("Зараз не фаза презентації.", show_alert=True)
        return

    uid = call.from_user.id
    touch_user_profile(uid, call.from_user.full_name, call.from_user.username or "")

    if uid not in g.players or not g.players[uid].alive:
        await call.answer("Ти не у грі.", show_alert=True)
        return

    if uid != g.current_speaker_id:
        await call.answer("Зараз не твій хід.", show_alert=True)
        return

    if key not in g.cards.get(uid, {}):
        await call.answer("Невідома характеристика.", show_alert=True)
        return

    round_map = g.revealed_by_round.setdefault(g.round_no, {})
    opened = round_map.setdefault(uid, set())
    limit = player_round_limit(g, uid)

    all_prev_opened: Set[str] = set()
    for rnd_map in g.revealed_by_round.values():
        all_prev_opened.update(rnd_map.get(uid, set()))

    if key in all_prev_opened:
        await call.answer("Ця характеристика вже відкривалась раніше.", show_alert=True)
        return

    if len(opened) >= limit:
        await call.answer(f"У цьому раунді можна відкрити лише {limit}.", show_alert=True)
        return

    opened.add(key)
    g.revealed_total[uid] = g.revealed_total.get(uid, 0) + 1

    title = CARD_TITLES[key]
    value = g.cards[uid][key]
    tag = g.players[uid].tag()

    await call.answer("✅ Відкрито", show_alert=False)

    try:
        await call.message.edit_reply_markup(reply_markup=kb_dm_reveal_menu(chat_id, uid, g))
    except Exception:
        pass

    await bot.send_message(chat_id, f"🃏 {tag} відкриває характеристику:\n• {title}: {value}")

    if len(opened) >= limit:
        await bot.send_message(chat_id, f"✅ {tag} відкрив потрібну кількість характеристик.")
        g.presentation_run_id += 1
        await cancel_timer(g)
        g.current_speaker_index += 1
        g.current_speaker_id = None
        await advance_to_next_speaker(chat_id, g)

@dp.callback_query(F.data.startswith("vote:"))
async def cb_vote(call: CallbackQuery):
    if call.message is None:
        return

    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Помилка кнопки", show_alert=True)
        return

    try:
        chat_id = int(parts[1])
        target_id = int(parts[2])
    except Exception:
        await call.answer("Помилка кнопки", show_alert=True)
        return

    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return
    if not g.active or not g.vote_open:
        await call.answer("Зараз немає відкритого голосування.", show_alert=True)
        return

    voter_id = call.from_user.id
    touch_user_profile(voter_id, call.from_user.full_name, call.from_user.username or "")

    if voter_id not in g.players or not g.players[voter_id].alive:
        await call.answer("Голосують лише живі гравці.", show_alert=True)
        return

    allowed_targets = set(g.vote_targets if g.vote_targets else g.alive_ids())

    if target_id not in allowed_targets:
        await call.answer("Цей кандидат недоступний.", show_alert=True)
        return
    if target_id == voter_id:
        await call.answer("Сам за себе не можна 😈", show_alert=True)
        return

    g.votes[voter_id] = target_id
    target_tag = g.players[target_id].tag()

    if g.settings.get("anonymous_vote", True):
        await call.answer("✅ Голос зараховано", show_alert=False)
    else:
        await call.answer(f"✅ Ти проголосував за {target_tag}", show_alert=False)

@dp.callback_query(F.data.startswith("elimreveal:"))
async def cb_elimreveal(call: CallbackQuery):
    if call.message is None:
        return

    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Помилка кнопки", show_alert=True)
        return

    action = parts[1]
    target_id = int(parts[2])

    if call.message.chat.type == "private":
        await call.answer("Ця кнопка працює у групі.", show_alert=True)
        return

    chat_id = call.message.chat.id
    g = get_game(chat_id)

    if blocked_by_pause_for_callback(g, call):
        await call.answer("Пауза.", show_alert=False)
        return

    uid = call.from_user.id
    touch_user_profile(uid, call.from_user.full_name, call.from_user.username or "")

    if not await is_admin_or_owner(chat_id, uid):
        await call.answer("⛔ Тільки OWNER або адмін чату", show_alert=True)
        return

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
    if len(parts) < 2:
        await call.answer("Помилка кнопки", show_alert=True)
        return

    user_id = call.from_user.id
    touch_user_profile(user_id, call.from_user.full_name, call.from_user.username or "")

    if user_id not in SETTINGS_SESSIONS:
        await call.answer("Відкрий /settings у групі ще раз.", show_alert=True)
        return

    chat_id = SETTINGS_SESSIONS[user_id]
    g = get_game(chat_id)

    if g.active:
        await call.answer("⛔ Під час гри не можна змінювати налаштування.", show_alert=True)
        return
    if not await is_admin_or_owner(chat_id, user_id):
        await call.answer("⛔ Тільки OWNER або адмін чату", show_alert=True)
        return

    s = g.settings if g.settings else get_chat_settings(chat_id)
    action = parts[1]

    if action == "timers":
        await call.message.edit_text("⏱ Таймери", reply_markup=kb_settings_timers(s))
        await call.answer()
        return

    if action == "rules":
        await call.message.edit_text(RULES_TEXT, reply_markup=kb_settings_rules(s))
        await call.answer()
        return

    if action == "back":
        await call.message.edit_text("⚙️ Налаштування", reply_markup=kb_settings_main())
        await call.answer()
        return

    if action == "save":
        set_chat_settings(chat_id, s)
        g.settings = s
        await call.message.edit_text("✅ Налаштування збережені.", reply_markup=kb_settings_main())
        await call.answer("✅ Збережено")
        return

    if action == "toggle":
        if len(parts) < 3:
            await call.answer("Помилка toggle", show_alert=True)
            return
        key = parts[2]
        if key in (
            "anonymous_vote",
            "show_cards_on_elim_default",
            "penalty_for_silence",
            "penalty_for_talk_during_vote",
        ):
            s[key] = not bool(s.get(key, DEFAULT_SETTINGS.get(key, False)))
        else:
            await call.answer("Невідомий параметр", show_alert=True)
            return
        g.settings = s
        await call.message.edit_reply_markup(reply_markup=kb_settings_rules(s))
        await call.answer("✅")
        return

    if len(parts) < 3:
        await call.answer("Помилка параметра", show_alert=True)
        return

    key = parts[1]
    try:
        delta = int(parts[2].replace("+", ""))
    except Exception:
        await call.answer("Помилка числа", show_alert=True)
        return

    if key not in s:
        await call.answer("Невідомий параметр", show_alert=True)
        return

    newv = int(s.get(key, DEFAULT_SETTINGS.get(key, 0))) + delta

    if key.startswith("t_"):
        newv = max(1, min(600, newv))
    if key in ("min_players", "max_players"):
        newv = max(2, min(30, newv))
        if key == "min_players":
            newv = min(newv, int(s.get("max_players", 15)))
        if key == "max_players":
            newv = max(newv, int(s.get("min_players", 6)))

    s[key] = newv
    g.settings = s

    if key in (
        "min_players",
        "max_players",
        "anonymous_vote",
        "show_cards_on_elim_default",
        "penalty_for_silence",
        "penalty_for_talk_during_vote",
    ):
        await call.message.edit_reply_markup(reply_markup=kb_settings_rules(s))
    else:
        await call.message.edit_reply_markup(reply_markup=kb_settings_timers(s))

    await call.answer(f"✅ {newv}")

@dp.message(F.text)
async def any_text(message: Message):
    g = get_game(message.chat.id)
    if blocked_by_pause_for_message(g, message):
        return
    if not g.active:
        return

    u = message.from_user
    if u:
        touch_user_profile(u.id, u.full_name, u.username or "")

    if g.vote_open and message.chat.type != "private":
        txt = (message.text or "").strip()
        if not txt.startswith("/"):
            if u and u.id in g.players and g.players[u.id].alive:
                g.silent_offenders.add(u.id)
                g.talk_vote_penalties.add(u.id)
                try:
                    await message.reply(ai_line(AI_HOST_TALK_PENALTY, tag=g.players[u.id].tag()))
                except Exception:
                    pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())