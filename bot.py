from datetime import datetime, time
from zoneinfo import ZoneInfo
import os
import requests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]

DEFAULT_CITY = {
    "name": "Ташкент",
    "lat": 41.2646,
    "lon": 69.2163,
    "timezone": "Asia/Tashkent",
}

CHAT_SETTINGS = {}


def get_chat_city(chat_id: int) -> dict:
    if chat_id not in CHAT_SETTINGS:
        CHAT_SETTINGS[chat_id] = DEFAULT_CITY.copy()
    return CHAT_SETTINGS[chat_id]


def set_chat_city(chat_id: int, city_name: str, lat: float, lon: float, timezone: str = "auto"):
    CHAT_SETTINGS[chat_id] = {
        "name": city_name,
        "lat": lat,
        "lon": lon,
        "timezone": timezone,
    }


def get_time_of_day_emoji(timezone_name: str) -> str:
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except Exception:
        now = datetime.now()

    hour = now.hour

    if 5 <= hour < 12:
        return "🌅"
    if 12 <= hour < 18:
        return "☀️"
    if 18 <= hour < 22:
        return "🌇"
    return "🌙"


def temp_feel(temp: float) -> str:
    if temp >= 35:
        return "🥵 Очень жарко"
    if temp >= 28:
        return "🔥 Жарко"
    if temp >= 20:
        return "😊 Комфортно"
    if temp >= 10:
        return "🧥 Прохладно"
    if temp >= 0:
        return "🥶 Холодно"
    return "🧊 Очень холодно"


def weather_description(code: int) -> str:
    codes = {
        0: "☀️ Ясно",
        1: "🌤 Малооблачно",
        2: "⛅ Переменная облачность",
        3: "☁️ Пасмурно",
        45: "🌫 Туман",
        48: "🌫 Сильный туман",
        51: "🌦 Слабая морось",
        53: "🌦 Морось",
        55: "🌧 Сильная морось",
        56: "🧊 Слабая ледяная морось",
        57: "🧊 Сильная ледяная морось",
        61: "🌦 Слабый дождь",
        63: "🌧 Дождь",
        65: "🌧 Сильный дождь",
        66: "🧊 Слабый ледяной дождь",
        67: "🧊 Сильный ледяной дождь",
        71: "🌨 Слабый снег",
        73: "🌨 Снег",
        75: "❄️ Сильный снег",
        77: "❄️ Снежные зёрна",
        80: "🌦 Кратковременный слабый дождь",
        81: "🌧 Кратковременный дождь",
        82: "⛈ Сильный ливень",
        85: "🌨 Слабый снегопад",
        86: "❄️ Сильный снегопад",
        95: "⛈ Гроза",
        96: "⛈ Гроза с небольшим градом",
        99: "⛈ Гроза с сильным градом",
    }
    return codes.get(code, "🌍 Погода неизвестна")


def clothing_advice(temp: float, rain: int) -> str:
    tips = []

    if temp >= 30:
        tips.append("👕 Надень что-то лёгкое")
    elif temp >= 20:
        tips.append("🙂 Погода комфортная")
    elif temp >= 10:
        tips.append("🧥 Лучше взять кофту")
    else:
        tips.append("🧣 Одевайся теплее")

    if rain >= 50:
        tips.append("☔ Возьми зонт")
    elif rain >= 20:
        tips.append("🌂 Возможен дождь")

    return "\n".join(tips)


def get_coordinates(city_name: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "ru",
        "format": "json",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "results" not in data or not data["results"]:
        return None

    city = data["results"][0]
    return {
        "name": city.get("name", city_name),
        "lat": city["latitude"],
        "lon": city["longitude"],
        "timezone": city.get("timezone", "auto"),
        "country": city.get("country", ""),
    }


def fetch_weather_data(lat: float, lon: float, timezone_name: str = "auto") -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,weather_code,relative_humidity_2m,apparent_temperature",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
        "timezone": timezone_name,
        "forecast_days": 7,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def make_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌡 Сейчас", callback_data="now"),
                InlineKeyboardButton("📅 Сегодня", callback_data="today"),
            ],
            [
                InlineKeyboardButton("🌙 Завтра", callback_data="tomorrow"),
                InlineKeyboardButton("📆 3 дня", callback_data="three_days"),
            ],
            [
                InlineKeyboardButton("🗓 Неделя", callback_data="week"),
                InlineKeyboardButton("📍 Ташкент", callback_data="set_tashkent"),
            ],
        ]
    )


def format_now(city_name: str, timezone_name: str, data: dict) -> str:
    current_temp = data["current"]["temperature_2m"]
    feels_like = data["current"]["apparent_temperature"]
    wind = data["current"]["wind_speed_10m"]
    humidity = data["current"]["relative_humidity_2m"]
    code = data["current"]["weather_code"]

    emoji = get_time_of_day_emoji(timezone_name)
    desc = weather_description(code)

    return (
        f"{emoji} Погода в {city_name} сейчас\n\n"
        f"{desc}\n"
        f"🌡 Температура: {current_temp}°C\n"
        f"🤔 Ощущается как: {feels_like}°C\n"
        f"💧 Влажность: {humidity}%\n"
        f"💨 Ветер: {wind} км/ч\n"
        f"{temp_feel(current_temp)}"
    )


def format_today(city_name: str, timezone_name: str, data: dict) -> str:
    current_temp = data["current"]["temperature_2m"]
    feels_like = data["current"]["apparent_temperature"]
    wind = data["current"]["wind_speed_10m"]
    humidity = data["current"]["relative_humidity_2m"]
    code = data["current"]["weather_code"]

    t_min = data["daily"]["temperature_2m_min"][0]
    t_max = data["daily"]["temperature_2m_max"][0]
    rain = data["daily"]["precipitation_probability_max"][0]

    return (
        f"{get_time_of_day_emoji(timezone_name)} Погода в {city_name} на сегодня\n\n"
        f"{weather_description(code)}\n"
        f"🌡 Сейчас: {current_temp}°C\n"
        f"🤔 Ощущается как: {feels_like}°C\n"
        f"📉 Минимум: {t_min}°C\n"
        f"📈 Максимум: {t_max}°C\n"
        f"💧 Влажность: {humidity}%\n"
        f"💨 Ветер: {wind} км/ч\n"
        f"☔ Вероятность дождя: {rain}%\n\n"
        f"{temp_feel(current_temp)}\n"
        f"{clothing_advice(current_temp, rain)}"
    )


def format_tomorrow(city_name: str, data: dict) -> str:
    t_min = data["daily"]["temperature_2m_min"][1]
    t_max = data["daily"]["temperature_2m_max"][1]
    code = data["daily"]["weather_code"][1]
    rain = data["daily"]["precipitation_probability_max"][1]

    avg_temp = (t_min + t_max) / 2

    return (
        f"🌙 Погода в {city_name} на завтра\n\n"
        f"{weather_description(code)}\n"
        f"📉 Минимум: {t_min}°C\n"
        f"📈 Максимум: {t_max}°C\n"
        f"☔ Вероятность дождя: {rain}%\n\n"
        f"{temp_feel(avg_temp)}\n"
        f"{clothing_advice(avg_temp, rain)}"
    )


def format_three_days(city_name: str, data: dict) -> str:
    labels = ["Сегодня", "Завтра", "Послезавтра"]
    parts = []

    for i in range(3):
        t_min = data["daily"]["temperature_2m_min"][i]
        t_max = data["daily"]["temperature_2m_max"][i]
        code = data["daily"]["weather_code"][i]
        rain = data["daily"]["precipitation_probability_max"][i]

        parts.append(
            f"📍 {labels[i]}\n"
            f"{weather_description(code)}\n"
            f"📉 {t_min}°C | 📈 {t_max}°C\n"
            f"☔ Дождь: {rain}%"
        )

    return f"📆 Прогноз для {city_name} на 3 дня\n\n" + "\n\n".join(parts)


def format_week(city_name: str, data: dict) -> str:
    labels = ["Сегодня", "Завтра", "День 3", "День 4", "День 5", "День 6", "День 7"]
    parts = []

    for i in range(7):
        t_min = data["daily"]["temperature_2m_min"][i]
        t_max = data["daily"]["temperature_2m_max"][i]
        code = data["daily"]["weather_code"][i]
        rain = data["daily"]["precipitation_probability_max"][i]

        parts.append(
            f"📍 {labels[i]}\n"
            f"{weather_description(code)}\n"
            f"📉 {t_min}°C | 📈 {t_max}°C\n"
            f"☔ {rain}%"
        )

    return f"🗓 Прогноз для {city_name} на неделю\n\n" + "\n\n".join(parts)


def get_weather_text(mode: str, city_data: dict) -> str:
    data = fetch_weather_data(city_data["lat"], city_data["lon"], city_data["timezone"])

    if mode == "now":
        return format_now(city_data["name"], city_data["timezone"], data)
    if mode == "tomorrow":
        return format_tomorrow(city_data["name"], data)
    if mode == "three_days":
        return format_three_days(city_data["name"], data)
    if mode == "week":
        return format_week(city_data["name"], data)

    return format_today(city_data["name"], city_data["timezone"], data)


async def send_weather_reply(update: Update, mode: str):
    chat_id = update.effective_chat.id
    city_data = get_chat_city(chat_id)

    try:
        await update.message.reply_text(
            get_weather_text(mode, city_data),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await update.message.reply_text("❌ Не удалось получить погоду. Попробуй позже.")


async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    city_data = get_chat_city(chat_id)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_weather_text("today", city_data),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Не удалось получить ежедневную погоду."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    get_chat_city(chat_id)

    keyboard = [
        ["🌡 Сейчас", "📅 Сегодня"],
        ["🌙 Завтра", "📆 3 дня"],
        ["🗓 Неделя", "📍 Ташкент"],
        [KeyboardButton("📌 Отправить локацию", request_location=True)],
        ["⏰ Вкл авто-погоду", "❌ Выкл авто-погоду"],
        ["ℹ️ Помощь", "🤖 О боте"],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Я умный погодный бот 🌤\n\n"
        "Я умею:\n"
        "- показывать погоду сейчас\n"
        "- прогноз на сегодня, завтра, 3 дня и неделю\n"
        "- искать любой город\n"
        "- принимать геолокацию\n"
        "- отправлять погоду автоматически каждый день\n\n"
        "Выбери действие или просто напиши название города:",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Что умеет бот:\n\n"
        "🌡 Сейчас — текущая погода\n"
        "📅 Сегодня — прогноз на сегодня\n"
        "🌙 Завтра — прогноз на завтра\n"
        "📆 3 дня — прогноз на 3 дня\n"
        "🗓 Неделя — прогноз на неделю\n"
        "📍 Ташкент — быстро переключиться на Ташкент\n"
        "📌 Отправить локацию — погода по твоему местоположению\n"
        "⏰ Вкл авто-погоду — ежедневная отправка в 8:00\n"
        "❌ Выкл авто-погоду — отключить рассылку\n\n"
        "Также можно просто написать название любого города."
    )
    await update.message.reply_text(text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 О боте\n\n"
        "Это погодный бот, который умеет:\n"
        "- работать 24/7\n"
        "- показывать прогноз по городам\n"
        "- принимать геолокацию\n"
        "- отправлять ежедневную погоду автоматически"
    )
    await update.message.reply_text(text)


async def now_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "now")


async def today_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "today")


async def tomorrow_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "tomorrow")


async def three_days_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "three_days")


async def week_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "week")


async def set_tashkent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    set_chat_city(
        chat_id,
        DEFAULT_CITY["name"],
        DEFAULT_CITY["lat"],
        DEFAULT_CITY["lon"],
        DEFAULT_CITY["timezone"],
    )
    await update.message.reply_text("📍 Город переключен на Ташкент.")
    await send_weather_reply(update, "today")


async def enable_auto_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    old_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in old_jobs:
        job.schedule_removal()

    context.job_queue.run_daily(
        send_daily_weather,
        time=time(hour=8, minute=0, second=0),
        chat_id=chat_id,
        name=str(chat_id),
    )

    city_data = get_chat_city(chat_id)
    await update.message.reply_text(
        f"✅ Авто-погода включена.\n"
        f"Теперь каждый день в 8:00 я буду присылать погоду для города: {city_data['name']}"
    )


async def disable_auto_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if not jobs:
        await update.message.reply_text("Авто-погода у тебя не была включена.")
        return

    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("❌ Авто-погода выключена.")


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lat = update.message.location.latitude
    lon = update.message.location.longitude

    set_chat_city(chat_id, "вашего местоположения", lat, lon, "auto")
    await update.message.reply_text("📌 Локация получена. Показываю погоду для твоего местоположения.")
    await send_weather_reply(update, "today")


async def city_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, city_query: str):
    chat_id = update.effective_chat.id

    try:
        city = get_coordinates(city_query)
        if not city:
            await update.message.reply_text("❌ Город не найден. Попробуй написать название по-другому.")
            return

        city_name = city["name"]
        if city.get("country"):
            city_name = f"{city['name']}, {city['country']}"

        set_chat_city(chat_id, city_name, city["lat"], city["lon"], city["timezone"])
        await update.message.reply_text(f"🌍 Город выбран: {city_name}")
        await send_weather_reply(update, "today")
    except Exception:
        await update.message.reply_text("❌ Не удалось найти город. Попробуй позже.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    city_data = get_chat_city(chat_id)
    mode = query.data

    try:
        if mode == "set_tashkent":
            set_chat_city(
                chat_id,
                DEFAULT_CITY["name"],
                DEFAULT_CITY["lat"],
                DEFAULT_CITY["lon"],
                DEFAULT_CITY["timezone"],
            )
            city_data = get_chat_city(chat_id)
            mode = "today"

        await query.edit_message_text(
            text=get_weather_text(mode, city_data),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await query.edit_message_text("❌ Не удалось обновить погоду.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "🌡 Сейчас":
        await now_weather(update, context)
    elif text == "📅 Сегодня":
        await today_weather(update, context)
    elif text == "🌙 Завтра":
        await tomorrow_weather(update, context)
    elif text == "📆 3 дня":
        await three_days_weather(update, context)
    elif text == "🗓 Неделя":
        await week_weather(update, context)
    elif text == "📍 Ташкент":
        await set_tashkent(update, context)
    elif text == "⏰ Вкл авто-погоду":
        await enable_auto_weather(update, context)
    elif text == "❌ Выкл авто-погоду":
        await disable_auto_weather(update, context)
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🤖 О боте":
        await about_command(update, context)
    elif text:
        await city_search_handler(update, context, text)
    else:
        await update.message.reply_text("Нажми кнопку из меню 👇")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("now", now_weather))
    app.add_handler(CommandHandler("today", today_weather))
    app.add_handler(CommandHandler("tomorrow", tomorrow_weather))
    app.add_handler(CommandHandler("three_days", three_days_weather))
    app.add_handler(CommandHandler("week", week_weather))
    app.add_handler(CommandHandler("auto_on", enable_auto_weather))
    app.add_handler(CommandHandler("auto_off", disable_auto_weather))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот работает...")
    app.run_polling()


if __name__ == "__main__":
    main()from datetime import datetime, time
from zoneinfo import ZoneInfo
import os
import requests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]

DEFAULT_CITY = {
    "name": "Ташкент",
    "lat": 41.2646,
    "lon": 69.2163,
    "timezone": "Asia/Tashkent",
}

CHAT_SETTINGS = {}


def get_chat_city(chat_id: int) -> dict:
    if chat_id not in CHAT_SETTINGS:
        CHAT_SETTINGS[chat_id] = DEFAULT_CITY.copy()
    return CHAT_SETTINGS[chat_id]


def set_chat_city(chat_id: int, city_name: str, lat: float, lon: float, timezone: str = "auto"):
    CHAT_SETTINGS[chat_id] = {
        "name": city_name,
        "lat": lat,
        "lon": lon,
        "timezone": timezone,
    }


def get_time_of_day_emoji(timezone_name: str) -> str:
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except Exception:
        now = datetime.now()

    hour = now.hour

    if 5 <= hour < 12:
        return "🌅"
    if 12 <= hour < 18:
        return "☀️"
    if 18 <= hour < 22:
        return "🌇"
    return "🌙"


def temp_feel(temp: float) -> str:
    if temp >= 35:
        return "🥵 Очень жарко"
    if temp >= 28:
        return "🔥 Жарко"
    if temp >= 20:
        return "😊 Комфортно"
    if temp >= 10:
        return "🧥 Прохладно"
    if temp >= 0:
        return "🥶 Холодно"
    return "🧊 Очень холодно"


def weather_description(code: int) -> str:
    codes = {
        0: "☀️ Ясно",
        1: "🌤 Малооблачно",
        2: "⛅ Переменная облачность",
        3: "☁️ Пасмурно",
        45: "🌫 Туман",
        48: "🌫 Сильный туман",
        51: "🌦 Слабая морось",
        53: "🌦 Морось",
        55: "🌧 Сильная морось",
        56: "🧊 Слабая ледяная морось",
        57: "🧊 Сильная ледяная морось",
        61: "🌦 Слабый дождь",
        63: "🌧 Дождь",
        65: "🌧 Сильный дождь",
        66: "🧊 Слабый ледяной дождь",
        67: "🧊 Сильный ледяной дождь",
        71: "🌨 Слабый снег",
        73: "🌨 Снег",
        75: "❄️ Сильный снег",
        77: "❄️ Снежные зёрна",
        80: "🌦 Кратковременный слабый дождь",
        81: "🌧 Кратковременный дождь",
        82: "⛈ Сильный ливень",
        85: "🌨 Слабый снегопад",
        86: "❄️ Сильный снегопад",
        95: "⛈ Гроза",
        96: "⛈ Гроза с небольшим градом",
        99: "⛈ Гроза с сильным градом",
    }
    return codes.get(code, "🌍 Погода неизвестна")


def clothing_advice(temp: float, rain: int) -> str:
    tips = []

    if temp >= 30:
        tips.append("👕 Надень что-то лёгкое")
    elif temp >= 20:
        tips.append("🙂 Погода комфортная")
    elif temp >= 10:
        tips.append("🧥 Лучше взять кофту")
    else:
        tips.append("🧣 Одевайся теплее")

    if rain >= 50:
        tips.append("☔ Возьми зонт")
    elif rain >= 20:
        tips.append("🌂 Возможен дождь")

    return "\n".join(tips)


def get_coordinates(city_name: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "ru",
        "format": "json",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "results" not in data or not data["results"]:
        return None

    city = data["results"][0]
    return {
        "name": city.get("name", city_name),
        "lat": city["latitude"],
        "lon": city["longitude"],
        "timezone": city.get("timezone", "auto"),
        "country": city.get("country", ""),
    }


def fetch_weather_data(lat: float, lon: float, timezone_name: str = "auto") -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,weather_code,relative_humidity_2m,apparent_temperature",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
        "timezone": timezone_name,
        "forecast_days": 7,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def make_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🌡 Сейчас", callback_data="now"),
                InlineKeyboardButton("📅 Сегодня", callback_data="today"),
            ],
            [
                InlineKeyboardButton("🌙 Завтра", callback_data="tomorrow"),
                InlineKeyboardButton("📆 3 дня", callback_data="three_days"),
            ],
            [
                InlineKeyboardButton("🗓 Неделя", callback_data="week"),
                InlineKeyboardButton("📍 Ташкент", callback_data="set_tashkent"),
            ],
        ]
    )


def format_now(city_name: str, timezone_name: str, data: dict) -> str:
    current_temp = data["current"]["temperature_2m"]
    feels_like = data["current"]["apparent_temperature"]
    wind = data["current"]["wind_speed_10m"]
    humidity = data["current"]["relative_humidity_2m"]
    code = data["current"]["weather_code"]

    emoji = get_time_of_day_emoji(timezone_name)
    desc = weather_description(code)

    return (
        f"{emoji} Погода в {city_name} сейчас\n\n"
        f"{desc}\n"
        f"🌡 Температура: {current_temp}°C\n"
        f"🤔 Ощущается как: {feels_like}°C\n"
        f"💧 Влажность: {humidity}%\n"
        f"💨 Ветер: {wind} км/ч\n"
        f"{temp_feel(current_temp)}"
    )


def format_today(city_name: str, timezone_name: str, data: dict) -> str:
    current_temp = data["current"]["temperature_2m"]
    feels_like = data["current"]["apparent_temperature"]
    wind = data["current"]["wind_speed_10m"]
    humidity = data["current"]["relative_humidity_2m"]
    code = data["current"]["weather_code"]

    t_min = data["daily"]["temperature_2m_min"][0]
    t_max = data["daily"]["temperature_2m_max"][0]
    rain = data["daily"]["precipitation_probability_max"][0]

    return (
        f"{get_time_of_day_emoji(timezone_name)} Погода в {city_name} на сегодня\n\n"
        f"{weather_description(code)}\n"
        f"🌡 Сейчас: {current_temp}°C\n"
        f"🤔 Ощущается как: {feels_like}°C\n"
        f"📉 Минимум: {t_min}°C\n"
        f"📈 Максимум: {t_max}°C\n"
        f"💧 Влажность: {humidity}%\n"
        f"💨 Ветер: {wind} км/ч\n"
        f"☔ Вероятность дождя: {rain}%\n\n"
        f"{temp_feel(current_temp)}\n"
        f"{clothing_advice(current_temp, rain)}"
    )


def format_tomorrow(city_name: str, data: dict) -> str:
    t_min = data["daily"]["temperature_2m_min"][1]
    t_max = data["daily"]["temperature_2m_max"][1]
    code = data["daily"]["weather_code"][1]
    rain = data["daily"]["precipitation_probability_max"][1]

    avg_temp = (t_min + t_max) / 2

    return (
        f"🌙 Погода в {city_name} на завтра\n\n"
        f"{weather_description(code)}\n"
        f"📉 Минимум: {t_min}°C\n"
        f"📈 Максимум: {t_max}°C\n"
        f"☔ Вероятность дождя: {rain}%\n\n"
        f"{temp_feel(avg_temp)}\n"
        f"{clothing_advice(avg_temp, rain)}"
    )


def format_three_days(city_name: str, data: dict) -> str:
    labels = ["Сегодня", "Завтра", "Послезавтра"]
    parts = []

    for i in range(3):
        t_min = data["daily"]["temperature_2m_min"][i]
        t_max = data["daily"]["temperature_2m_max"][i]
        code = data["daily"]["weather_code"][i]
        rain = data["daily"]["precipitation_probability_max"][i]

        parts.append(
            f"📍 {labels[i]}\n"
            f"{weather_description(code)}\n"
            f"📉 {t_min}°C | 📈 {t_max}°C\n"
            f"☔ Дождь: {rain}%"
        )

    return f"📆 Прогноз для {city_name} на 3 дня\n\n" + "\n\n".join(parts)


def format_week(city_name: str, data: dict) -> str:
    labels = ["Сегодня", "Завтра", "День 3", "День 4", "День 5", "День 6", "День 7"]
    parts = []

    for i in range(7):
        t_min = data["daily"]["temperature_2m_min"][i]
        t_max = data["daily"]["temperature_2m_max"][i]
        code = data["daily"]["weather_code"][i]
        rain = data["daily"]["precipitation_probability_max"][i]

        parts.append(
            f"📍 {labels[i]}\n"
            f"{weather_description(code)}\n"
            f"📉 {t_min}°C | 📈 {t_max}°C\n"
            f"☔ {rain}%"
        )

    return f"🗓 Прогноз для {city_name} на неделю\n\n" + "\n\n".join(parts)


def get_weather_text(mode: str, city_data: dict) -> str:
    data = fetch_weather_data(city_data["lat"], city_data["lon"], city_data["timezone"])

    if mode == "now":
        return format_now(city_data["name"], city_data["timezone"], data)
    if mode == "tomorrow":
        return format_tomorrow(city_data["name"], data)
    if mode == "three_days":
        return format_three_days(city_data["name"], data)
    if mode == "week":
        return format_week(city_data["name"], data)

    return format_today(city_data["name"], city_data["timezone"], data)


async def send_weather_reply(update: Update, mode: str):
    chat_id = update.effective_chat.id
    city_data = get_chat_city(chat_id)

    try:
        await update.message.reply_text(
            get_weather_text(mode, city_data),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await update.message.reply_text("❌ Не удалось получить погоду. Попробуй позже.")


async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    city_data = get_chat_city(chat_id)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_weather_text("today", city_data),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Не удалось получить ежедневную погоду."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    get_chat_city(chat_id)

    keyboard = [
        ["🌡 Сейчас", "📅 Сегодня"],
        ["🌙 Завтра", "📆 3 дня"],
        ["🗓 Неделя", "📍 Ташкент"],
        [KeyboardButton("📌 Отправить локацию", request_location=True)],
        ["⏰ Вкл авто-погоду", "❌ Выкл авто-погоду"],
        ["ℹ️ Помощь", "🤖 О боте"],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Я умный погодный бот 🌤\n\n"
        "Я умею:\n"
        "- показывать погоду сейчас\n"
        "- прогноз на сегодня, завтра, 3 дня и неделю\n"
        "- искать любой город\n"
        "- принимать геолокацию\n"
        "- отправлять погоду автоматически каждый день\n\n"
        "Выбери действие или просто напиши название города:",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Что умеет бот:\n\n"
        "🌡 Сейчас — текущая погода\n"
        "📅 Сегодня — прогноз на сегодня\n"
        "🌙 Завтра — прогноз на завтра\n"
        "📆 3 дня — прогноз на 3 дня\n"
        "🗓 Неделя — прогноз на неделю\n"
        "📍 Ташкент — быстро переключиться на Ташкент\n"
        "📌 Отправить локацию — погода по твоему местоположению\n"
        "⏰ Вкл авто-погоду — ежедневная отправка в 8:00\n"
        "❌ Выкл авто-погоду — отключить рассылку\n\n"
        "Также можно просто написать название любого города."
    )
    await update.message.reply_text(text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 О боте\n\n"
        "Это погодный бот, который умеет:\n"
        "- работать 24/7\n"
        "- показывать прогноз по городам\n"
        "- принимать геолокацию\n"
        "- отправлять ежедневную погоду автоматически"
    )
    await update.message.reply_text(text)


async def now_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "now")


async def today_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "today")


async def tomorrow_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "tomorrow")


async def three_days_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "three_days")


async def week_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_weather_reply(update, "week")


async def set_tashkent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    set_chat_city(
        chat_id,
        DEFAULT_CITY["name"],
        DEFAULT_CITY["lat"],
        DEFAULT_CITY["lon"],
        DEFAULT_CITY["timezone"],
    )
    await update.message.reply_text("📍 Город переключен на Ташкент.")
    await send_weather_reply(update, "today")


async def enable_auto_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    old_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in old_jobs:
        job.schedule_removal()

    context.job_queue.run_daily(
        send_daily_weather,
        time=time(hour=8, minute=0, second=0),
        chat_id=chat_id,
        name=str(chat_id),
    )

    city_data = get_chat_city(chat_id)
    await update.message.reply_text(
        f"✅ Авто-погода включена.\n"
        f"Теперь каждый день в 8:00 я буду присылать погоду для города: {city_data['name']}"
    )


async def disable_auto_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if not jobs:
        await update.message.reply_text("Авто-погода у тебя не была включена.")
        return

    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("❌ Авто-погода выключена.")


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lat = update.message.location.latitude
    lon = update.message.location.longitude

    set_chat_city(chat_id, "вашего местоположения", lat, lon, "auto")
    await update.message.reply_text("📌 Локация получена. Показываю погоду для твоего местоположения.")
    await send_weather_reply(update, "today")


async def city_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, city_query: str):
    chat_id = update.effective_chat.id

    try:
        city = get_coordinates(city_query)
        if not city:
            await update.message.reply_text("❌ Город не найден. Попробуй написать название по-другому.")
            return

        city_name = city["name"]
        if city.get("country"):
            city_name = f"{city['name']}, {city['country']}"

        set_chat_city(chat_id, city_name, city["lat"], city["lon"], city["timezone"])
        await update.message.reply_text(f"🌍 Город выбран: {city_name}")
        await send_weather_reply(update, "today")
    except Exception:
        await update.message.reply_text("❌ Не удалось найти город. Попробуй позже.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    city_data = get_chat_city(chat_id)
    mode = query.data

    try:
        if mode == "set_tashkent":
            set_chat_city(
                chat_id,
                DEFAULT_CITY["name"],
                DEFAULT_CITY["lat"],
                DEFAULT_CITY["lon"],
                DEFAULT_CITY["timezone"],
            )
            city_data = get_chat_city(chat_id)
            mode = "today"

        await query.edit_message_text(
            text=get_weather_text(mode, city_data),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await query.edit_message_text("❌ Не удалось обновить погоду.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "🌡 Сейчас":
        await now_weather(update, context)
    elif text == "📅 Сегодня":
        await today_weather(update, context)
    elif text == "🌙 Завтра":
        await tomorrow_weather(update, context)
    elif text == "📆 3 дня":
        await three_days_weather(update, context)
    elif text == "🗓 Неделя":
        await week_weather(update, context)
    elif text == "📍 Ташкент":
        await set_tashkent(update, context)
    elif text == "⏰ Вкл авто-погоду":
        await enable_auto_weather(update, context)
    elif text == "❌ Выкл авто-погоду":
        await disable_auto_weather(update, context)
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🤖 О боте":
        await about_command(update, context)
    elif text:
        await city_search_handler(update, context, text)
    else:
        await update.message.reply_text("Нажми кнопку из меню 👇")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("now", now_weather))
    app.add_handler(CommandHandler("today", today_weather))
    app.add_handler(CommandHandler("tomorrow", tomorrow_weather))
    app.add_handler(CommandHandler("three_days", three_days_weather))
    app.add_handler(CommandHandler("week", week_weather))
    app.add_handler(CommandHandler("auto_on", enable_auto_weather))
    app.add_handler(CommandHandler("auto_off", disable_auto_weather))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот работает...")
    app.run_polling()


if __name__ == "__main__":
    main()
