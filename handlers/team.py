from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
import database as db
from keyboards import team_manage_kb, setup_type_kb, SETUP_ROLES, back_btn

router = Router()


class TeamStates(StatesGroup):
    put_market_price = State()
    put_market_player = State()
    change_salary_player = State()
    change_salary_amount = State()


async def notify_admins(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📢 {text}")
        except:
            pass


@router.callback_query(F.data == "my_team")
async def my_team(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.message.edit_text(
            "❌ У вас нет команды. Обратитесь к администратору.",
            reply_markup=back_btn()
        )
        return

    players = await db.get_team_players(team['id'])
    active = [p for p in players if not p['is_benched']]
    benched = [p for p in players if p['is_benched']]
    coach = await db.get_team_coach(team['id'])

    total_salary = sum(
        p['loan_salary'] if p['loaned_from_team_id'] else p['salary']
        for p in players
    )
    if coach:
        total_salary += coach['salary']

    text = f"🏠 **{team['name']}** [{team['tag']}]\n"
    text += f"💰 Бюджет: **${team['budget']:,.0f}**\n"
    text += f"💸 Общие зарплаты: **${total_salary:,.0f}**\n"
    text += f"🎯 Сетап: **{team['setup_type']}**\n"
    text += f"👤 Менеджер: @{team['manager_username']}\n\n"

    text += f"**Ростер ({len(active)}/5):**\n"
    for p in active:
        role = p['role'] or "—"
        loan = " (аренда)" if p['loaned_from_team_id'] else ""
        sal = p['loan_salary'] if p['loaned_from_team_id'] else p['salary']
        market = " [MARKET]" if p['is_on_market'] else ""
        text += f"  • {p['nickname']} | {role} | ${sal:,.0f}{loan}{market}\n"

    if benched:
        text += f"\n**Бенч ({len(benched)}):**\n"
        for p in benched:
            sal = p['loan_salary'] if p['loaned_from_team_id'] else p['salary']
            text += f"  • {p['nickname']} | ${sal:,.0f}\n"

    if coach:
        text += f"\n🏋️ **Тренер:** {coach['nickname']} | ${coach['salary']:,.0f}\n"

    await callback.message.edit_text(
        text, reply_markup=team_manage_kb(team['id']), parse_mode="Markdown"
    )


# ========== ROSTER ==========
@router.callback_query(F.data.startswith("roster_"))
async def show_roster(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[1])
    team = await db.get_team(team_id)
    active = await db.get_active_roster(team_id)
    text = f"📋 **Ростер {team['name']}:**\n\n"
    if not active:
        text += "Пусто\n"
    for p in active:
        role = p['role'] or "—"
        loan = " (аренда)" if p['loaned_from_team_id'] else ""
        text += f"• {p['nickname']} | Роль: {role}{loan}\n"
    await callback.message.edit_text(text, reply_markup=back_btn("my_team"), parse_mode="Markdown")


# ========== BENCH ==========
@router.callback_query(F.data.startswith("bench_"))
async def show_bench(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[1])
    team = await db.get_team(team_id)
    benched = await db.get_benched_players(team_id)
    text = f"🪑 **Бенч {team['name']}:**\n\n"
    if not benched:
        text += "Пусто\n"
    for p in benched:
        text += f"• {p['nickname']}\n"
    await callback.message.edit_text(text, reply_markup=back_btn("my_team"), parse_mode="Markdown")


# ========== SETUP ==========
@router.callback_query(F.data.startswith("setup_") and ~F.data.startswith("setup_AWP") and ~F.data.startswith("setup_NO"))
async def show_setup(callback: CallbackQuery):
    if callback.data in ["setup_AWP", "setup_AWP-IGL", "setup_NO AWP"]:
        return
    team_id = int(callback.data.split("_")[1])
    team = await db.get_team(team_id)
    active = await db.get_active_roster(team_id)
    roles = SETUP_ROLES.get(team['setup_type'], SETUP_ROLES['AWP'])

    text = f"🎯 **Сетап {team['name']}** ({team['setup_type']}):\n\n"
    for role in roles:
        assigned = next((p for p in active if p['role'] == role), None)
        if assigned:
            text += f"**{role}**: {assigned['nickname']}\n"
        else:
            text += f"**{role}**: ❌ Не назначен\n"

    # Buttons to assign roles
    unassigned = [p for p in active if not p['role']]
    buttons = []
    for role in roles:
        assigned = next((p for p in active if p['role'] == role), None)
        if not assigned:
            for p in active:
                if not p['role']:
                    buttons.append([InlineKeyboardButton(
                        text=f"Назначить {p['nickname']} → {role}",
                        callback_data=f"assignrole_{p['id']}_{role}"
                    )])

    # Also allow reassigning
    for p in active:
        for role in roles:
            buttons.append([InlineKeyboardButton(
                text=f"{p['nickname']} → {role}",
                callback_data=f"assignrole_{p['id']}_{role}"
            )])

    # Limit buttons
    buttons = buttons[:20]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("assignrole_"))
async def assign_role(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_", 2)
    player_id = int(parts[1])
    role = parts[2]

    player = await db.get_player(player_id)
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team or player['team_id'] != team['id']:
        await callback.answer("Ошибка", show_alert=True)
        return

    # Clear role from other player with same role
    active = await db.get_active_roster(team['id'])
    for p in active:
        if p['role'] == role and p['id'] != player_id:
            await db.set_player_role(p['id'], None)

    await db.set_player_role(player_id, role)
    await callback.answer(f"{player['nickname']} → {role}", show_alert=True)
    await notify_admins(bot, f"🎯 {team['name']}: {player['nickname']} назначен на роль {role}")

    # Refresh setup view
    callback.data = f"setup_{team['id']}"
    await show_setup(callback)


# ========== CHANGE SETUP TYPE ==========
@router.callback_query(F.data == "change_setup")
async def change_setup(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    await callback.message.edit_text("Выберите тип сетапа:", reply_markup=setup_type_kb())


@router.callback_query(F.data.startswith("setup_"))
async def set_setup_type(callback: CallbackQuery, bot: Bot):
    setup = callback.data.replace("setup_", "")
    if setup not in SETUP_ROLES:
        return
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    await db.set_team_setup(team['id'], setup)
    # Reset all roles
    players = await db.get_active_roster(team['id'])
    for p in players:
        await db.set_player_role(p['id'], None)
    await callback.answer(f"Сетап изменён на {setup}", show_alert=True)
    await notify_admins(bot, f"🔄 {team['name']} сменил сетап на {setup}")
    callback.data = "my_team"
    await my_team(callback)


# ========== PUT ON MARKET ==========
@router.callback_query(F.data == "put_market")
async def put_market(callback: CallbackQuery, state: FSMContext):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    players = await db.get_team_players(team['id'])
    available = [p for p in players if not p['is_on_market'] and not p['loaned_from_team_id']]
    if not available:
        await callback.answer("Нет доступных игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{p['nickname']}", callback_data=f"putmkt_{p['id']}"
    )] for p in available]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text(
        "Выберите игрока для выставления на маркет:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("putmkt_"))
async def put_mkt_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[1])
    await state.update_data(mkt_player_id=player_id)
    await callback.message.edit_text("Введите цену на маркете:")
    await state.set_state(TeamStates.put_market_price)


@router.message(TeamStates.put_market_price)
async def put_mkt_price(message: Message, state: FSMContext, bot: Bot):
    try:
        price = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return
    data = await state.get_data()
    await db.put_on_market(data['mkt_player_id'], price)
    player = await db.get_player(data['mkt_player_id'])
    team = await db.get_team_by_manager(message.from_user.id)
    await message.answer(
        f"✅ **{player['nickname']}** выставлен на маркет за **${price:,.0f}**",
        reply_markup=back_btn("my_team"), parse_mode="Markdown"
    )
    await notify_admins(bot, f"🏪 {team['name']} выставил {player['nickname']} на маркет за ${price:,.0f}")
    await state.clear()


# ========== REMOVE FROM MARKET ==========
@router.callback_query(F.data == "remove_market")
async def remove_market(callback: CallbackQuery, bot: Bot):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    players = await db.get_team_players(team['id'])
    on_market = [p for p in players if p['is_on_market']]
    if not on_market:
        await callback.answer("Нет игроков на маркете", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"❌ {p['nickname']}", callback_data=f"rmmkt_{p['id']}"
    )] for p in on_market]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Снять с маркета:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("rmmkt_"))
async def rm_mkt(callback: CallbackQuery, bot: Bot):
    player_id = int(callback.data.split("_")[1])
    player = await db.get_player(player_id)
    await db.remove_from_market(player_id)
    team = await db.get_team_by_manager(callback.from_user.id)
    await callback.answer(f"{player['nickname']} снят с маркета", show_alert=True)
    await notify_admins(bot, f"🏪 {team['name']} снял {player['nickname']} с маркета")
    callback.data = "my_team"
    await my_team(callback)


# ========== BENCH / UNBENCH ==========
@router.callback_query(F.data == "bench_player")
async def bench_player_select(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    active = await db.get_active_roster(team['id'])
    if not active:
        await callback.answer("Нет активных игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"🪑 {p['nickname']}", callback_data=f"dobench_{p['id']}"
    )] for p in active]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Забенчить:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("dobench_"))
async def do_bench(callback: CallbackQuery, bot: Bot):
    player_id = int(callback.data.split("_")[1])
    player = await db.get_player(player_id)
    await db.bench_player(player_id, True)
    team = await db.get_team_by_manager(callback.from_user.id)
    await callback.answer(f"{player['nickname']} забенчен", show_alert=True)
    await notify_admins(bot, f"🪑 {team['name']} забенчил {player['nickname']}")
    callback.data = "my_team"
    await my_team(callback)


@router.callback_query(F.data == "unbench_player")
async def unbench_player_select(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    benched = await db.get_benched_players(team['id'])
    if not benched:
        await callback.answer("Нет забенченных игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"✅ {p['nickname']}", callback_data=f"dounbench_{p['id']}"
    )] for p in benched]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Вернуть с бенча:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("dounbench_"))
async def do_unbench(callback: CallbackQuery, bot: Bot):
    player_id = int(callback.data.split("_")[1])
    player = await db.get_player(player_id)
    team = await db.get_team_by_manager(callback.from_user.id)

    # Check roster limit
    active = await db.get_active_roster(team['id'])
    if len(active) >= 5:
        await callback.answer("Ростер полный (5/5). Сначала забенчьте кого-то.", show_alert=True)
        return

    await db.bench_player(player_id, False)
    await callback.answer(f"{player['nickname']} возвращён в ростер", show_alert=True)
    await notify_admins(bot, f"✅ {team['name']} вернул {player['nickname']} с бенча")
    callback.data = "my_team"
    await my_team(callback)


# ========== RELEASE PLAYER ==========
@router.callback_query(F.data == "release_player")
async def release_player_select(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    players = await db.get_team_players(team['id'])
    own = [p for p in players if not p['loaned_from_team_id']]
    if not own:
        await callback.answer("Нет своих игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"🚪 {p['nickname']}", callback_data=f"dorelease_{p['id']}"
    )] for p in own]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Отпустить игрока:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("dorelease_"))
async def do_release(callback: CallbackQuery, bot: Bot):
    player_id = int(callback.data.split("_")[1])
    player = await db.get_player(player_id)
    team = await db.get_team_by_manager(callback.from_user.id)
    await db.remove_player_from_team(player_id)
    await db.add_transfer_record(player_id, team['id'], None, "release")
    await callback.answer(f"{player['nickname']} отпущен", show_alert=True)
    await notify_admins(bot, f"🚪 {team['name']} отпустил {player['nickname']}")
    callback.data = "my_team"
    await my_team(callback)


# ========== RETURN FROM LOAN ==========
@router.callback_query(F.data == "return_loan")
async def return_loan_select(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    players = await db.get_team_players(team['id'])
    loaned = [p for p in players if p['loaned_from_team_id']]
    if not loaned:
        await callback.answer("Нет арендованных игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"↩️ {p['nickname']}", callback_data=f"doretloan_{p['id']}"
    )] for p in loaned]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Вернуть арендованного:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("doretloan_"))
async def do_return_loan(callback: CallbackQuery, bot: Bot):
    player_id = int(callback.data.split("_")[1])
    player = await db.get_player(player_id)
    team = await db.get_team_by_manager(callback.from_user.id)
    from_team = await db.get_team(player['loaned_from_team_id'])
    await db.return_from_loan(player_id)
    await db.add_transfer_record(player_id, team['id'], from_team['id'], "loan_return")
    await callback.answer(f"{player['nickname']} возвращён", show_alert=True)
    await notify_admins(bot, f"↩️ {team['name']} вернул {player['nickname']} в {from_team['name']} (аренда)")

    if from_team['manager_tg_id']:
        try:
            await bot.send_message(
                from_team['manager_tg_id'],
                f"↩️ **{player['nickname']}** вернулся с аренды из **{team['name']}**",
                parse_mode="Markdown"
            )
        except:
            pass

    callback.data = "my_team"
    await my_team(callback)


# ========== CHANGE SALARY ==========
@router.callback_query(F.data == "change_salary")
async def change_salary_select(callback: CallbackQuery, state: FSMContext):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        return
    players = await db.get_team_players(team['id'])
    if not players:
        await callback.answer("Нет игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{p['nickname']} (${p['salary']:,.0f})", callback_data=f"chsal_{p['id']}"
    )] for p in players]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")])
    await callback.message.edit_text("Выберите игрока:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("chsal_"))
async def ch_sal_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[1])
    await state.update_data(chsal_player_id=player_id)
    await callback.message.edit_text("Введите новую зарплату:")
    await state.set_state(TeamStates.change_salary_amount)


@router.message(TeamStates.change_salary_amount)
async def ch_sal_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return
    data = await state.get_data()
    await db.set_player_salary(data['chsal_player_id'], salary)
    player = await db.get_player(data['chsal_player_id'])
    team = await db.get_team_by_manager(message.from_user.id)
    await message.answer(
        f"✅ Зарплата **{player['nickname']}** изменена на **${salary:,.0f}**",
        reply_markup=back_btn("my_team"), parse_mode="Markdown"
    )
    await notify_admins(bot, f"💰 {team['name']} изменил зарплату {player['nickname']} → ${salary:,.0f}")
    await state.clear()


# ========== COACH ==========
@router.callback_query(F.data.startswith("coach_"))
async def show_coach(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[1])
    team = await db.get_team(team_id)
    coach = await db.get_team_coach(team_id)

    if coach:
        text = f"🏋️ **Тренер {team['name']}:**\n\n"
        text += f"• {coach['nickname']} | ЗП: ${coach['salary']:,.0f}\n"

        buttons = [
            [InlineKeyboardButton(text="🚪 Уволить тренера", callback_data=f"fire_coach_{coach['id']}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")]
        ]
    else:
        text = f"🏋️ У команды **{team['name']}** нет тренера\n"
        buttons = [[InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")]]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("fire_coach_"))
async def fire_coach(callback: CallbackQuery, bot: Bot):
    coach_id = int(callback.data.split("_")[-1])
    team = await db.get_team_by_manager(callback.from_user.id)
    await db.remove_coach_from_team(coach_id)
    await callback.answer("Тренер уволен", show_alert=True)
    await notify_admins(bot, f"🏋️ {team['name']} уволил тренера")
    callback.data = "my_team"
    await my_team(callback)


# ========== TOURNAMENT INVITES ==========
@router.callback_query(F.data == "tournament_invites")
async def tournament_invites(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if not team:
        await callback.message.edit_text("❌ У вас нет команды.", reply_markup=back_btn())
        return
    invites = await db.get_team_invites(team['id'])
    if not invites:
        await callback.message.edit_text("📭 Нет инвайтов на турниры.", reply_markup=back_btn())
        return
    buttons = []
    text = "🏆 **Инвайты на турниры:**\n\n"
    for inv in invites:
        text += f"• {inv['tournament_name']}\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ Принять {inv['tournament_name']}", callback_data=f"acc_inv_{inv['id']}"),
            InlineKeyboardButton(text=f"❌ Отклонить", callback_data=f"dec_inv_{inv['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("acc_inv_"))
async def accept_invite(callback: CallbackQuery, bot: Bot):
    invite_id = int(callback.data.split("_")[-1])
    await db.update_invite_status(invite_id, "accepted")
    team = await db.get_team_by_manager(callback.from_user.id)
    await callback.answer("Инвайт принят!", show_alert=True)
    await notify_admins(bot, f"🏆 {team['name']} принял инвайт на турнир")
    callback.data = "tournament_invites"
    await tournament_invites(callback)


@router.callback_query(F.data.startswith("dec_inv_"))
async def decline_invite(callback: CallbackQuery, bot: Bot):
    invite_id = int(callback.data.split("_")[-1])
    await db.update_invite_status(invite_id, "declined")
    team = await db.get_team_by_manager(callback.from_user.id)
    await callback.answer("Инвайт отклонён", show_alert=True)
    await notify_admins(bot, f"🏆 {team['name']} отклонил инвайт на турнир")
    callback.data = "tournament_invites"
    await tournament_invites(callback)


# ========== TRANSFER HISTORY ==========
@router.callback_query(F.data == "transfer_history")
async def transfer_history(callback: CallbackQuery):
    team = await db.get_team_by_manager(callback.from_user.id)
    if team:
        history = await db.get_transfer_history(team['id'])
    else:
        history = await db.get_transfer_history()

    if not history:
        await callback.message.edit_text("📜 История трансферов пуста.", reply_markup=back_btn())
        return

    text = "📜 **История трансферов:**\n\n"
    for h in history:
        from_t = h['from_team_name'] or "Free Agent"
        to_t = h['to_team_name'] or "Free Agent"
        text += f"• **{h['player_nick']}**: {from_t} → {to_t} ({h['transfer_type']}) | ${h['price']:,.0f} | ЗП: ${h['salary']:,.0f}\n"
        text += f"  📅 {h['timestamp']}\n"

    if len(text) > 4000:
        text = text[:4000] + "\n..."

    await callback.message.edit_text(text, reply_markup=back_btn(), parse_mode="Markdown")