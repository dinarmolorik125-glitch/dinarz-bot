import asyncio
import logging
import os
from io import BytesIO

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from rembg import remove, new_session
from PIL import Image


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()

session = new_session("u2netp")

pending_photos = {}


def remove_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✂️ УБРАТЬ ФОН",
                    callback_data="remove_bg"
                )
            ]
        ]
    )


             def remove_background(data):
    result = remove(data, session=session)

    image = Image.open(BytesIO(result)).convert("RGBA")

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)

    return output.getvalue()


async def health(request):
    return web.Response(text="DINARZ BOT работает ❤️")


async def start_web_server():
    app = web.Application()

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", "10000"))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(f"Web server started on port {port}")


@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🤖 <b>DINARZ BOT</b>\n\n"
        "Привет!\n\n"
        "📸 Отправь мне фотографию.\n"
        "✂️ Я уберу фон.\n"
        "🖼️ Верну прозрачный PNG.\n\n"
        "С любовью от DINAUZ ❤️",
        parse_mode="HTML"
    )


@dp.message(Command("help"))
async def help_command(message: Message):

    await message.answer(
        "📸 Просто отправь фотографию.\n\n"
        "После этого появится кнопка "
        "«✂️ УБРАТЬ ФОН»."
    )


@dp.message(F.photo)
async def photo_received(message: Message):

    photo = message.photo[-1]

    pending_photos[message.chat.id] = photo.file_id

    await message.answer(
        "📸 <b>Фото получил!</b>\n\n"
        "Теперь нажми кнопку ниже 👇",
        parse_mode="HTML",
        reply_markup=remove_button()
    )


@dp.callback_query(F.data == "remove_bg")
async def remove_bg(callback: CallbackQuery):

    await callback.answer()

    chat_id = callback.message.chat.id

    file_id = pending_photos.get(chat_id)

    if not file_id:

        await callback.message.answer(
            "📸 Сначала отправь фотографию."
        )

        return

    status = await callback.message.answer(
        "⏳ Загружаю фотографию..."
    )

    try:

        telegram_file = await bot.get_file(file_id)

        data = BytesIO()

        await bot.download_file(
            telegram_file.file_path,
            data
        )

        await status.edit_text(
            "🤖 Убираю фон...\n\n"
            "Подожди немного ⏳"
        )

        result = await asyncio.to_thread(
            remove_background,
            data.getvalue()
        )

        await status.delete()

        await callback.message.answer_document(

            BufferedInputFile(
                result,
                filename="DINARZ_BOT.png"
            ),

            caption=(
                "✨ <b>Ваше фото готово!</b>\n\n"
                "Формат: прозрачный PNG\n\n"
                "С любовью от DINAUZ ❤️"
            ),

            parse_mode="HTML"
        )

    except Exception as error:

        logging.exception(error)

        await status.edit_text(
            "❌ Не получилось обработать фото.\n\n"
            "Попробуй отправить JPG или PNG."
        )


@dp.message()
async def other_message(message: Message):

    await message.answer(
        "📸 Отправь мне фотографию, "
        "и я уберу с неё фон."
    )


async def main():

    await start_web_server()

    print("DINARZ BOT запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
