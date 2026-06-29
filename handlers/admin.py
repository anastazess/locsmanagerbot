from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
import database as db
from keyboards import admin_panel_kb, back_btn

router = Router()


class AdminStates(StatesGroup):
    create_team_name = State()
    create_team_tag = State()
    create_player_nick = State()
    create_coach_nick = State()
    set_manager_team = State()
    set_manager_id = State()
    set_budget_team = State()
    set_budget_amount = State()
    add_player_team_select = State()
    add_player_select = State()
    add_player_salary = State()
    assign_coach_team = State()
    assign_coach_select = State()
    assign_coach_salary = State()
    create_tournament_name = State()
    send_invite_tournament = State()
    send_invite_team = State()
    delete_team_select = State()
    delete_player_select = State()


def admin_check(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def notify_admin(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📢 {text}")
        except:
            pass


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not admin_check(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("⚙️ **Админ-панель**", reply_markup=admin_panel_kb(), parse_mode="Markdown")


# ========== CREATE TEAM ==========
@router.callback_query(F.data == "adm_create_team")
async def adm_create_team(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    await callback.message.edit_text("Введите название команды:")
    await state.set_state(AdminStates.create_team_name)


@router.message(AdminStates.create_team_name)
async def adm_create_team_name(message: Message, state: FSMContext):
    await state.update_data(team_name=message.text)
    await message.answer("Введите тег команды (сокращение):")
    await state.set_state(AdminStates.create_team_tag)


@router.message(AdminStates.create_team_tag)
async def adm_create_team_tag(message: Message, state: FSMContext):
    data = await state.get_data()
    team_id = await db.create_team(data['team_name'], message.text)
    await message.answer(
        f"✅ Команда **{data['team_name']}** [{message.text}] создана (ID: {team_id})",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ========== CREATE PLAYER ==========
@router.callback_query(F.data == "adm_create_player")
async def adm_create_player(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    await callback.message.edit_text("Введите никнейм игрока:")
    await state.set_state(AdminStates.create_player_nick)


@router.message(AdminStates.create_player_nick)
async def adm_create_player_nick(message: Message, state: FSMContext):
    player_id = await db.create_player(message.text)
    await message.answer(
        f"✅ Игрок **{message.text}** создан (ID: {player_id})",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ========== CREATE COACH ==========
@router.callback_query(F.data == "adm_create_coach")
async def adm_create_coach(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    await callback.message.edit_text("Введите никнейм тренера:")
    await state.set_state(AdminStates.create_coach_nick)


@router.message(AdminStates.create_coach_nick)
async def adm_create_coach_nick(message: Message, state: FSMContext):
    coach_id = await db.create_coach(message.text)
    await message.answer(
        f"✅ Тренер **{message.text}** создан (ID: {coach_id})",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ========== SET MANAGER ==========
@router.callback_query(F.data == "adm_set_manager")
async def adm_set_manager(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    teams = await db.get_all_teams()
    if not teams:
        await callback.answer("Нет команд", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']} [{t['tag']}]", callback_data=f"adm_mgr_team_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите команду:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_mgr_team_"))
async def adm_mgr_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    await state.update_data(mgr_team_id=team_id)
    await callback.message.edit_text("Введите Telegram ID менеджера:")
    await state.set_state(AdminStates.set_manager_id)


@router.message(AdminStates.set_manager_id)
async def adm_mgr_id(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Введите числовой Telegram ID:")
        return

    try:
        chat = await bot.get_chat(tg_id)
        username = chat.username or "unknown"
    except:
        username = "unknown"

    await db.set_manager(data['mgr_team_id'], tg_id, username)
    team = await db.get_team(data['mgr_team_id'])
    await message.answer(
        f"✅ Менеджер @{username} (ID: {tg_id}) назначен для **{team['name']}**",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )

    try:
        await bot.send_message(tg_id, f"🎉 Вы назначены менеджером команды **{team['name']}**!", parse_mode="Markdown")
    except:
        pass

    await state.clear()


# ========== SET BUDGET ==========
@router.callback_query(F.data == "adm_set_budget")
async def adm_set_budget(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    teams = await db.get_all_teams()
    if not teams:
        await callback.answer("Нет команд", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']} (бюджет: ${t['budget']:,.0f})", callback_data=f"adm_bud_team_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите команду:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_bud_team_"))
async def adm_bud_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    await state.update_data(bud_team_id=team_id)
    await callback.message.edit_text("Введите новый бюджет (число):")
    await state.set_state(AdminStates.set_budget_amount)


@router.message(AdminStates.set_budget_amount)
async def adm_bud_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        budget = float(message.text.strip())
    except ValueError:
        await message.answer("Введите числовое значение:")
        return
    await db.set_team_budget(data['bud_team_id'], budget)
    team = await db.get_team(data['bud_team_id'])
    await message.answer(
        f"✅ Бюджет **{team['name']}** установлен: **${budget:,.0f}**",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ========== ADD PLAYER TO TEAM ==========
@router.callback_query(F.data == "adm_add_player_team")
async def adm_add_player_team(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    teams = await db.get_all_teams()
    if not teams:
        await callback.answer("Нет команд", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']}", callback_data=f"adm_apt_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите команду:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_apt_"))
async def adm_apt_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    await state.update_data(apt_team_id=team_id)
    free = await db.get_free_agents()
    if not free:
        await callback.answer("Нет свободных игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{p['nickname']} (ID:{p['id']})", callback_data=f"adm_aps_{p['id']}"
    )] for p in free]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text(
        "Выберите игрока:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("adm_aps_"))
async def adm_aps_player(callback: CallbackQuery, state: FSMContext):
    player_id = int(callback.data.split("_")[-1])
    await state.update_data(apt_player_id=player_id)
    await callback.message.edit_text("Введите зарплату для игрока:")
    await state.set_state(AdminStates.add_player_salary)


@router.message(AdminStates.add_player_salary)
async def adm_aps_salary(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите числовое значение:")
        return
    await db.add_player_to_team(data['apt_player_id'], data['apt_team_id'], salary)
    player = await db.get_player(data['apt_player_id'])
    team = await db.get_team(data['apt_team_id'])
    await message.answer(
        f"✅ **{player['nickname']}** добавлен в **{team['name']}** с зп **${salary:,.0f}**",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ========== ASSIGN COACH ==========
@router.callback_query(F.data == "adm_assign_coach")
async def adm_assign_coach(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    teams = await db.get_all_teams()
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']}", callback_data=f"adm_act_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите команду:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_act_"))
async def adm_act_team(callback: CallbackQuery, state: FSMContext):
    team_id = int(callback.data.split("_")[-1])
    await state.update_data(act_team_id=team_id)
    coaches = await db.get_free_coaches()
    if not coaches:
        await callback.answer("Нет свободных тренеров", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{c['nickname']}", callback_data=f"adm_acs_{c['id']}"
    )] for c in coaches]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите тренера:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_acs_"))
async def adm_acs_coach(callback: CallbackQuery, state: FSMContext):
    coach_id = int(callback.data.split("_")[-1])
    await state.update_data(act_coach_id=coach_id)
    await callback.message.edit_text("Введите зарплату тренера:")
    await state.set_state(AdminStates.assign_coach_salary)


@router.message(AdminStates.assign_coach_salary)
async def adm_acs_salary(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        salary = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число:")
        return
    await db.assign_coach_to_team(data['act_coach_id'], data['act_team_id'], salary)
    await message.answer("✅ Тренер назначен!", reply_markup=admin_panel_kb())
    await state.clear()


# ========== DEDUCT SALARIES ==========
@router.callback_query(F.data == "adm_deduct_salaries")
async def adm_deduct_salaries(callback: CallbackQuery):
    if not admin_check(callback.from_user.id):
        return
    results = await db.deduct_all_salaries()
    text = "💸 **Зарплаты сняты:**\n\n"
    for r in results:
        text += f"• {r['team_name']}: -${r['total_salary']:,.0f} → Бюджет: ${r['new_budget']:,.0f}\n"
    await callback.message.edit_text(text, reply_markup=admin_panel_kb(), parse_mode="Markdown")


# ========== CREATE TOURNAMENT ==========
@router.callback_query(F.data == "adm_create_tournament")
async def adm_create_tournament(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    await callback.message.edit_text("Введите название турнира:")
    await state.set_state(AdminStates.create_tournament_name)


@router.message(AdminStates.create_tournament_name)
async def adm_tournament_name(message: Message, state: FSMContext):
    t_id = await db.create_tournament(message.text)
    await message.answer(
        f"✅ Турнир **{message.text}** создан (ID: {t_id})",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ========== SEND TOURNAMENT INVITE ==========
@router.callback_query(F.data == "adm_send_invite")
async def adm_send_invite(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    tournaments = await db.get_tournaments()
    if not tournaments:
        await callback.answer("Нет турниров", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']}", callback_data=f"adm_inv_t_{t['id']}"
    )] for t in tournaments]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите турнир:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_inv_t_"))
async def adm_inv_tournament(callback: CallbackQuery, state: FSMContext):
    t_id = int(callback.data.split("_")[-1])
    await state.update_data(inv_tournament_id=t_id)
    teams = await db.get_all_teams()
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']}", callback_data=f"adm_inv_tm_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите команду:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_inv_tm_"))
async def adm_inv_team(callback: CallbackQuery, state: FSMContext, bot: Bot):
    team_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    await db.send_tournament_invite(data['inv_tournament_id'], team_id)
    team = await db.get_team(team_id)
    tournament = await db.get_tournament(data['inv_tournament_id'])
    await callback.message.edit_text(
        f"✅ Инвайт на **{tournament['name']}** отправлен **{team['name']}**",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )
    # Notify manager
    if team['manager_tg_id']:
        try:
            await bot.send_message(
                team['manager_tg_id'],
                f"🏆 Ваша команда **{team['name']}** получила инвайт на турнир **{tournament['name']}**!\n"
                f"Проверьте раздел инвайтов.",
                parse_mode="Markdown"
            )
        except:
            pass
    await state.clear()


# ========== DELETE TEAM ==========
@router.callback_query(F.data == "adm_delete_team")
async def adm_delete_team(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    teams = await db.get_all_teams()
    if not teams:
        await callback.answer("Нет команд", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"🗑 {t['name']}", callback_data=f"adm_delt_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите команду для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_delt_"))
async def adm_delt_confirm(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[-1])
    team = await db.get_team(team_id)
    await db.delete_team(team_id)
    await callback.message.edit_text(
        f"✅ Команда **{team['name']}** удалена",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )


# ========== DELETE PLAYER ==========
@router.callback_query(F.data == "adm_delete_player")
async def adm_delete_player(callback: CallbackQuery, state: FSMContext):
    if not admin_check(callback.from_user.id):
        return
    players = await db.get_all_players()
    if not players:
        await callback.answer("Нет игроков", show_alert=True)
        return
    buttons = [[InlineKeyboardButton(
        text=f"🗑 {p['nickname']} ({p['team_name'] or 'Free'})", callback_data=f"adm_delp_{p['id']}"
    )] for p in players[:30]]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await callback.message.edit_text("Выберите игрока:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_delp_"))
async def adm_delp_confirm(callback: CallbackQuery):
    player_id = int(callback.data.split("_")[-1])
    player = await db.get_player(player_id)
    await db.delete_player(player_id)
    await callback.message.edit_text(
        f"✅ Игрок **{player['nickname']}** удалён",
        reply_markup=admin_panel_kb(), parse_mode="Markdown"
    )


# ========== ALL PLAYERS / ALL TEAMS ==========
@router.callback_query(F.data == "adm_all_players")
async def adm_all_players(callback: CallbackQuery):
    if not admin_check(callback.from_user.id):
        return
    players = await db.get_all_players()
    if not players:
        await callback.answer("Нет игроков", show_alert=True)
        return
    text = "📊 **Все игроки:**\n\n"
    for p in players:
        team_info = p['team_name'] or "Free Agent"
        loan_info = ""
        if p['loaned_from_team_id']:
            loan_info = " (аренда)"
        bench_info = " [BENCH]" if p['is_benched'] else ""
        market_info = f" [MARKET ${p['market_price']:,.0f}]" if p['is_on_market'] else ""
        text += f"• **{p['nickname']}** — {team_info}{loan_info}{bench_info}{market_info} | ЗП: ${p['salary']:,.0f}\n"
    await callback.message.edit_text(text, reply_markup=admin_panel_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "adm_all_teams")
async def adm_all_teams(callback: CallbackQuery):
    if not admin_check(callback.from_user.id):
        return
    teams = await db.get_all_teams()
    if not teams:
        await callback.answer("Нет команд", show_alert=True)
        return
    text = "📊 **Все команды:**\n\n"
    for t in teams:
        mgr = f"@{t['manager_username']}" if t['manager_username'] else "Не назначен"
        text += f"• **{t['name']}** [{t['tag']}] | Бюджет: ${t['budget']:,.0f} | Менеджер: {mgr} | Сетап: {t['setup_type']}\n"
    await callback.message.edit_text(text, reply_markup=admin_panel_kb(), parse_mode="Markdown")