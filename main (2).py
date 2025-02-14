import sqlite3
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import Message
import os

if not os.path.exists("databases"):
    os.makedirs("databases")


def get_db_path(chat_id):
    """Возвращает путь к БД для конкретной группы."""
    db_name = f"data_group_{chat_id}.db"
    return os.path.join("databases", db_name)

TOKEN = "7914429035:AAFXYjhHpfdIaAzw1o4Qv578jfZOFG_1s6Y"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

logging.basicConfig(level=logging.INFO)


def initialize_db(chat_id):
    """Создаёт БД и таблицы для группы, если их нет."""
    db_path = get_db_path(chat_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            deposit REAL DEFAULT 0,
            trader_rate REAL DEFAULT 10,
            payout REAL DEFAULT 0,
            exchange_rate REAL DEFAULT 100
        )
    """)

    # Если настроек нет — добавляем их
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (id) VALUES (1)")

    conn.commit()
    conn.close()



@router.message(Command("start"))
async def start(message: Message):
    chat_id = message.chat.id
    db_path = get_db_path(chat_id)

    # Гарантируем, что БД и таблицы существуют
    initialize_db(chat_id)
    await message.answer("Бот запущен!")


@router.message(Command("чек"))
async def add_receipt_command(message: Message):
    try:
        chat_id = message.chat.id
        db_path = get_db_path(chat_id)

        # Гарантируем, что БД и таблицы существуют
        initialize_db(chat_id)
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("Неверный формат")

        amount = float(parts[1])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Исправлено!

        conn = sqlite3.connect(f"{db_path}")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO receipts (amount, timestamp) VALUES (?, ?)", (amount, timestamp))
        conn.commit()
        conn.close()

        sign = "добавлен" if amount > 0 else "удален"
        await message.answer(f"Чек на {amount} {sign} в {timestamp}.")

    except (IndexError, ValueError):
        await message.answer("Некорректный формат. Используйте: /чек 100.00 или /чек -50.00")


@router.message(Command("депозит"))
async def set_deposit(message: Message):
    try:
        chat_id = message.chat.id
        db_path = get_db_path(chat_id)

        # Гарантируем, что БД и таблицы существуют
        initialize_db(chat_id)
        amount = float(message.text.split()[1])
        conn = sqlite3.connect(f"{db_path}")
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET deposit = ? WHERE id = 1", (amount,))
        conn.commit()
        conn.close()
        await message.answer(f"Депозит установлен: {amount}")
    except (IndexError, ValueError):
        await message.answer("Некорректный формат. Используйте: /депозит 1000")


@router.message(Command("ставка"))
async def set_trader_rate(message: Message):
    try:
        chat_id = message.chat.id
        db_path = get_db_path(chat_id)

        # Гарантируем, что БД и таблицы существуют
        initialize_db(chat_id)
        rate = float(message.text.split()[1])
        conn = sqlite3.connect(f"{db_path}")
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET trader_rate = ? WHERE id = 1", (rate,))
        conn.commit()
        conn.close()
        await message.answer(f"Ставка трейдера установлена: {rate}%")
    except (IndexError, ValueError):
        await message.answer("Некорректный формат. Используйте: /ставка 10")


@router.message(Command("выплата"))
async def set_payout(message: Message):
    try:
        chat_id = message.chat.id
        db_path = get_db_path(chat_id)

        # Гарантируем, что БД и таблицы существуют
        initialize_db(chat_id)
        amount = float(message.text.split()[1])

        conn = sqlite3.connect(f"{db_path}")
        cursor = conn.cursor()

        # Получаем текущий остаток к выплате
        cursor.execute("SELECT SUM(amount) FROM receipts WHERE timestamp LIKE ?", (f"{datetime.now().strftime('%Y-%m-%d')}%",))
        turnover = cursor.fetchone()[0] or 0

        cursor.execute("SELECT trader_rate, payout FROM settings WHERE id = 1")
        result = cursor.fetchone()
        if result is None:
            await message.answer("Ошибка: настройки не найдены.")
            conn.close()
            return

        trader_rate, current_payout = result

        # Учитываем комиссию трейдера
        turnover_after_fee = turnover - (turnover * trader_rate / 100)
        payout_left = max(turnover_after_fee - current_payout, 0)

        if amount > payout_left:
            await message.answer(f"Ошибка: сумма выплаты {amount:.2f} превышает доступную {payout_left:.2f}.")
            conn.close()
            return

        # Обновляем сумму выплаченного
        cursor.execute("UPDATE settings SET payout = payout + ? WHERE id = 1", (amount,))
        conn.commit()
        conn.close()

        await message.answer(f"Выплата {amount:.2f} проведена. Осталось к выплате: {payout_left - amount:.2f}")

    except (IndexError, ValueError):
        await message.answer("Некорректный формат. Используйте: /выплата 500")


@router.message(Command("курс"))
async def set_exchange_rate(message: Message):
    try:
        chat_id = message.chat.id
        db_path = get_db_path(chat_id)

        # Гарантируем, что БД и таблицы существуют
        initialize_db(chat_id)
        rate = float(message.text.split()[1])
        conn = sqlite3.connect(f"{db_path}")
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET exchange_rate = ? WHERE id = 1", (rate,))
        conn.commit()
        conn.close()
        await message.answer(f"Курс установлен: {rate}")
    except (IndexError, ValueError):
        await message.answer("Некорректный формат. Используйте: /курс 92.5")

from datetime import datetime

@router.message(Command("инфо"))
async def get_last_receipts(message: Message):
    chat_id = message.chat.id
    db_path = get_db_path(chat_id)
    initialize_db(chat_id)  # Проверяем, есть ли БД и таблицы

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Выбираем последние 5 чеков
    cursor.execute("SELECT amount, timestamp FROM receipts ORDER BY id DESC LIMIT 5")
    receipts = cursor.fetchall()

    # Получаем настройки
    cursor.execute("SELECT deposit, trader_rate, payout, exchange_rate FROM settings WHERE id = 1")
    result = cursor.fetchone()

    if result is None:
        await message.answer("Ошибка: настройки не найдены.")
        conn.close()
        return

    deposit, trader_rate, payout, exchange_rate = result

    # Оборот за сегодня
    cursor.execute("SELECT SUM(amount) FROM receipts WHERE DATE(timestamp) = DATE('now', 'localtime')")
    turnover = cursor.fetchone()[0] or 0  

    # Учитываем комиссию трейдера
    trader_fee = turnover * (trader_rate / 100)
    turnover_after_fee = turnover - trader_fee

    # Осталось к выплате
    payout_left = max(turnover_after_fee - payout, 0)

    receipt_text = "\n".join([
        f"{r[1]} | {r[0]:.2f} | {r[0] / exchange_rate:.2f}"
        for r in receipts
    ]) if receipts else "Нет чеков"

    response = (f"<b>Последние 5 чеков:</b>\n{receipt_text}\n\n"
                f"<b>Депозит:</b> {deposit:.2f} | {deposit / exchange_rate:.2f}\n"
                f"<b>Оборот за сегодня:</b> {turnover:.2f} | {turnover / exchange_rate:.2f}\n"
                f"<b>Ставка трейдера:</b> {trader_rate:.2f}%\n"
                f"<b>Оборот (-{trader_rate:.2f}%):</b> {turnover_after_fee:.2f} | {turnover_after_fee / exchange_rate:.2f}\n"
                f"<b>Осталось к выплате:</b> {payout_left:.2f} | {payout_left / exchange_rate:.2f}\n"
                f"<b>Выплачено:</b> {payout:.2f} | {payout / exchange_rate:.2f}\n"
                f"<b>Курс:</b> {exchange_rate:.2f}")

    await message.answer(response, parse_mode="HTML")
    conn.close()


@router.message(Command("сброс"))
async def reset_data(message: Message):
    chat_id = message.chat.id
    db_path = get_db_path(chat_id)

    # Гарантируем, что БД и таблицы существуют
    initialize_db(chat_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Удаляем все чеки
    cursor.execute("DELETE FROM receipts")

    # Сбрасываем настройки
    cursor.execute("""
        UPDATE settings 
        SET deposit = 0, trader_rate = 10, payout = 0, exchange_rate = 1
        WHERE id = 1
    """)

    conn.commit()
    conn.close()

    await message.answer("<b>Все данные для этой группы сброшены!</b>", parse_mode="HTML")



async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
