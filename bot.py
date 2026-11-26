import asyncio
import os
import shutil
import time
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

TOKEN = os.getenv("BOT_TOKEN", "9248679108:AAGzHgw5RlPI_PdDAE0oPYlFU6mL5vm5Oz4")

bot = Bot(token=TOKEN)
dp = Dispatcher()

NOMINALS = ["1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000"]
BASE_DIR = "dataset"

for nom in NOMINALS:
    os.makedirs(os.path.join(BASE_DIR, nom), exist_ok=True)


def get_nominals_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for nom in NOMINALS:
        row.append(InlineKeyboardButton(text=f"{nom} swm", callback_data=f"save:{nom}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Biykar etiw", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


pending_photos = {}


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalawma aleykum! Kupyura dataset jıynawshı bot.\n\n"
        "📸 Súwret jiberiń — papkaǵa saqlayman.\n"
        "📊 /stats — hár bir kupyuradan neshe súwret jıynalǵanın kóriw.\n"
        "📦 /export — barlıq datasetti ZIP arxiv qılıp júklep alıw."
    )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    lines = ["📊 <b>Jıynalǵan dataset statistikası:</b>\n"]
    total = 0
    for nom in NOMINALS:
        count = len(os.listdir(os.path.join(BASE_DIR, nom)))
        total += count
        lines.append(f"• <b>{nom} swm:</b> {count} dana")
    lines.append(f"\n<b>Jámi:</b> {total} súwret")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("export"))
async def cmd_export(message: types.Message):
    wait_msg = await message.answer("⏳ Dataset arxivlenbekte, kútiń...")
    zip_filename = "kupyura_dataset"
    shutil.make_archive(zip_filename, 'zip', BASE_DIR)
    zip_path = f"{zip_filename}.zip"

    try:
        doc = FSInputFile(zip_path)
        await message.answer_document(doc, caption="📦 Tayar dataset (ZIP arxiv)")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        await wait_msg.delete()


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    pending_photos[message.from_user.id] = photo.file_id
    await message.reply("Bul qansha swmlıq kupyura?", reply_markup=get_nominals_keyboard())


@dp.message(F.document & F.document.mime_type.startswith("image/"))
async def handle_document_image(message: types.Message):
    pending_photos[message.from_user.id] = message.document.file_id
    await message.reply("Bul qansha swmlıq kupyura?", reply_markup=get_nominals_keyboard())


@dp.callback_query(F.data.startswith("save:"))
async def save_image_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    nominal = callback.data.split(":")[1]

    file_id = pending_photos.get(user_id)
    if not file_id:
        await callback.answer("Súwret tabılmadı, qaytadan jiberiń.", show_alert=True)
        return

    filename = f"{nominal}_{user_id}_{int(time.time() * 1000)}.jpg"
    save_path = os.path.join(BASE_DIR, nominal, filename)

    file_info = await bot.get_file(file_id)
    await bot.download_file(file_info.file_path, destination=save_path)

    count = len(os.listdir(os.path.join(BASE_DIR, nominal)))
    del pending_photos[user_id]

    await callback.message.edit_text(
        f"✅ Saqlandı: <b>{nominal} swm</b>\n"
        f"📁 Papkada jámi: <b>{count}</b> súwret boldı.",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery):
    pending_photos.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Biykar etildi.")
    await callback.answer()


# Render va Koyeb uchun port ochib turuvchi web-server
async def health_check(request):
    return web.Response(text="Bot ishlamoqda!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    await start_web_server()
    print("Bot iske tústi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())