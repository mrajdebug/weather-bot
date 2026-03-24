from datetime import datetime, time
from zoneinfo import ZoneInfo
import requests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import os

TOKEN = os.getenv("8784508057:AAFZH6ZncD3rm_UqtOSRIItuFvTyeV1GxaM")

print("TOKEN VALUE:", TOKEN)

LAT = 41.2646
LON = 69.2163
TIMEZONE = "Asia/Tashkent"


def get_time_of_day_emoji() -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
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


def fetch_weather_data() -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}"
        f"&longitude={LON}"
        "&current=temperature_2m,wind_speed_10m,weather_code,relative_humidity_2m,apparent_temperature"
        "&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max"
        "&timezone=Asia%2FTashkent"
        "&forecast_days=7"
    )

    response = requests.get(url, timeout=10)
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
                InlineKeyboardButton("🔄 Обновить", callback_data="today"),
            ],
        ]
    )


def format_now(data: dict) -> str:
    current_temp = data["current"]["temperature_2m"]
    feels_like = data["current"]["apparent_temperature"]
    wind = data["current"]["wind_speed_10m"]
    humidity = data["current"]["relative_humidity_2m"]
    code = data["current"]["weather_code"]

    emoji = get_time_of_day_emoji()
    desc = weather_description(code)

    return (
        f"{emoji} Погода в Ташкенте сейчас\n\n"
        f"{desc}\n"
        f"🌡 Температура: {current_temp}°C\n"
        f"🤔 Ощущается как: {feels_like}°C\n"
        f"💧 Влажность: {humidity}%\n"
        f"💨 Ветер: {wind} км/ч\n"
        f"{temp_feel(current_temp)}"
    )


def format_today(data: dict) -> str:
    current_temp = data["current"]["temperature_2m"]
    feels_like = data["current"]["apparent_temperature"]
    wind = data["current"]["wind_speed_10m"]
    humidity = data["current"]["relative_humidity_2m"]
    code = data["current"]["weather_code"]

    t_min = data["daily"]["temperature_2m_min"][0]
    t_max = data["daily"]["temperature_2m_max"][0]
    rain = data["daily"]["precipitation_probability_max"][0]

    return (
        f"{get_time_of_day_emoji()} Погода в Ташкенте на сегодня\n\n"
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


def format_tomorrow(data: dict) -> str:
    t_min = data["daily"]["temperature_2m_min"][1]
    t_max = data["daily"]["temperature_2m_max"][1]
    code = data["daily"]["weather_code"][1]
    rain = data["daily"]["precipitation_probability_max"][1]

    avg_temp = (t_min + t_max) / 2

    return (
        "🌙 Погода в Ташкенте на завтра\n\n"
        f"{weather_description(code)}\n"
        f"📉 Минимум: {t_min}°C\n"
        f"📈 Максимум: {t_max}°C\n"
        f"☔ Вероятность дождя: {rain}%\n\n"
        f"{temp_feel(avg_temp)}\n"
        f"{clothing_advice(avg_temp, rain)}"
    )


def format_three_days(data: dict) -> str:
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

    return "📆 Прогноз на 3 дня\n\n" + "\n\n".join(parts)


def format_week(data: dict) -> str:
    day_names = [
        "Сегодня",
        "Завтра",
        "День 3",
        "День 4",
        "День 5",
        "День 6",
        "День 7",
    ]

    parts = []

    for i in range(7):
        t_min = data["daily"]["temperature_2m_min"][i]
        t_max = data["daily"]["temperature_2m_max"][i]
        code = data["daily"]["weather_code"][i]
        rain = data["daily"]["precipitation_probability_max"][i]

        parts.append(
            f"📍 {day_names[i]}\n"
            f"{weather_description(code)}\n"
            f"📉 {t_min}°C | 📈 {t_max}°C\n"
            f"☔ {rain}%"
        )

    return "🗓 Прогноз на неделю\n\n" + "\n\n".join(parts)


def get_weather_text(mode: str = "today") -> str:
    data = fetch_weather_data()

    if mode == "now":
        return format_now(data)
    if mode == "tomorrow":
        return format_tomorrow(data)
    if mode == "three_days":
        return format_three_days(data)
    if mode == "week":
        return format_week(data)

    return format_today(data)


async def send_weather_reply(update: Update, mode: str):
    try:
        await update.message.reply_text(
            get_weather_text(mode),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await update.message.reply_text("❌ Не удалось получить погоду. Попробуй позже.")


async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_weather_text("today"),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Не удалось получить ежедневную погоду."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🌡 Сейчас", "📅 Сегодня"],
        ["🌙 Завтра", "📆 3 дня"],
        ["🗓 Неделя", "⏰ Вкл авто-погоду"],
        ["❌ Выкл авто-погоду", "ℹ️ Помощь"],
        ["🤖 О боте"],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Привет! Я умный погодный бот для Ташкента 👋\n\nВыбери действие:",
        reply_markup=markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Что умеет бот:\n\n"
        "🌡 Сейчас — погода прямо сейчас\n"
        "📅 Сегодня — прогноз на сегодня\n"
        "🌙 Завтра — прогноз на завтра\n"
        "📆 3 дня — короткий прогноз\n"
        "🗓 Неделя — прогноз на 7 дней\n"
        "⏰ Вкл авто-погоду — каждый день в 8:00\n"
        "❌ Выкл авто-погоду — отключить рассылку\n\n"
        "Команды:\n"
        "/start\n"
        "/now\n"
        "/today\n"
        "/tomorrow\n"
        "/three_days\n"
        "/week\n"
        "/auto_on\n"
        "/auto_off\n"
        "/help"
    )
    await update.message.reply_text(text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 О боте\n\n"
        "Этот бот показывает погоду в Ташкенте:\n"
        "- текущую\n"
        "- на сегодня\n"
        "- на завтра\n"
        "- на 3 дня\n"
        "- на неделю\n"
        "- и умеет слать её автоматически каждое утро."
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

    await update.message.reply_text(
        "✅ Авто-погода включена.\nКаждый день в 8:00 я буду присылать прогноз."
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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mode = query.data

    try:
        await query.edit_message_text(
            text=get_weather_text(mode),
            reply_markup=make_inline_keyboard(),
        )
    except Exception:
        await query.edit_message_text("❌ Не удалось обновить погоду.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

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
    elif text == "⏰ Вкл авто-погоду":
        await enable_auto_weather(update, context)
    elif text == "❌ Выкл авто-погоду":
        await disable_auto_weather(update, context)
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🤖 О боте":
        await about_command(update, context)
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот работает...")
    app.run_polling()


if __name__ == "__main__":
    main()
    main()
