import asyncio
import logging
import random
import csv
from datetime import datetime
import mysql.connector
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.enums import ParseMode
import aiofiles

API_TOKEN = '340005579:AAGW3s6k9TG9ocfmsSmxXR7XcN45rWK20LE'  # 🔐 Замените на ваш токен

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_states = {}

# DB
def db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root1',
        database='lab1'
    )

def get_tasks():
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, text FROM items")
        return cur.fetchall()

def insert_task(text):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO items (text) VALUES (%s)", (text,))
        conn.commit()

def update_task(task_id, new_text):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE items SET text = %s WHERE id = %s", (new_text, task_id))
        conn.commit()

def delete_task(task_id):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM items WHERE id = %s", (task_id,))
        conn.commit()

# Главное меню
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Мои задачи"), KeyboardButton(text="➕ Новая задача")],
            [KeyboardButton(text="⏰ Напоминание")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def start(msg: types.Message):
    user_states[msg.chat.id] = {"step": "login"}
    await msg.answer("Введите логин:")

@dp.message()
async def handler(msg: types.Message):
    cid = msg.chat.id
    state = user_states.get(cid, {})

    # Авторизация
    if state.get("step") == "login":
        state["login"] = msg.text.strip()
        state["step"] = "pass"
        await msg.answer("Введите пароль:")
        return

    if state.get("step") == "pass":
        if state["login"] == "admin" and msg.text.strip() == "admin":
            state["auth"] = True
            state["step"] = "idle"
            await msg.answer("✅ Добро пожаловать!", reply_markup=main_menu())
        else:
            await msg.answer("❌ Неверные данные. /start")
            user_states.pop(cid, None)
        return

    if not state.get("auth"):
        await msg.answer("⚠ Сначала авторизуйтесь через /start")
        return

    # Добавление
    if state.get("step") == "adding":
        insert_task(msg.text.strip())
        await msg.answer("✅ Задача добавлена!", reply_markup=main_menu())
        state["step"] = "idle"
        return

    # Редактирование
    if state.get("step") == "editing":
        update_task(state["edit_id"], msg.text.strip())
        await msg.answer("✅ Обновлено!", reply_markup=main_menu())
        state["step"] = "idle"
        return

    # Напоминание
    if state.get("step") == "reminder_text":
        state["reminder_task"] = msg.text.strip()
        state["step"] = "reminder_time"
        await msg.answer("Во сколько напомнить? (в формате ЧЧ:ММ, например 14:30):")
        return

    if state.get("step") == "reminder_time":
        try:
            hour, minute = map(int, msg.text.strip().split(":"))
            now = datetime.now()
            remind_time = datetime(now.year, now.month, now.day, hour, minute)
            if remind_time <= now:
                remind_time = remind_time.replace(day=now.day + 1)
            delay = (remind_time - now).total_seconds()
            asyncio.create_task(schedule_reminder(cid, state["reminder_task"], delay))
            await msg.answer("✅ Напоминание установлено!", reply_markup=main_menu())
            state["step"] = "idle"
        except:
            await msg.answer("⚠ Неверный формат времени. Пример: 14:30")
        return

    # Меню
    if msg.text == "📝 Мои задачи":
        await send_task_list(msg)
    elif msg.text == "➕ Новая задача":
        state["step"] = "adding"
        await msg.answer("Введите текст новой задачи:")
    elif msg.text == "⏰ Напоминание":
        state["step"] = "reminder_text"
        await msg.answer("Что напомнить?")

# Напоминание
async def schedule_reminder(chat_id, task_text, delay):
    await asyncio.sleep(delay)
    await bot.send_message(chat_id, f"🔔 Напоминание:\n<b>{task_text}</b>", parse_mode=ParseMode.HTML)

# Callback (редактирование и удаление)
@dp.callback_query()
async def cb_handler(cb: types.CallbackQuery):
    cid = cb.message.chat.id
    state = user_states.get(cid, {})
    if not state.get("auth"):
        await cb.message.answer("⚠ Авторизуйтесь.")
        return
    action, tid = cb.data.split("_")
    tid = int(tid)
    if action == "del":
        delete_task(tid)
        await cb.message.answer("🗑 Удалено.")
        await send_task_list(cb.message)
    elif action == "edit":
        state["step"] = "editing"
        state["edit_id"] = tid
        await cb.message.answer("Введите новый текст:")

# Показ задач
async def send_task_list(msg: types.Message):
    tasks = get_tasks()
    if not tasks:
        await msg.answer("📭 Список задач пуст.")
        return
    for tid, text in tasks:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✏", callback_data=f"edit_{tid}"),
            InlineKeyboardButton(text="🗑", callback_data=f"del_{tid}")
        ]])
        await msg.answer(f"<b>{text}</b>", reply_markup=markup, parse_mode=ParseMode.HTML)



# Запуск
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
