from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
import database as db
from keyboards import back_btn

router = Router()


class MarketStates(StatesGroup):
    buy_salary = State()
    hire_free_salary = State()


async def notify_admins(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📢 {text}")
        except:
            pass


@router.callback_query(F.data == "market")
async def market(callback: CallbackQuery):
    players = await db.get_market_players()
    if not players:
        await callback.message.edit_text("🏪 Маркет пуст.", reply_markup=back_btn())
        return
    text = "🏪 **Маркет игроков:**\n\n"
    buttons = []
    for p in players:
        team_info = p['team_name'] or "Free"
        text += f"• **{p['nickname']}** ({team_info}) — ${p['market_price']:,.0f}\n"
        buttons.append([InlineKeyboardButton(
            text=f"💰 Купить {p['nickname']} (${p['market_price']:,.0f})",
            callback_data=f"buy_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("buy_"))
async def buy_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[1])
    player = await db.get_player(player_id)
    team = await db.get_team_by_manager(callback.from_user.id)

    if not team:
        await callback.answer("У вас нет команды!", show_alert=True)
        return

    if not player or not player['is_on_market']:
        await callback.answer("Игрок не на маркете", show_alert=True)
        return

    if player['team_id'] == team['id']:
        await callback.answer("Это ваш игрок!", show_alert=True)
        return

    if team['budget'] < player['market_price']:
        await callback.answer(f"Недостаточно бюджета! Нужно ${player['market_price']:,.0f}", show_alert=True)
        return

    await state.update_data(buy_player_id=player_id, buy_price=player['market_price'])
    await callback.message.edit_text(
        f"Введите зарплату для **{player['nickname']}**:",
        parse_mode="Markdown"
    )
    await state.set_state(MarketStates.buy_salary)


@router.message(MarketStates.buy_salary)
async def buy_salary(message: Message, state: FSMContext, bot: Bot):
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return

    data = await state.get_data()
    player = await db.get_player(data['buy_player_id'])
    buyer_team = await db.get_team_by_manager(message.from_user.id)
    seller_team_id = player['team_id']
    price = data['buy_price']

    # Deduct from buyer
    await db.update_team_budget(buyer_team['id'], -price)

    # Add to seller
    if seller_team_id:
        await db.update_team_budget(seller_team_id, price)
        seller_team = await db.get_team(seller_team_id)
    else:
        seller_team = None

    # Transfer player
    await db.add_player_to_team(data['buy_player_id'], buyer_team['id'], salary)
    await db.add_transfer_record(
        data['buy_player_id'], seller_team_id, buyer_team['id'],
        "market_buy", price, salary
    )

    await message.answer(
        f"✅ **{player['nickname']}** куплен за **${price:,.0f}** с зарплатой **${salary:,.0f}**",
        reply_markup=back_btn("my_team"), parse_mode="Markdown"
    )

    log = f"💰 {buyer_team['name']} купил {player['nickname']}"
    if seller_team:
        log += f" у {seller_team['name']}"
    log += f" за ${price:,.0f} (ЗП: ${salary:,.0f})"
    await notify_admins(bot, log)

    # Notify seller
    if seller_team and seller_team['manager_tg_id']:
        try:
            await bot.send_message(
                seller_team['manager_tg_id'],
                f"💰 **{player['nickname']}** куплен командой **{buyer_team['name']}** за **${price:,.0f}**",
                parse_mode="Markdown"
            )
        except:
            pass

    await state.clear()


# ========== FREE AGENTS ==========
@router.callback_query(F.data == "free_agents")
async def free_agents(callback: CallbackQuery):
    players = await db.get_free_agents()
    if not players:
        await callback.message.edit_text("📋 Нет свободных агентов.", reply_markup=back_btn())
        return

    text = "📋 **Свободные агенты:**\n\n"
    buttons = []
    for p in players:
        text += f"• **{p['nickname']}**\n"
        buttons.append([InlineKeyboardButton(
            text=f"📝 Подписать {p['nickname']}", callback_data=f"sign_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("sign_"))
async def sign_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[1])
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.answer("У вас нет команды!", show_alert=True)
        return
    player = await db.get_player(player_id)
    if player['team_id']:
        await callback.answer("Игрок уже в команде", show_alert=True)
        return
    await state.update_data(sign_player_id=player_id)
    await callback.message.edit_text(f"Введите зарплату для **{player['nickname']}**:", parse_mode="Markdown")
    await state.set_state(MarketStates.hire_free_salary)


@router.message(MarketStates.hire_free_salary)
async def hire_free_salary(message: Message, state: FSMContext, bot: Bot):
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return
    data = await state.get_data()
    team = await db.get_team_by_manager(message.from_user.id)
    player = await db.get_player(data['sign_player_id'])
    await db.add_player_to_team(data['sign_player_id'], team['id'], salary)
    await db.add_transfer_record(data['sign_player_id'], None, team['id'], "free_agent_sign", 0, salary)

    await message.answer(
        f"✅ **{player['nickname']}** подписан с зарплатой **${salary:,.0f}**",
        reply_markup=back_btn("my_team"), parse_mode="Markdown"
    )
    await notify_admins(bot, f"📝 {team['name']} подписал {player['nickname']} (ЗП: ${salary:,.0f})")
    await state.clear()