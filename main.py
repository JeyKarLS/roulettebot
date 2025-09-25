import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import sqlite3
import random
import os

ADMINS = [858127740, 891023107]

PRIZES = [
    {"name": "Совет дня", "weight": 0.90, "action": None, "image_path": "media/pictures/советдня.jpg", "caption": "💡Совет дня\nсегодня отличный день для креатива — попробуй что-то новое", "url": None, "requires_email": False},
    {"name": "Атмосферные обои на телефон", "weight": 0.80, "action": None, "image_path": "media/pictures/атмосферные обои.jpg", "caption": "атмосферные обои на телефон", "url": "https://drive.google.com/drive/folders/1UBqX7121hr5ZYop2kFshcXWa3Go6BcNj", "requires_email": False},
    {"name": "Набор идей выходного дня", "weight": 0.70, "action": None, "image_path": "media/pictures/набор идей.jpg", "caption": None, "url": "https://drive.google.com/drive/folders/1ww0nxkWFyS9jDUHktjO4nQMADLbxDLoR", "requires_email": False},
    {"name": "Канал с музыкой без АП", "weight": 0.70, "action": None, "image_path": "media/pictures/канал с музыкой.jpg", "caption": None, "url": "https://t.me/music_for_video", "requires_email": False},
    {"name": "Гайд по мобильной съемке", "weight": 0.70, "action": None, "image_path": "media/pictures/гайд по мобильной сьёмке.jpg", "caption": None, "url": "https://drive.google.com/drive/folders/1YJ3EI7qL2s_5drVKRsI_f-R4ocZWt_Zx", "requires_email": False},
    {"name": "Гайд по осенней эстетике", "weight": 0.60, "action": None, "image_path": "media/pictures/гайд по осенней эстетике.jpg", "caption": None, "url": "https://drive.google.com/drive/folders/1SYIqBAH5kuVR6NuwqWgSWcJu2ODecreM", "requires_email": False},
    {"name": "Карта HomePass 30% на события от PULSE", "weight": 0.40, "action": None, "image_path": "media/pictures/карт HomePas30.jpg", "caption": "💳 30% скидки на все события от PULSE до 31.12.2025", "url": None, "requires_email": True},
    {"name": "Сертификат Литрес на 300 рублей", "weight": 0.20, "action": None, "image_path": "media/pictures/Литресс.jpg", "caption": "💳 Сертификат Литрес на 300 руб (аудио книги)", "url": None, "requires_email": True},
    {"name": "Разбор вашей страницы в любой соц.сети", "weight": 0.20, "action": None, "image_path": "media/pictures/разбор страницы.jpg", "caption": "👥 Полный аудит твоей страницы от контента, подачи до стратегии и идей в формате голосовых/файла", "url": "https://t.me/solnikos", "requires_email": False},
    {"name": "Сертификат Лэтуаль на 500 рублей", "weight": 0.10, "action": None, "image_path": "media/pictures/сертификат летуаль.jpg", "caption": "💳 Сертификат Лэтуаль на 500 рублей", "url": None, "requires_email": True},
    {"name": "Бизнес - завтрак", "weight": 0.10, "action": None, "image_path": "media/pictures/бизнес завтрак.jpg", "caption": "☕️ 2-х часовый формат work - life в атмосферной локации", "spoiler": "Можно задать любые вопросы в профессиональной деятельности и не только", "url": "https://t.me/solnikos", "requires_email": False},
    {"name": "Бонусное вращение", "weight": 0.05, "action": "spin", "image_path": "media/pictures/бонусное вращение.jpg", "caption": "🎰 Тебе выпало +1 вращение", "url": None, "requires_email": False}
]

# PRIZES defined later after database setup

API_TOKEN = os.environ.get('API_TOKEN')
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable is required")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class PrizeStates(StatesGroup):
    waiting_for_email = State()

class AdminStates(StatesGroup):
    waiting_for_give_spins = State()
    waiting_for_broadcast = State()
    waiting_for_search_user = State()
    waiting_for_add_prize = State()
    waiting_for_edit_prize = State()

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        spins_count INTEGER DEFAULT 0,
        referred_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        username TEXT,
        wins_money INTEGER DEFAULT 0,
        wins_spin INTEGER DEFAULT 0,
        wins_rare INTEGER DEFAULT 0,
        wins_bonus INTEGER DEFAULT 0,
        wins_empty INTEGER DEFAULT 0,
        menu_message_id INTEGER
    )
''')
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]
for col in ['username', 'wins_money', 'wins_spin', 'wins_rare', 'wins_bonus', 'wins_empty', 'menu_message_id']:
    if col not in columns:
        if col in ['wins_money', 'wins_spin', 'wins_rare', 'wins_bonus', 'wins_empty', 'menu_message_id']:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
        else:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS promos (
        code TEXT PRIMARY KEY,
        spins INTEGER
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS prize_requests (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        prize_text TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS wins_log (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        prize_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS prizes (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        weight REAL,
        action TEXT,
        image_path TEXT,
        caption TEXT,
        url TEXT,
        requires_email INTEGER
    )
''')
# Insert default prizes if table is empty
cursor.execute("SELECT COUNT(*) FROM prizes")
if cursor.fetchone()[0] == 0:
    for prize in PRIZES:
        cursor.execute('''
            INSERT INTO prizes (name, weight, action, image_path, caption, url, requires_email)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            prize['name'],
            prize['weight'],
            prize.get('action'),
            prize.get('image_path'),
            prize.get('caption'),
            prize.get('url'),
            1 if prize.get('requires_email') else 0
        ))
conn.commit()

def load_prizes():
    cursor.execute("SELECT name, weight, action, image_path, caption, url, requires_email FROM prizes ORDER BY weight DESC")
    rows = cursor.fetchall()
    prizes = []
    for row in rows:
        name, weight, action, image_path, caption, url, requires_email = row
        prize = {
            "name": name,
            "weight": weight,
            "action": action,
            "image_path": image_path,
            "caption": caption,
            "url": url,
            "requires_email": bool(requires_email)
        }
        prizes.append(prize)
    # Add spoiler for specific prize if not in DB
    for prize in prizes:
        if prize["name"] == "Бизнес - завтрак":
            prize["spoiler"] = "Можно задать любые вопросы в профессиональной деятельности и не только"
    return prizes

PRIZES = load_prizes()

async def get_referral_link(user_id):
    bot_info = await bot.get_me()
    return f"https://t.me/{bot_info.username}?start={user_id}"

def get_main_keyboard(is_admin: bool = False, is_wheel_available: bool = False) -> types.InlineKeyboardMarkup:
    # Порядок:
    # Админ панель (если админ), Профиль, Статистика, Пригласить друзей, Посмотреть все призы, Крутить колесо (если доступно)
    rows = []
    if is_admin:
        rows.append([types.InlineKeyboardButton(text="🔧 Админ панель", callback_data="admin_panel")])
    rows.extend([
        [types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="user_stats")],
        [types.InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="invite_friends")],
        [types.InlineKeyboardButton(text="⬆️ Посмотреть все призы", callback_data="view_prizes")],
    ])
    if is_wheel_available:
        rows.append([types.InlineKeyboardButton(text="🎰 КРУТИТЬ КОЛЕСО ФОРТУНЫ", callback_data="spin_wheel")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=rows)
    return keyboard

async def send_prizes_overview(chat: types.Message | types.CallbackQuery):
    is_admin = (isinstance(chat, types.CallbackQuery) and (chat.from_user.id in ADMINS)) or (isinstance(chat, types.Message) and (chat.from_user.id in ADMINS))
    # Формируем список призов как в примере
    prize_lines = [
        "Список возможных призов:",
        "",
        "1. Совет дня",
        "2. Атмосферные обои на телефон",
        "3. Набор идей выходного дня",
        "4. Канал с музыкой без АП",
        "5. Гайд по мобильной съемке",
        "6. Гайд по осенней эстетике",
        "7. Карта HomePass 30% на события от PULSE",
        "8. Сертификат Литрес на 300 рублей",
        "9. Разбор вашей страницы в любой соц.сети",
        "10. Сертификат Лэтуаль на 500 рублей",
        "11. Бизнес - завтрак",
        "12. Бонусное вращение",
        ""
    ]
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/pulse_lip")],
        [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub_start")]
    ])
    photo = FSInputFile("media/pictures/список призов.jpg")
    text = "Твой приз… Выбирается случайно по вероятностям. Жми, чтобы попытать удачу!\n\n" + "\n".join(prize_lines)
    user_id = chat.from_user.id if isinstance(chat, types.CallbackQuery) else chat.from_user.id
    cursor.execute("SELECT menu_message_id FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    menu_id = row[0] if row else None

    if isinstance(chat, types.CallbackQuery):
        if menu_id:
            try:
                await bot.edit_message_media(chat_id=chat.message.chat.id, message_id=menu_id, media=InputMediaPhoto(media=photo, caption=text), reply_markup=kb)
            except:
                msg = await chat.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
                cursor.execute("UPDATE users SET menu_message_id=? WHERE user_id=?", (msg.message_id, user_id))
                conn.commit()
        else:
            msg = await chat.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
            cursor.execute("UPDATE users SET menu_message_id=? WHERE user_id=?", (msg.message_id, user_id))
            conn.commit()
    else:
        if menu_id:
            try:
                await bot.edit_message_media(chat_id=chat.chat.id, message_id=menu_id, media=InputMediaPhoto(media=photo, caption=text), reply_markup=kb)
            except:
                msg = await chat.answer_photo(photo=photo, caption=text, reply_markup=kb)
                cursor.execute("UPDATE users SET menu_message_id=? WHERE user_id=?", (msg.message_id, user_id))
                conn.commit()
        else:
            msg = await chat.answer_photo(photo=photo, caption=text, reply_markup=kb)
            cursor.execute("UPDATE users SET menu_message_id=? WHERE user_id=?", (msg.message_id, user_id))
            conn.commit()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: Command):
    user_id = message.from_user.id
    referral_id = command.args if command.args else None

    is_new = False
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        is_new = True
        cursor.execute("INSERT INTO users (user_id, spins_count, referred_by, username) VALUES (?, 0, ?, ?)", (user_id, int(referral_id) if referral_id and referral_id.isdigit() else None, message.from_user.username))
        conn.commit()
        # Уведомление админам
        for admin in ADMINS:
            try:
                await bot.send_message(admin, f"🆕 Новый пользователь: @{message.from_user.username or 'Нет'} ID: {user_id}")
            except:
                pass

    # Скрыть возможную обычную (reply) клавиатуру
    try:
        rm_msg = await message.answer("⏳", reply_markup=types.ReplyKeyboardRemove())
        try:
            await rm_msg.delete()
        except:
            pass
    except:
        pass

    main_keyboard = get_main_keyboard(user_id in ADMINS)
    if is_new and referral_id:
        # Special welcome for referred users
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Перейти в канал", url="https://t.me/pulse_lip")],
            [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub_start")]
        ])
        await message.answer("🎉 Добро пожаловать в Колесо Фортуны!\n\nПодпишись на наш канал, чтобы получить бонусные вращения и начать игру!", reply_markup=kb)
    else:
        welcome_kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬆️ Посмотреть все призы", callback_data="view_prizes")]])
        await message.answer_photo(
            photo=FSInputFile("media/welcome/ПриветствиеКФ.jpg"),
            caption="Добро пожаловать в Колесо Фортуны!\n\n🎰 Подпишись на канал, чтобы получить бонусные вращения и начать игру.\n\nДелись ссылкой с друзьями — получай +1 вращение за каждого!",
            reply_markup=welcome_kb
        )
        # Откроется по кнопке "Посмотреть все призы"

@dp.callback_query(F.data == "spin_wheel")
async def spin_wheel_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    # Check subscription
    try:
        member = await bot.get_chat_member(chat_id="@pulse_lip", user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/pulse_lip")],
                [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub_start")]
            ])
            await callback.message.edit_text("Ты не подписан на канал. Подпишись и проверь подписку.", reply_markup=kb)
            return
    except:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/pulse_lip")],
            [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub_start")]
        ])
        await callback.message.edit_text("Ошибка проверки подписки. Попробуй снова.", reply_markup=kb)
        return

    cursor.execute("SELECT spins_count FROM users WHERE user_id=?", (user_id,))
    spins = cursor.fetchone()[0]

    if spins <= 0 and user_id not in ADMINS:
        referral_link = await get_referral_link(user_id)
        photo = FSInputFile("media/pictures/недостаточно шансов.jpg")
        text = (
            "Недостаточно «шансов»\n\n"
            "Приглашай друзей и за каждого друга дадим «шансов».\n\n"
            "Отправляй свою ссылку друзьям:\n"
            f"{referral_link}\n\n"
            "Как только твои друзья подпишутся тебе придет уведомления и ты получишь «шансов»"
        )
        kb = get_main_keyboard(callback.from_user.id in ADMINS, True)
        # Показать экран в основном сообщении
        cursor.execute("SELECT menu_message_id FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        menu_id = row[0] if row else None
        try:
            if menu_id:
                await bot.edit_message_media(chat_id=callback.message.chat.id, message_id=menu_id, media=InputMediaPhoto(media=photo, caption=text), reply_markup=kb)
            else:
                msg = await callback.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
                cursor.execute("UPDATE users SET menu_message_id=? WHERE user_id=?", (msg.message_id, user_id))
                conn.commit()
        except:
            pass
        return

    if user_id not in ADMINS:
        cursor.execute("UPDATE users SET spins_count = spins_count - 1 WHERE user_id=?", (user_id,))
        conn.commit()

    animation = FSInputFile('media/wheel.gif')
    anim_msg = await callback.message.answer_animation(animation)

    await asyncio.sleep(3)

    await anim_msg.delete()

    weights = [p["weight"] for p in PRIZES]
    selected_prize = random.choices(PRIZES, weights=weights, k=1)[0]
    prize_name = selected_prize["name"]
    await callback.message.answer(f"🎡 Твой приз: {prize_name}")

    # Логирование выигрыша (для просмотра в админке)
    try:
        cursor.execute("INSERT INTO wins_log (user_id, prize_name) VALUES (?, ?)", (user_id, prize_name))
        conn.commit()
    except:
        pass

    if selected_prize.get("action") == "spin":
        cursor.execute("UPDATE users SET spins_count = spins_count + 1 WHERE user_id=?", (user_id,))
        conn.commit()
        await callback.message.answer("🎉 Поздравляем! Ты получил дополнительное вращение!")

    kb_rows = []
    if selected_prize.get("url"):
        kb_rows.append([types.InlineKeyboardButton(text="Забрать подарок", url=selected_prize["url"])])
    if selected_prize.get("requires_email"):
        kb_rows.append([types.InlineKeyboardButton(text="Укажи email", callback_data="enter_email")])
        # Создать заявку сразу, чтобы она отобразилась в админке
        try:
            cursor.execute("INSERT INTO prize_requests (user_id, prize_text) VALUES (?, ?)", (user_id, prize_name))
            conn.commit()
        except:
            pass
    # Add action buttons
    if callback.from_user.id in ADMINS:
        kb_rows.insert(0, [types.InlineKeyboardButton(text="🔧 Админ панель", callback_data="admin_panel")])
    kb_rows.extend([
        [types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [types.InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="invite_friends")],
        [types.InlineKeyboardButton(text="🎰 ПРОКРУТИТЬ КОЛЕСО ФОРТУНЫ", callback_data="spin_wheel")]
    ])
    kb = types.InlineKeyboardMarkup(inline_keyboard=kb_rows)

    caption_text = selected_prize.get("caption") or prize_name
    # Без HTML-спойлера — простым текстом, чтобы избежать ошибок парсера
    if selected_prize.get("spoiler"):
        caption_text = f"{caption_text}\n\n{selected_prize['spoiler']}"

    if selected_prize.get("image_path"):
        try:
            prize_image = FSInputFile(selected_prize["image_path"])
            await callback.message.answer_photo(photo=prize_image, caption=caption_text, reply_markup=kb)
        except Exception:
            await callback.message.answer(caption_text, reply_markup=kb)
    else:
        await callback.message.answer(caption_text, reply_markup=kb)

    if selected_prize.get("action") == "spin":
        cursor.execute("UPDATE users SET wins_spin = wins_spin + 1 WHERE user_id=?", (user_id,))
    else:
        cursor.execute("UPDATE users SET wins_bonus = wins_bonus + 1 WHERE user_id=?", (user_id,))
        conn.commit()

@dp.callback_query(F.data == "view_prizes")
async def view_prizes(callback: types.CallbackQuery):
    await send_prizes_overview(callback)

@dp.callback_query(F.data == "check_sub_start")
async def check_sub_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(chat_id="@pulse_lip", user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            cursor.execute("UPDATE users SET spins_count = spins_count + 1 WHERE user_id=?", (user_id,))
            conn.commit()
            # Give spin to referrer if exists
            cursor.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                referrer_id = row[0]
                cursor.execute("UPDATE users SET spins_count = spins_count + 1 WHERE user_id=?", (referrer_id,))
                conn.commit()
                try:
                    await bot.send_message(referrer_id, "✅ Твой друг проверил подписку на канал! Ты получил +1 шанс.")
                except:
                    pass
            kb = get_main_keyboard(callback.from_user.id in ADMINS, True)
            if callback.message.photo:
                await callback.message.edit_caption("✅ Подписка подтверждена! Ты получил 1 бонусное вращение!\n\n🎰 Теперь можешь пользоваться ботом!", reply_markup=kb)
            else:
                await callback.message.edit_text("✅ Подписка подтверждена! Ты получил 1 бонусное вращение!\n\n🎰 Теперь можешь пользоваться ботом!", reply_markup=kb)
        else:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/pulse_lip")],
                [types.InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub_start")]
            ])
            if callback.message.photo:
                await callback.message.edit_caption("❌ Ты не подписан на канал. Подпишись и проверь подписку снова.", reply_markup=kb)
            else:
                await callback.message.edit_text("❌ Ты не подписан на канал. Подпишись и проверь подписку снова.", reply_markup=kb)
    except:
        await callback.answer("❌ Ошибка проверки.")



@dp.callback_query(F.data == "invite_friends")
async def invite_friends_callback(callback: types.CallbackQuery):
    referral_link = await get_referral_link(callback.from_user.id)
    channel_link = "https://t.me/pulse_lip"
    await callback.message.answer(f"🔗 Пригласи друзей: сначала подпишись на канал {channel_link}, затем запусти бота по ссылке {referral_link}\n\n💡 После того как приглашённый проверит подписку в боте, ты получишь +1 вращение!")

@dp.callback_query(F.data == "enter_email")
async def enter_email(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✉️ Введи, пожалуйста, свой email для получения приза.")
    await state.set_state(PrizeStates.waiting_for_email)

@dp.callback_query(F.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "Нет"
    cursor.execute("SELECT spins_count, referred_by, created_at, wins_money, wins_spin, wins_rare, wins_bonus, wins_empty FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    if data:
        spins, referred_by, created_at, wins_money, wins_spin, wins_rare, wins_bonus, wins_empty = data
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,))
        invited = cursor.fetchone()[0]
        if referred_by:
            cursor.execute("SELECT username FROM users WHERE user_id=?", (referred_by,))
            referrer_row = cursor.fetchone()
            referred_name = f"@{referrer_row[0]}" if referrer_row and referrer_row[0] else f"ID: {referred_by}"
        else:
            referred_name = "Никто"
        await callback.message.answer(f"👤 Твой профиль:\n\n🆔 ID: `{user_id}`\n👤 Username: @{username}\n🎰 Вращений: {spins}\n👥 Приглашенных друзей: {invited}\n👨‍👩‍👧‍👦 Приглашен тобой: {referred_name}\n📅 Дата регистрации: {created_at}\n\n🏆 Статистика побед:\n🤑 Деньги: {wins_money} | 🔄 Спин: {wins_spin} | 💎 Редкие: {wins_rare} | 🎉 Бонусы: {wins_bonus} | 😔 Пусто: {wins_empty}\n\n⭐ Продолжай приглашать друзей и крутить колесо!")
    else:
        await callback.message.answer("❌ Профиль не найден.")

@dp.callback_query(F.data == "user_stats")
async def user_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT spins_count, wins_money, wins_spin, wins_rare, wins_bonus, wins_empty FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()
    if data:
        spins, wins_money, wins_spin, wins_rare, wins_bonus, wins_empty = data
        total_wins = wins_money + wins_spin + wins_rare + wins_bonus + wins_empty
        text = f"📊 **Ваша статистика:**\n\n🎰 Вращений: {spins}\n🏆 Всего побед: {total_wins}\n\nПодробно:\n🤑 Деньги: {wins_money}\n🔄 Спин: {wins_spin}\n💎 Редкие: {wins_rare}\n🎉 Бонусы: {wins_bonus}\n😔 Пусто: {wins_empty}"
    else:
        text = "❌ Статистика не найдена."
    await callback.message.answer(text)

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещен!")
        return

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🏆 Призы", callback_data="admin_prizes")],
            [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [types.InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")],
            [types.InlineKeyboardButton(text="📈 Статистика призов", callback_data="admin_prize_stats")],
            [types.InlineKeyboardButton(text="🔍 Поиск пользователей", callback_data="admin_search_user")],
            [types.InlineKeyboardButton(text="🎁 Управление призами", callback_data="admin_manage_prizes")],
            [types.InlineKeyboardButton(text="🎁 Выдать спины", callback_data="admin_give_spins")],
            [types.InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [types.InlineKeyboardButton(text="🏆 Топ пользователей", callback_data="admin_top")]
        ]
    )
    await callback.message.answer("🔧 **Админ панель:**\n\nВыберите действие:", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_give_spins")
async def admin_give_spins(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещен!")
        return
    await callback.message.answer("🎁 Введите ID пользователя и количество спинов через пробел.\n\nПример: 123456789 5")
    await state.set_state(AdminStates.waiting_for_give_spins)

@dp.callback_query(F.data == "admin_search_user")
async def admin_search_user(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещен!")
        return
    await callback.message.answer("🔍 Введите username или ID пользователя для поиска.\n\nПример: @username или 123456789")
    await state.set_state(AdminStates.waiting_for_search_user)

@dp.message(AdminStates.waiting_for_search_user)
async def process_search_user(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    search = message.text.strip()
    if search.startswith('@'):
        # Search by username
        cursor.execute("SELECT user_id, referred_by, spins_count, created_at, username FROM users WHERE username = ?", (search[1:],))
    else:
        # Search by ID
        try:
            user_id = int(search)
            cursor.execute("SELECT user_id, referred_by, spins_count, created_at, username FROM users WHERE user_id = ?", (user_id,))
        except:
            await message.answer("❌ Неверный формат. Введите @username или ID.")
            return
    row = cursor.fetchone()
    if row:
        user_id, referred_by, spins, created, username = row
        user_display = f"@{username}" if username else f"`{user_id}`"
        if referred_by:
            cursor.execute("SELECT username FROM users WHERE user_id=?", (referred_by,))
            referrer_row = cursor.fetchone()
            referrer_display = f"@{referrer_row[0]}" if referrer_row and referrer_row[0] else f"`{referred_by}`"
        else:
            referrer_display = "Новый пользователь"
        invited_count = cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,)).fetchone()[0]
        text = f"👤 **Найден пользователь:**\n\n🆔 {user_display} | Приглашен: {referrer_display} | Приглашенных: {invited_count} | Вращений: {spins} | Дата: {created}"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ])
        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await message.answer("❌ Пользователь не найден.")
    await state.clear()
@dp.message(AdminStates.waiting_for_give_spins)
async def process_give_spins(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    try:
        user_id, count = message.text.split()
        user_id = int(user_id)
        count = int(count)
        cursor.execute("UPDATE users SET spins_count = spins_count + ? WHERE user_id=?", (count, user_id))
        conn.commit()
        await message.answer(f"✅ Выдано {count} вращений пользователю {user_id}")
        # Вернуться к админ панели
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🏆 Призы", callback_data="admin_prizes")],
                [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
                [types.InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")],
                [types.InlineKeyboardButton(text="📈 Статистика призов", callback_data="admin_prize_stats")],
                [types.InlineKeyboardButton(text="🔍 Поиск пользователей", callback_data="admin_search_user")],
                [types.InlineKeyboardButton(text="🎁 Управление призами", callback_data="admin_manage_prizes")],
                [types.InlineKeyboardButton(text="🎁 Выдать спины", callback_data="admin_give_spins")],
                [types.InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
                [types.InlineKeyboardButton(text="🏆 Топ пользователей", callback_data="admin_top")]
            ]
        )
        await message.answer("🔧 **Админ панель:**\n\nВыберите действие:", reply_markup=keyboard)
    except:
        await message.answer("❌ Неверный формат. Используйте: ID количество\n\nПример: 123456789 5")
    await state.clear()
@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещен!")
        return
    await callback.message.answer("📢 Введите текст рассылки.")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    text = message.text
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid[0], text)
            sent += 1
        except:
            pass
    await message.answer(f"✅ Рассылка отправлена {sent} пользователям")
    await state.clear()

@dp.callback_query(F.data == "admin_manage_prizes")
async def admin_manage_prizes(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ Доступ запрещен!")
        return
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить приз", callback_data="admin_add_prize")],
            [types.InlineKeyboardButton(text="✏️ Редактировать приз", callback_data="admin_edit_prize")],
            [types.InlineKeyboardButton(text="🗑️ Удалить приз", callback_data="admin_delete_prize")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
        ]
    )
    await callback.message.answer("🎁 **Управление призами:**\n\nВыберите действие:", reply_markup=keyboard)
@dp.callback_query(F.data == "admin_prize_stats")
async def admin_prize_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    cursor.execute("SELECT prize_name, COUNT(*) as count FROM wins_log GROUP BY prize_name ORDER BY count DESC")
    stats = cursor.fetchall()
    text = "📈 **Статистика призов:**\n\n"
    if stats:
        for prize, count in stats:
            text += f"{prize}: {count} раз(а)\n"
    else:
        text += "Пока нет данных."
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]])
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    cursor.execute("SELECT user_id, referred_by, spins_count, created_at, username FROM users ORDER BY created_at DESC LIMIT 50")
    rows = cursor.fetchall()
    text = "👥 **Список пользователей (последние 50):**\n\n"
    for user_id, referred_by, spins, created, username in rows:
        user_display = f"@{username}" if username else f"`{user_id}`"
        if referred_by:
            cursor.execute("SELECT username FROM users WHERE user_id=?", (referred_by,))
            referrer_row = cursor.fetchone()
            referrer_display = f"@{referrer_row[0]}" if referrer_row and referrer_row[0] else f"`{referred_by}`"
        else:
            referrer_display = "Новый пользователь"
        invited_count = cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,)).fetchone()[0]
        text += f"🆔 {user_display} | Приглашен: {referrer_display} | Приглашенных: {invited_count} | Вращений: {spins} | Дата: {created}\n"
    if not rows:
        text += "Нет пользователей."
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]])
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(spins_count) FROM users")
    total_spins = cursor.fetchone()[0] or 0
    text = f"📊 **Статистика бота:**\n\n👥 Пользователей: {total_users}\n🎰 Всего вращений: {total_spins}"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]])
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_top")
async def admin_top(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    # Топ по приглашениям
    cursor.execute("SELECT user_id, username, COUNT(referred_by) as invited FROM users LEFT JOIN users u2 ON users.user_id = u2.referred_by GROUP BY user_id ORDER BY invited DESC LIMIT 10")
    top_invited = cursor.fetchall()
    text = "🏆 **Топ по приглашениям:**\n\n"
    for i, (uid, uname, inv) in enumerate(top_invited, 1):
        display = f"@{uname}" if uname else f"`{uid}`"
        text += f"{i}. {display} - {inv} приглашений\n"
    # Топ по вращениям
    cursor.execute("SELECT user_id, username, spins_count FROM users ORDER BY spins_count DESC LIMIT 10")
    top_spins = cursor.fetchall()
    text += "\n🏆 **Топ по вращениям:**\n\n"
    for i, (uid, uname, spins) in enumerate(top_spins, 1):
        display = f"@{uname}" if uname else f"`{uid}`"
        text += f"{i}. {display} - {spins} вращений\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]])
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_prizes")
async def admin_prizes(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("Нет доступа")
        return
    # Последние выигрыши
    cursor.execute("SELECT w.user_id, u.username, w.prize_name, w.created_at FROM wins_log w LEFT JOIN users u ON w.user_id = u.user_id ORDER BY w.created_at DESC LIMIT 30")
    wins = cursor.fetchall()
    text = "🏆 **Последние выигрыши:**\n\n"
    if wins:
        for uid, uname, prize, created in wins:
            display = f"@{uname}" if uname else f"`{uid}`"
            text += f"{display} — {prize} — {created}\n"
    else:
        text += "Пока пусто.\n"

    # Запросы на призы (email)
    cursor.execute("SELECT user_id, prize_text, email, created_at FROM prize_requests ORDER BY created_at DESC LIMIT 30")
    rows = cursor.fetchall()
    text += "\n📨 **Запросы на призы (email):**\n\n"
    if rows:
        for uid, prize, email, created in rows:
            cursor.execute("SELECT username FROM users WHERE user_id=?", (uid,))
            uname = cursor.fetchone()
            user_display = f"@{uname[0]}" if uname and uname[0] else f"`{uid}`"
            email_str = email if email else "Не указан"
            text += f"{user_display} — {prize} — Email: {email_str} — {created}\n"
    else:
        text += "Пока нет запросов."
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]])
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.message(PrizeStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text
    user_id = message.from_user.id
    cursor.execute("UPDATE prize_requests SET email=? WHERE user_id=? AND email IS NULL ORDER BY id DESC LIMIT 1", (email, user_id))
    conn.commit()
    await message.answer("✅ Email сохранен! Админ свяжется с вами для отправки приза.")
    # Вернуть пользователя к главному меню (картинка + кнопки)
    try:
        await send_prizes_overview(message)
    except Exception:
        pass
    await state.clear()

@dp.message(Command("give_spins"))
async def give_spins(message: types.Message, command: Command):
    if message.from_user.id not in ADMINS:
        return
    try:
        user_id, count = command.args.split()
        user_id = int(user_id)
        count = int(count)
        cursor.execute("UPDATE users SET spins_count = spins_count + ? WHERE user_id=?", (count, user_id))
        conn.commit()
        await message.answer(f"✅ Выдано {count} вращений пользователю {user_id}")
    except:
        await message.answer("❌ Использование: /give_spins <user_id> <count>")

@dp.message(Command("create_promo"))
async def create_promo(message: types.Message, command: Command):
    if message.from_user.id not in ADMINS:
        return
    try:
        code, spins = command.args.split()
        spins = int(spins)
        cursor.execute("INSERT INTO promos (code, spins) VALUES (?, ?)", (code, spins))
        conn.commit()
        await message.answer(f"✅ Промокод {code} создан, дает {spins} вращений")
    except:
        await message.answer("❌ Использование: /create_promo <code> <spins>")

@dp.message(Command("promo"))
async def use_promo(message: types.Message, command: Command):
    user_id = message.from_user.id
    try:
        code = command.args[0]
        cursor.execute("SELECT spins FROM promos WHERE code=?", (code,))
        row = cursor.fetchone()
        if row:
            spins = row[0]
            cursor.execute("UPDATE users SET spins_count = spins_count + ? WHERE user_id=?", (spins, user_id))
            cursor.execute("DELETE FROM promos WHERE code=?", (code,))
            conn.commit()
            await message.answer(f"✅ Промокод активирован! Ты получил {spins} вращений")
        else:
            await message.answer("❌ Промокод не найден или уже использован")
    except:
        await message.answer("❌ Использование: /promo <code>")

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message, command: Command):
    if message.from_user.id not in ADMINS:
        return
    text = ' '.join(command.args)
    if not text:
        await message.answer("❌ Укажи текст")
        return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid[0], text)
            sent += 1
        except:
            pass
    await message.answer(f"✅ Рассылка отправлена {sent} пользователям")

async def main():
    print("Бот запущен!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())