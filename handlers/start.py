from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from config import ADMIN_IDS
from keyboards import main_menu_kb

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "🎮 **CS2 Manager League Bot**\n\nДобро пожаловать! Выберите действие:",
        reply_markup=main_menu_kb(is_admin),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text(
        "🎮 **CS2 Manager League Bot**\n\nВыберите действие:",
        reply_markup=main_menu_kb(is_admin),
        parse_mode="Markdown"
    )