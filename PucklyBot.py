import asyncio
import random
import pytz
from g4f.client import AsyncClient
from g4f import Provider
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
import nest_asyncio
#
#### бот должен некоторое время побыть запущенным в беседе. Только после отправки нескольких сообщений при нем включенном он будет отвечать
#
nest_asyncio.apply() 

bot = Bot(
    token="7641084405:AAGwy5VauRD_91roksFkvW460Ke5tJK-VpE",
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML 
    )
)

dp = Dispatcher()
client = AsyncClient()

message_logs = {}
worker_tasks = {}
RUNNING = {}
next_message_times = {}

message_log = []

START_CMD = "kR4pd0WBY6RIed4urYBP8c9osW498Vn7"
STOP_CMD = "bb70FgP8mG9gEbxW9u7WTGNr201zMtP9"
NEXT_CMD = "jxaJ4nt2qJP3jU68zZrF97vR85bST4UA"
DIAG_MES_CMD = "Wfy041srlQ54BsrvMNEi6LRwL05z8MU7"
next_message_time = None

def moscow_time_now():
    return datetime.now(pytz.timezone("Europe/Moscow"))

def is_night():
    hour = moscow_time_now().hour
    return hour < 8

async def random_joke(username, text):
    prompt = (
        f"Сделай забавную шутку про пользователя с ником {username}, "
        f"который написал следующее: «{text}». "
        f"Шутка должна быть очень жесткой и остроумной. Можно с черным юмором. Она должна балансировать на грани и при этом оставаться концептуальной, иметь глубокий смысл. Не оформляй её как ответ, а просто сразу пиши шутку, без пояснений. Постарайся уложиться в 200 символов."
    )

    try:
        response = await client.chat.completions.create(
            provider=Provider.AnyProvider,
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        joke = response.choices[0].message.content  # response — уже строка с ответом модели
    except Exception as e:
        joke = "К сожалению, шутка не смогла быть сгенерирована."
        print(f"Все проперделолсь в запросе ГПТ. Зовите Бамбини Ф1: {e}")

    return f"{joke}"

async def worker_loop(chat_id):
    RUNNING[chat_id] = True
    bot_user = await bot.get_me()
    while RUNNING.get(chat_id, False):
        now = moscow_time_now()

        if is_night():
            sleep_seconds = ((8 - now.hour) % 24) * 3600
            next_message_times[chat_id] = now + timedelta(seconds=sleep_seconds)
            await asyncio.sleep(sleep_seconds)
            continue

        # Получаем лог для данного чата
        chat_log = message_logs.get(chat_id, [])

        eligible = [msg for msg in chat_log if len(msg.text or "") >= 3 and msg.from_user.id != bot_user.id]

        if eligible:
            msg = random.choice(eligible)
            fact_text = await random_joke(msg.from_user.username or "User", msg.text)
            try:
                await bot.send_message(chat_id, fact_text, reply_to_message_id=msg.message_id)
            except Exception as e:
                print(f"Ошибка отправки в рабочем цикле: {e}")
        else:
            print(f"В чате {chat_id} нет подходящих сообщений для шуток")

        delay = random.randint(2*3600, 4*3600)
        next_message_times[chat_id] = now + timedelta(seconds=delay)
        await asyncio.sleep(delay)
    print(f"Рабочий цикл для чата {chat_id} остановлен")

@dp.message(Command(START_CMD))
async def cmd_start(message: Message):
    chat_id = message.chat.id
    if not RUNNING.get(chat_id, False):
        # Запускаем воркер для этого чата, если не запущен
        task = asyncio.create_task(worker_loop(chat_id))
        worker_tasks[chat_id] = task
        await message.reply("Продолжайте наблюдение...")
    else:
        await message.reply("Работа в этом чате уже запущена.")

@dp.message(Command(STOP_CMD))
async def cmd_stop(message: Message):
    chat_id = message.chat.id
    if RUNNING.get(chat_id, False):
        RUNNING[chat_id] = False
        # Можно попытаться отменить задачу (если нужно)
        task = worker_tasks.pop(chat_id, None)
        if task:
            task.cancel()
        await message.reply("Работа остановлена.")
    else:
        await message.reply("В этом чате не было запущено.")

@dp.message(Command(DIAG_MES_CMD))
async def cmd_diag(message: Message):
    await message.reply("diag")

@dp.message(Command(NEXT_CMD))
async def cmd_next_send(message: Message):
    chat_id = message.chat.id
    next_time = next_message_times.get(chat_id)
    if next_time is None:
        await message.answer("Пока бот не планирует отправлять сообщения.")
    else:
        formatted_time = next_time.strftime('%Y-%m-%d %H:%M:%S')
        await message.answer(f"Кто-то получит по жопе в {formatted_time} по МСК.")

@dp.message(F.text)
async def on_message(message: Message):
    chat_id = message.chat.id
    if chat_id not in message_logs:
        message_logs[chat_id] = []
    if len(message_logs[chat_id]) >= 50:
        message_logs[chat_id].pop(0)
    message_logs[chat_id].append(message)

    if f"@{(await bot.me()).username}" in (message.text or ""):
        await message.reply("По#$%")


@dp.errors()
async def error_handler(update: types.Update, exception: Exception):
    print(f"Ошибка: {exception}")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
