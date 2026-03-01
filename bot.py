import os
import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

MAX_ROUNDS = 7

OWNER_ID = 1123645206 

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

GENDERS = ["Чоловік", "Жінка", "Небінарна особа"]
BODIES = ["Худорлявий", "Спортивний", "Повний", "Міцної статури", "Невисокий", "Високий"]
TRAITS = ["Лідер", "Емпат", "Параноїк", "Оптиміст", "Цинік", "Педант", "Хитрий", "Сміливий", "Панікер", "Спокійний"]

PROFESSIONS = [
    "Лікар", "Фельдшер", "Медсестра", "Інженер", "Електрик", "Механік", "Будівельник",
    "Пожежник", "Військовий", "Поліцейський", "Психолог", "Фермер", "Кухар", "Вчитель",
    "Програміст", "Хімік", "Біолог", "Водій", "Радіоаматор", "Кравець"
]

HEALTH = ["Здоровий", "Астма", "Діабет", "Гіпертонія", "Проблеми зі спиною", "Алергія", "Після травми коліна"]
HOBBIES = ["Риболовля", "Кемпінг", "Ремонт техніки", "Кулінарія", "Садівництво", "Шахи", "Біг", "Фотографія", "Плавання"]
PHOBIAS = ["Клаустрофобія", "Арахнофобія", "Гідрофобія", "Ніктoфобія", "Аерофобія", "Соціофобія", "Гемофобія"]

BIG_ITEMS = ["Аптечний кейс", "Набір інструментів", "Радіостанція", "Намет і спальник", "Бронежилет", "Лук і стріли", "Переносний фільтр води"]
BACKPACK = ["Ліхтарик", "Ніж", "Запальничка", "Турнікет", "Бинти", "Фільтр-пляшка", "Компас", "Батарейки", "Сірники", "Мультиінструмент"]

EXTRA_INFO = [
    "Знає азбуку Морзе", "Вміє шити та лагодити одяг", "Вміє робити саморобні фільтри",
    "Знає першу допомогу", "Має навички переговорів", "Знає їстівні рослини"
]

SPECIALS = [
    "Може вилікувати 1 хворобу (1 раз за гру)",
    "Може перевірити 1 характеристику іншого (1 раз за гру)",
    "Може зняти 1 голос з будь-кого (1 раз за гру)",
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

class Phase(str, Enum):
    LOBBY = "lobby"
    ROUND_START = "round_start"
    PRESENTATION = "presentation"
    DISCUSSION = "discussion"
    SPEECHES = "speeches"
    VOTE = "vote"
    JUSTIFY = "justify"
    REVOTE = "revote"
    FAREWELL = "farewell"
    FINISH = "finish"

@dataclass
class Player:
    user_id: int
    name: str
    username: str = ""
    alive: bool = True

    skip_speech_next_round: bool = False 

    profile: Dict[str, str] = field(default_factory=dict)  
    revealed: Set[str] = field(default_factory=set)

    def tag(self) -> str:
        return f"@{self.username}" if self.username else self.name

@dataclass
class Game:
    active: bool = False
    paused: bool = False 
    host_id: Optional[int] = None

    catastrophe: str = ""
    bunker_desc: str = ""

    phase: Phase = Phase.LOBBY
    round_no: int = 0

    clockwise: bool = True
    order: List[int] = field(default_factory=list)

    players: Dict[int, Player] = field(default_factory=dict)

    slots: int = 0
    reveal_plan: List[int] = field(default_factory=list)

    vote_open: bool = False
    votes: Dict[int, int] = field(default_factory=dict)  # voter -> target
    silent_offenders: Set[int] = field(default_factory=set)

    justified_this_round: Set[int] = field(default_factory=set)
    justify_candidates: List[int] = field(default_factory=list)
    revote_mode: bool = False

    skipvote_open: bool = False
    skipvote_yes: Set[int] = field(default_factory=set)
    skipped_vote_in_round1: bool = False

    pending_elims_this_round: int = 1

    timer_task: Optional[asyncio.Task] = None  

    speeches_task: Optional[asyncio.Task] = None
    speeches_order: List[int] = field(default_factory=list)
    speeches_index: int = 0

    presentation_task: Optional[asyncio.Task] = None
    presentation_order: List[int] = field(default_factory=list)
    presentation_index: int = 0

    def alive_ids(self) -> List[int]:
        return [pid for pid, p in self.players.items() if p.alive]

    def alive_players(self) -> List[Player]:
        return [p for p in self.players.values() if p.alive]

    def roster_text(self, only_alive: bool = True) -> str:
        plist = self.alive_players() if only_alive else list(self.players.values())
        lines = []
        for i, p in enumerate(plist, start=1):
            status = "" if p.alive else " (вибув)"
            lines.append(f"{i}. {p.tag()}{status}")
        return "\n".join(lines) if lines else "—"

    def alive_list_index(self) -> List[int]:
        return [p.user_id for p in self.alive_players()]

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

def is_owner(user_id: Optional[int]) -> bool:
    return user_id == OWNER_ID

def blocked_by_pause(g: Game, command_name: str, user_id: Optional[int]) -> bool:
    if not g.paused:
        return False
    if command_name == "resume" and user_id == OWNER_ID:
        return False
    return True

def is_host(g: Game, user_id: Optional[int]) -> bool:
    return (user_id is not None) and (g.host_id == user_id)

def gen_profile() -> Dict[str, str]:
    return {
        "Стать": random.choice(GENDERS),
        "Тілобудова": random.choice(BODIES),
        "Людська риса": random.choice(TRAITS),
        "Професія": random.choice(PROFESSIONS),
        "Здоровʼя": random.choice(HEALTH),
        "Хобі / Увл": random.choice(HOBBIES),
        "Фобія / Страх": random.choice(PHOBIAS),
        "Крупний інвентар": random.choice(BIG_ITEMS),
        "Рюкзак": ", ".join(random.sample(BACKPACK, k=3)),
        "Дод. свідчення": random.choice(EXTRA_INFO),
        "Спец. можливість": random.choice(SPECIALS),
    }


def format_profile(p: Player) -> str:
    lines = [
        "🧬 Твій персонаж у «Бункер Онлайн»",
        f"👤 Ти: {p.tag()}",
        "",
    ]
    for k, v in p.profile.items():
        lines.append(f"• {k}: {v}")
    lines.append("\n⚠️ Не показуй це повідомлення в чаті 😉")
    return "\n".join(lines)


async def send_profiles_private(bot: Bot, g: Game, chat_id: int):
    failed = []
    for pid, p in g.players.items():
        if not p.alive:
            continue
        try:
            await bot.send_message(pid, format_profile(p))
        except Exception:
            failed.append(p.tag())

    if failed:
        await bot.send_message(
            chat_id,
            "⚠️ Я не зміг надіслати анкети в приват цим гравцям:\n"
            + "\n".join(failed)
            + "\n\n👉 Нехай кожен з них відкриє бота в приваті та натисне Start."
            "\nПісля цього перезапусти гру: /new → /join → /startgame"
        )

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Немає BOT_TOKEN у .env")

bot = Bot(TOKEN)
dp = Dispatcher()

def cancel_timer(g: Game):
    if g.timer_task and not g.timer_task.done():
        g.timer_task.cancel()
    g.timer_task = None


def cancel_speeches(g: Game):
    if g.speeches_task and not g.speeches_task.done():
        g.speeches_task.cancel()
    g.speeches_task = None
    g.speeches_order = []
    g.speeches_index = 0


def cancel_presentation(g: Game):
    if g.presentation_task and not g.presentation_task.done():
        g.presentation_task.cancel()
    g.presentation_task = None
    g.presentation_order = []
    g.presentation_index = 0


def cancel_all_tasks(g: Game):
    cancel_timer(g)
    cancel_speeches(g)
    cancel_presentation(g)


async def start_openvote_auto(chat_id: int):
    g = get_game(chat_id)
    if not g.active or g.paused:
        return
    if g.vote_open:
        return

    g.phase = Phase.VOTE
    g.vote_open = True
    g.votes.clear()
    g.silent_offenders.clear()

    alive = g.alive_players()
    roster = [f"{i}. {p.tag()}" for i, p in enumerate(alive, start=1)]
    extra = "\n\n(У 1 раунді можна запропонувати пропуск: /skipvote)" if g.round_no == 1 else ""

    await bot.send_message(
        chat_id,
        "🗳 ГОЛОСУВАННЯ.\n"
        "15 секунд тиші. Будь-які повідомлення = штраф.\n\n"
        "Голос: /vote <номер>\n"
        + "\n".join(roster)
        + extra
    )


async def speeches_runner(chat_id: int):
    g = get_game(chat_id)
    try:
        g.speeches_order = [pid for pid in g.order if pid in g.players and g.players[pid].alive]
        g.speeches_index = 0

        await bot.send_message(
            chat_id,
            "⚖️ Етап 3: ОБВИНУВАЧЕННЯ / ЗАХИСТ.\n"
            "Бот по черзі дає слово кожному на 30 секунд.\n"
            "Після останнього — голосування відкриється автоматично ✅"
        )

        while g.speeches_index < len(g.speeches_order):
            if not g.active or g.paused or g.phase != Phase.SPEECHES:
                return

            pid = g.speeches_order[g.speeches_index]
            g.speeches_index += 1

            p = g.players.get(pid)
            if not p or not p.alive:
                continue

            if p.skip_speech_next_round:
                await bot.send_message(chat_id, f"⏭ {p.tag()} пропускає 30-сек виступ (штраф за порушення тиші).")
                continue

            await bot.send_message(chat_id, f"🎤 Слово має {p.tag()} — 30 секунд!")
            await asyncio.sleep(30)

        if not g.active or g.paused or g.phase != Phase.SPEECHES:
            return

        await bot.send_message(chat_id, "✅ Виступи завершено. Відкриваю голосування…")
        await start_openvote_auto(chat_id)

    except asyncio.CancelledError:
        return


async def discussion_timer(chat_id: int):
    g = get_game(chat_id)
    try:
        await asyncio.sleep(60)
    except asyncio.CancelledError:
        return

    if (not g.active) or g.paused or g.phase != Phase.DISCUSSION:
        return

    g.phase = Phase.SPEECHES
    cancel_speeches(g)
    g.speeches_task = asyncio.create_task(speeches_runner(chat_id))


async def presentation_runner(chat_id: int):
    g = get_game(chat_id)
    try:
        g.presentation_order = [pid for pid in g.order if pid in g.players and g.players[pid].alive]
        g.presentation_index = 0

        plan = g.reveal_plan[g.round_no - 1] if g.round_no >= 1 else 0
        await bot.send_message(
            chat_id,
            f"🎙 Раунд {g.round_no}. Етап 1: ПРЕЗЕНТАЦІЯ.\n"
            "Бот по черзі дає слово кожному на 1 хвилину.\n"
            f"Кожен відкриває характеристик: {plan}.\n\n"
        )

        while g.presentation_index < len(g.presentation_order):
            if not g.active or g.paused or g.phase != Phase.PRESENTATION:
                return

            pid = g.presentation_order[g.presentation_index]
            g.presentation_index += 1

            p = g.players.get(pid)
            if not p or not p.alive:
                continue

            await bot.send_message(chat_id, f"🗣 Слово має {p.tag()} — 1 хвилина!")
            await asyncio.sleep(60)

        if not g.active or g.paused or g.phase != Phase.PRESENTATION:
            return

        g.phase = Phase.DISCUSSION
        await bot.send_message(
            chat_id,
            "💬 Етап 2: КОЛЕКТИВНЕ ОБГОВОРЕННЯ.\n"
            "⏳ У вас є 1 хвилина.\n\n"
        )

        cancel_timer(g)
        g.timer_task = asyncio.create_task(discussion_timer(chat_id))

    except asyncio.CancelledError:
        return

@dp.message(Command("start"))
async def start_cmd(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "start", uid):
        return

    await message.answer(
        "☢️ «Бункер Онлайн» (UA).\n\n"
        "Команди:\n"
        "• /new — створити лобі\n"
        "• /join — приєднатись\n"
        "• /leave — вийти\n"
        "• /players — список\n"
        "• /startgame — старт\n"
        "• /next — запуск авто-етапів (хост)\n"
        "• /vote <номер> — голос\n"
        "• /skipvote — пропуск голосування (лише 1 раунд)\n"
        "• /skip — голос за пропуск\n"
        "• /closevote — закрити голосування (хост)\n"
        "• /pause — ПАУЗА\n"
        "• /resume — ВІДНОВИТИ\n"
        "• /myid — показати твій Telegram ID\n"
        "• /status — стан гри\n"
        "• /end — завершити гру\n"
    )


@dp.message(Command("myid"))
async def myid(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "myid", uid):
        return
    if message.from_user:
        await message.answer(f"Твій ID: {message.from_user.id}")


@dp.message(Command("pause"))
async def pause(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if not is_owner(uid):
        return
    cancel_all_tasks(g)
    g.paused = True


@dp.message(Command("resume"))
async def resume(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if not is_owner(uid):
        return
    g.paused = False
    await message.answer("▶ Відновлено. Бот знову активний.")


@dp.message(Command("new"))
async def new_lobby(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "new", uid):
        return

    cancel_all_tasks(g)
    g.__dict__.update(Game().__dict__)
    await message.answer("🧩 Лобі створено.\nЗаходьте: /join\nКоли готові — /startgame")


@dp.message(Command("join"))
async def join(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "join", uid):
        return

    if message.chat.type == "private":
        await message.answer("Додай мене у групу — гра працює в чаті 🙂")
        return

    if g.active:
        await message.answer("Гра вже йде. Чекай наступної 🙂")
        return

    u = message.from_user
    if not u:
        return

    if u.id in g.players:
        await message.answer("Ти вже в лобі.")
        return

    g.players[u.id] = Player(user_id=u.id, name=u.full_name, username=(u.username or ""))
    await message.answer(f"✅ {g.players[u.id].tag()} приєднався.\nГравців: {len(g.players)}")


@dp.message(Command("leave"))
async def leave(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "leave", uid):
        return

    u = message.from_user
    if not u:
        return
    if g.active:
        await message.answer("Гра вже стартувала — вийти не можна.")
        return
    if u.id not in g.players:
        await message.answer("Тебе немає в лобі.")
        return
    tag = g.players[u.id].tag()
    del g.players[u.id]
    await message.answer(f"❌ {tag} вийшов. Гравців: {len(g.players)}")


@dp.message(Command("players"))
async def players(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "players", uid):
        return
    await message.answer("👥 Гравці:\n" + g.roster_text(only_alive=False))


@dp.message(Command("startgame"))
async def startgame(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "startgame", uid):
        return

    if message.chat.type == "private":
        await message.answer("Стартуй гру в групі 🙂")
        return

    if g.active:
        await message.answer("Гра вже йде.")
        return

    if len(g.players) < 6:
        await message.answer("Потрібно мінімум 6 гравців.")
        return

    cancel_all_tasks(g)
    g.active = True
    g.host_id = message.from_user.id if message.from_user else None

    g.catastrophe = random.choice(CATASTROPHES)
    g.bunker_desc = build_bunker_desc()

    g.slots = bunker_slots(len(g.players))
    g.reveal_plan = reveals_per_round(len(g.players))

    g.round_no = 1
    g.clockwise = True
    g.pending_elims_this_round = 1

    for p in g.players.values():
        p.alive = True
        p.skip_speech_next_round = False

    for p in g.players.values():
        p.profile = gen_profile()
        p.revealed.clear()

    await send_profiles_private(bot, g, message.chat.id)

    g.justified_this_round.clear()
    g.justify_candidates.clear()
    g.vote_open = False
    g.votes.clear()
    g.silent_offenders.clear()
    g.skipvote_open = False
    g.skipvote_yes.clear()
    g.skipped_vote_in_round1 = False

    g.make_round_order()
    g.phase = Phase.ROUND_START

    await message.answer(
        "☢️ СИРЕНИ. ПАНІКА. ПОПІЛ НА НЕБІ.\n\n"
        f"Катаклізм: {g.catastrophe}\n\n"
        f"{g.bunker_desc}\n"
        f"👁 Місць у бункері: {g.slots} із {len(g.players)}.\n"
        "Ті, хто не потрапить — загинуть.\n\n"
        "Раунд 1.\n"
    )


@dp.message(Command("status"))
async def status(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "status", uid):
        return

    if not g.active:
        await message.answer("Зараз немає активної гри.")
        return
    await message.answer(
        f"📌 Стан гри:\n"
        f"Раунд: {g.round_no}/{MAX_ROUNDS}\n"
        f"Фаза: {g.phase}\n"
        f"Напрямок: {'за годинниковою' if g.clockwise else 'проти годинникової'}\n"
        f"Живі: {len(g.alive_ids())} | Місць: {g.slots}\n"
        f"Потрібно вигнати в цьому раунді: {g.pending_elims_this_round}\n\n"
        f"👥 Живі:\n{g.roster_text(only_alive=True)}"
    )


@dp.message(Command("end"))
async def end(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "end", uid):
        return

    cancel_all_tasks(g)
    g.__dict__.update(Game().__dict__)
    await message.answer("🏁 Гру завершено.")

@dp.message(Command("next"))
async def next_phase(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "next", uid):
        return

    u = message.from_user
    if not g.active:
        await message.answer("Гра не стартувала.")
        return
    if not is_host(g, u.id if u else None):
        await message.answer("Тільки хост може запускати")
        return

    cancel_all_tasks(g)

    if g.need_finish():
        g.phase = Phase.FINISH
        await message.answer(
            "🏁 ФІНАЛ.\n"
            f"Переможці:\n{g.roster_text(only_alive=True)}\n\n"
            "Гра завершена."
        )
        g.active = False
        return

    if g.phase == Phase.ROUND_START:
        g.phase = Phase.PRESENTATION
        cancel_presentation(g)
        g.presentation_task = asyncio.create_task(presentation_runner(message.chat.id))
        return

    if g.phase == Phase.PRESENTATION:
        g.phase = Phase.DISCUSSION
        await message.answer(
            "💬 Етап 2: КОЛЕКТИВНЕ ОБГОВОРЕННЯ.\n"
            "⏳ У вас є 1 хвилина.\n\n"
        )
        cancel_timer(g)
        g.timer_task = asyncio.create_task(discussion_timer(message.chat.id))
        return

    if g.phase == Phase.DISCUSSION:
        g.phase = Phase.SPEECHES
        cancel_speeches(g)
        g.speeches_task = asyncio.create_task(speeches_runner(message.chat.id))
        return

    if g.phase == Phase.SPEECHES:
        await message.answer("Бот сам відкриє голосування після виступів")
        return

    if g.phase == Phase.VOTE:
        await message.answer("Голосування вже відкрите. Закрий: /closevote")
        return

    await message.answer("Немає наступного етапу. Використай /status")

@dp.message(Command("vote"))
async def vote(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "vote", uid):
        return

    u = message.from_user
    if not u:
        return
    if not g.active or not g.vote_open:
        await message.answer("Зараз немає відкритого голосування.")
        return
    if u.id not in g.players or not g.players[u.id].alive:
        await message.answer("Голосують лише живі гравці.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Формат: /vote <номер>")
        return

    try:
        idx = int(parts[1])
    except ValueError:
        await message.answer("Номер має бути числом. Приклад: /vote 3")
        return

    alive_ids = g.alive_list_index()
    if idx < 1 or idx > len(alive_ids):
        await message.answer("Невірний номер.")
        return

    target_id = alive_ids[idx - 1]
    if target_id == u.id:
        await message.answer("Сам себе? Ні 😈")
        return

    g.votes[u.id] = target_id
    await message.answer("✅ Голос прийнято.")


@dp.message(Command("skipvote"))
async def skipvote(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "skipvote", uid):
        return

    u = message.from_user
    if not u:
        return
    if not g.active or not g.vote_open:
        await message.answer("Пропуск можна пропонувати тільки під час відкритого голосування.")
        return
    if g.round_no != 1:
        await message.answer("Пропуск голосування дозволений тільки в 1 раунді.")
        return

    g.skipvote_open = True
    g.skipvote_yes.clear()
    await message.answer(
        "⏭ Пропуск голосування (лише 1 раунд).\n"
        "Щоб підтримати пропуск — /skip\n"
        "Потрібна більшість живих."
    )


@dp.message(Command("skip"))
async def skip(message: Message):
    g = get_game(message.chat.id)
    uid = message.from_user.id if message.from_user else None
    if blocked_by_pause(g, "skip", uid):
        return

    u = message.from_user
    if not u:
        return
    if not g.active or not g.vote_open or not g.skipvote_open:
        await message.answer("Зараз немає активного голосування за пропуск.")
        return
    if u.id not in g.players or not g.players[u.id].alive:
        await message.answer("Лише живі можуть голосувати за пропуск.")
        return

    g.skipvote_yes.add(u.id)
    alive_count = len(g.alive_ids())
    need = (alive_count // 2) + 1
    await message.answer(f"✅ За пропуск: {len(g.skipvote_yes)}/{need}")

    if len(g.skipvote_yes) >= need:
        g.vote_open = False
        g.skipvote_open = False
        g.skipped_vote_in_round1 = True

        await message.answer(
            "⏭ Більшість вирішила НЕ голосувати у 1 раунді.\n"
            "Переходимо до наступного раунду.\n"
            "⚠️ У 2 раунді голосування буде проведено ДВІЧІ, щоб вигнати 2 гравців."
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())




    
         

















