from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
import database as db
from keyboards import back_btn

router = Router()


class TradeStates(StatesGroup):
    select_target_team = State()
    select_my_player = State()
    select_their_player = State()
    offered_salary = State()
    requested_salary = State()


class LoanStates(StatesGroup):
    select_target_team = State()
    select_player = State()
    loan_salary = State()


async def notify_admins(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📢 {text}")
        except:
            pass


# ==================== TRADE ====================
@router.callback_query(F.data == "offer_trade")
async def offer_trade(callback: CallbackQuery, state: FSMContext):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.answer("У вас нет команды", show_alert=True)
        return
    teams = await db.get_all_teams()
    other = [t for t in teams if t['id'] != team['id']]
    if not other:
        await callback.answer("Нет других команд", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']}", callback_data=f"trade_target_{t['id']}"
    )] for t in other]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Выберите команду для трейда:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("trade_target_"))
async def trade_target(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[-1])
    await state.update_data(trade_target_team=target_id)
    team = await db.get_team_by_manager(callback.from_user.id)
    my_players = await db.get_team_players(team['id'])
    own = [p for p in my_players if not p['loaned_from_team_id']]
    if not own:
        await callback.answer("У вас нет своих игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{p['nickname']}", callback_data=f"trade_myp_{p['id']}"
    )] for p in own]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Выберите вашего игрока для обмена:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("trade_myp_"))
async def trade_my_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[-1])
    await state.update_data(trade_my_player=player_id)
    data = await state.get_data()
    target_players = await db.get_team_players(data['trade_target_team'])
    own = [p for p in target_players if not p['loaned_from_team_id']]
    if not own:
        await callback.answer("У целевой команды нет игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{p['nickname']}", callback_data=f"trade_theirp_{p['id']}"
    )] for p in own]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Выберите игрока из другой команды:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("trade_theirp_"))
async def trade_their_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[-1])
    await state.update_data(trade_their_player=player_id)
    await callback.message.edit_text("Введите зарплату, которую вы предложите получаемому игроку:")
    await state.set_state(TradeStates.offered_salary)


@router.message(TradeStates.offered_salary)
async def trade_offered_salary(message: Message, state: FSMContext):
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return
    await state.update_data(trade_offered_salary=salary)
    await message.answer("Введите зарплату, которую другая команда будет платить вашему игроку (предложение):")
    await state.set_state(TradeStates.requested_salary)


@router.message(TradeStates.requested_salary)
async def trade_requested_salary(message: Message, state: FSMContext, bot: Bot):
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return

    data = await state.get_data()
    team = await db.get_team_by_manager(message.from_user.id)
    target_team = await db.get_team(data['trade_target_team'])
    my_player = await db.get_player(data['trade_my_player'])
    their_player = await db.get_player(data['trade_their_player'])

    trade_id = await db.create_trade_offer(
        team['id'], target_team['id'],
        data['trade_my_player'], data['trade_their_player'],
        data['trade_offered_salary'], salary
    )

    await message.answer(
        f"✅ Предложение трейда отправлено!\n"
        f"Вы: **{my_player['nickname']}** → {target_team['name']}\n"
        f"Они: **{their_player['nickname']}** → {team['name']}",
        reply_markup=back_btn("my_team"), parse_mode="Markdown"
    )

    await notify_admins(bot,
        f"🔄 Трейд: {team['name']} предлагает {my_player['nickname']} ↔ {their_player['nickname']} ({target_team['name']})"
    )

    if target_team['manager_tg_id']:
        try:
            await bot.send_message(
                target_team['manager_tg_id'],
                f"🔄 **Предложение трейда от {team['name']}!**\n"
                f"Они отдают: **{my_player['nickname']}** (ЗП для вас: ${salary:,.0f})\n"
                f"Они хотят: **{their_player['nickname']}** (ЗП для них: ${data['trade_offered_salary']:,.0f})\n\n"
                f"Проверьте входящие трейды.",
                parse_mode="Markdown"
            )
        except:
            pass

    await state.clear()


# ========== INCOMING TRADES ==========
@router.callback_query(F.data == "incoming_trades")
async def incoming_trades(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.message.edit_text("❌ У вас нет команды.", reply_markup=back_btn())
        return
    trades = await db.get_pending_trades(team['id'])
    if not trades:
        await callback.message.edit_text("📭 Нет входящих предложений трейда.", reply_markup=back_btn())
        return
    text = "🔄 **Входящие трейды:**\n\n"
    buttons = []
    for t in trades:
        text += (f"• {t['from_team_name']} предлагает **{t['offered_nick']}** "
                 f"за вашего **{t['requested_nick']}**\n"
                 f"  ЗП их игрока для вас: ${t['requested_salary']:,.0f}\n"
                 f"  ЗП вашего игрока для них: ${t['offered_salary']:,.0f}\n\n")
        buttons.append([
            InlineKeyboardButton(text=f"✅ Принять #{t['id']}", callback_data=f"acc_trade_{t['id']}"),
            InlineKeyboardButton(text=f"❌ Отклонить #{t['id']}", callback_data=f"dec_trade_{t['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("acc_trade_"))
async def accept_trade(callback: CallbackQuery, bot: Bot):
    trade_id = int(callback.data.split("_")[-1])
    trade = await db.get_trade(trade_id)
    if not trade or trade['status'] != 'pending':
        await callback.answer("Трейд уже обработан", show_alert=True)
        return

    my_team = await db.get_team_by_manager(callback.from_user.id)
    offered_player = await db.get_player(trade['offered_player_id'])
    requested_player = await db.get_player(trade['requested_player_id'])

    # Swap players
    await db.add_player_to_team(trade['offered_player_id'], trade['to_team_id'], trade['requested_salary'])
    await db.add_player_to_team(trade['requested_player_id'], trade['from_team_id'], trade['offered_salary'])

    await db.update_trade_status(trade_id, 'accepted')

    await db.add_transfer_record(
        trade['offered_player_id'], trade['from_team_id'], trade['to_team_id'],
        "trade", 0, trade['requested_salary']
    )
    await db.add_transfer_record(
        trade['requested_player_id'], trade['to_team_id'], trade['from_team_id'],
        "trade", 0, trade['offered_salary']
    )

    from_team = await db.get_team(trade['from_team_id'])
    await callback.answer("Трейд принят!", show_alert=True)
    await notify_admins(bot,
        f"✅ Трейд завершён: {offered_player['nickname']} ↔ {requested_player['nickname']} "
        f"({from_team['name']} ↔ {my_team['name']})"
    )

    if from_team['manager_tg_id']:
        try:
            await bot.send_message(
                from_team['manager_tg_id'],
                f"✅ **{my_team['name']}** принял ваш трейд!\n"
                f"Вы получили: **{requested_player['nickname']}**\n"
                f"Вы отдали: **{offered_player['nickname']}**",
                parse_mode="Markdown"
            )
        except:
            pass

    callback.data = "incoming_trades"
    await incoming_trades(callback)


@router.callback_query(F.data.startswith("dec_trade_"))
async def decline_trade(callback: CallbackQuery, bot: Bot):
    trade_id = int(callback.data.split("_")[-1])
    trade = await db.get_trade(trade_id)
    if not trade or trade['status'] != 'pending':
        await callback.answer("Трейд уже обработан", show_alert=True)
        return

    await db.update_trade_status(trade_id, 'declined')
    my_team = await db.get_team_by_manager(callback.from_user.id)
    from_team = await db.get_team(trade['from_team_id'])
    await callback.answer("Трейд отклонён", show_alert=True)
    await notify_admins(bot, f"❌ {my_team['name']} отклонил трейд от {from_team['name']}")

    if from_team['manager_tg_id']:
        try:
            await bot.send_message(
                from_team['manager_tg_id'],
                f"❌ **{my_team['name']}** отклонил ваше предложение трейда.",
                parse_mode="Markdown"
            )
        except:
            pass

    callback.data = "incoming_trades"
    await incoming_trades(callback)


# ==================== LOAN ====================
@router.callback_query(F.data == "offer_loan")
async def offer_loan(callback: CallbackQuery, state: FSMContext):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.answer("У вас нет команды", show_alert=True)
        return
    teams = await db.get_all_teams()
    other = [t for t in teams if t['id'] != team['id']]
    if not other:
        await callback.answer("Нет других команд", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']}", callback_data=f"loan_target_{t['id']}"
    )] for t in other]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text(
        "Выберите команду, из которой хотите арендовать игрока:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("loan_target_"))
async def loan_target(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split("_")[-1])
    await state.update_data(loan_target_team=target_id)
    target_players = await db.get_team_players(target_id)
    own = [p for p in target_players if not p['loaned_from_team_id']]
    if not own:
        await callback.answer("У команды нет доступных игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{p['nickname']}", callback_data=f"loan_player_{p['id']}"
    )] for p in own]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Выберите игрока для аренды:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("loan_player_"))
async def loan_player_select(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[-1])
    await state.update_data(loan_player_id=player_id)
    await callback.message.edit_text("Введите зарплату, которую вы будете платить арендованному игроку:")
    await state.set_state(LoanStates.loan_salary)


@router.message(LoanStates.loan_salary)
async def loan_salary_input(message: Message, state: FSMContext, bot: Bot):
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return

    data = await state.get_data()
    team = await db.get_team_by_manager(message.from_user.id)
    target_team = await db.get_team(data['loan_target_team'])
    player = await db.get_player(data['loan_player_id'])

    loan_id = await db.create_loan_offer(
        team['id'], target_team['id'], data['loan_player_id'], salary
    )

    await message.answer(
        f"✅ Запрос аренды отправлен!\n"
        f"Игрок: **{player['nickname']}** из **{target_team['name']}**\n"
        f"Предложенная ЗП: **${salary:,.0f}**",
        reply_markup=back_btn("my_team"), parse_mode="Markdown"
    )

    await notify_admins(bot,
        f"📥 {team['name']} запросил аренду {player['nickname']} у {target_team['name']} (ЗП: ${salary:,.0f})"
    )

    if target_team['manager_tg_id']:
        try:
            await bot.send_message(
                target_team['manager_tg_id'],
                f"📥 **{team['name']}** хочет арендовать вашего **{player['nickname']}**!\n"
                f"Предложенная ЗП: **${salary:,.0f}**\n\n"
                f"Проверьте входящие аренды.",
                parse_mode="Markdown"
            )
        except:
            pass

    await state.clear()


# ========== INCOMING LOANS ==========
@router.callback_query(F.data == "incoming_loans")
async def incoming_loans(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.message.edit_text("❌ У вас нет команды.", reply_markup=back_btn())
        return
    loans = await db.get_pending_loans_for_team(team['id'])
    if not loans:
        await callback.message.edit_text("📭 Нет входящих запросов аренды.", reply_markup=back_btn())
        return
    text = "📥 **Входящие запросы аренды:**\n\n"
    buttons = []
    for lo in loans:
        text += (f"• {lo['from_team_name']} хочет арендовать **{lo['player_nick']}**\n"
                 f"  Предложенная ЗП: ${lo['loan_salary']:,.0f}\n\n")
        buttons.append([
            InlineKeyboardButton(text=f"✅ Одобрить #{lo['id']}", callback_data=f"acc_loan_{lo['id']}"),
            InlineKeyboardButton(text=f"❌ Отклонить #{lo['id']}", callback_data=f"dec_loan_{lo['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("acc_loan_"))
async def accept_loan(callback: CallbackQuery, bot: Bot):
    loan_id = int(callback.data.split("_")[-1])
    loan = await db.get_loan(loan_id)
    if not loan or loan['status'] != 'pending':
        await callback.answer("Запрос уже обработан", show_alert=True)
        return

    player = await db.get_player(loan['player_id'])
    my_team = await db.get_team_by_manager(callback.from_user.id)
    from_team = await db.get_team(loan['from_team_id'])

    await db.set_player_loan(loan['player_id'], loan['from_team_id'], my_team['id'], loan['loan_salary'])
    await db.update_loan_status(loan_id, 'accepted')

    await db.add_transfer_record(
        loan['player_id'], my_team['id'], from_team['id'],
        "loan", 0, loan['loan_salary']
    )

    await callback.answer("Аренда одобрена!", show_alert=True)
    await notify_admins(bot,
        f"✅ Аренда: {player['nickname']} из {my_team['name']} → {from_team['name']} (ЗП: ${loan['loan_salary']:,.0f})"
    )

    if from_team['manager_tg_id']:
        try:
            await bot.send_message(
                from_team['manager_tg_id'],
                f"✅ **{my_team['name']}** одобрил аренду **{player['nickname']}**!",
                parse_mode="Markdown"
            )
        except:
            pass

    callback.data = "incoming_loans"
    await incoming_loans(callback)


@router.callback_query(F.data.startswith("dec_loan_"))
async def decline_loan(callback: CallbackQuery, bot: Bot):
    loan_id = int(callback.data.split("_")[-1])
    loan = await db.get_loan(loan_id)
    if not loan or loan['status'] != 'pending':
        await callback.answer("Запрос уже обработан", show_alert=True)
        return

    await db.update_loan_status(loan_id, 'declined')
    my_team = await db.get_team_by_manager(callback.from_user.id)
    from_team = await db.get_team(loan['from_team_id'])
    await callback.answer("Аренда отклонена", show_alert=True)
    await notify_admins(bot, f"❌ {my_team['name']} отклонил запрос аренды от {from_team['name']}")

    if from_team['manager_tg_id']:
        try:
            await bot.send_message(
                from_team['manager_tg_id'],
                f"❌ **{my_team['name']}** отклонил вашу аренду.",
                parse_mode="Markdown"
            )
        except:
            pass

    callback.data = "incoming_loans"
    await incoming_loans(callback)