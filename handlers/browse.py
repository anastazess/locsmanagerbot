from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import database as db
from keyboards import back_btn

router = Router()


@router.callback_query(F.data == "browse_teams")
async def browse_teams(callback: CallbackQuery):
    teams = await db.get_all_teams()
    if not teams:
        await callback.message.edit_text("📭 Нет команд.", reply_markup=back_btn())
        return
    buttons = [[InlineKeyboardButton(
        text=f"{t['name']} [{t['tag']}]", callback_data=f"view_team_{t['id']}"
    )] for t in teams]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text("👀 **Все команды:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("view_team_"))
async def view_team(callback: CallbackQuery):
    team_id = int(callback.data.split("_")[-1])
    team = await db.get_team(team_id)
    if not team:
        await callback.answer("Команда не найдена", show_alert=True)
        return

    my_team = await db.get_team_by_manager(callback.from_user.id)
    is_own = my_team and my_team['id'] == team_id

    players = await db.get_team_players(team_id)
    active = [p for p in players if not p['is_benched']]
    benched = [p for p in players if p['is_benched']]
    coach = await db.get_team_coach(team_id)

    text = f"👀 **{team['name']}** [{team['tag']}]\n"
    text += f"🎯 Сетап: **{team['setup_type']}**\n"
    mgr = f"@{team['manager_username']}" if team['manager_username'] else "Не назначен"
    text += f"👤 Менеджер: {mgr}\n"

    if is_own:
        text += f"💰 Бюджет: **${team['budget']:,.0f}**\n"

    text += f"\n**Ростер ({len(active)}/5):**\n"
    for p in active:
        role = p['role'] or "—"
        loan = " (аренда)" if p['loaned_from_team_id'] else ""
        if is_own:
            sal = p['loan_salary'] if p['loaned_from_team_id'] else p['salary']
            text += f"  • {p['nickname']} | {role} | ${sal:,.0f}{loan}\n"
        else:
            text += f"  • {p['nickname']} | {role}{loan}\n"

    if benched:
        text += f"\n**Бенч ({len(benched)}):**\n"
        for p in benched:
            if is_own:
                sal = p['loan_salary'] if p['loaned_from_team_id'] else p['salary']
                text += f"  • {p['nickname']} | ${sal:,.0f}\n"
            else:
                text += f"  • {p['nickname']}\n"

    if coach:
        if is_own:
            text += f"\n🏋️ **Тренер:** {coach['nickname']} | ${coach['salary']:,.0f}\n"
        else:
            text += f"\n🏋️ **Тренер:** {coach['nickname']}\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_btn("browse_teams"),
        parse_mode="Markdown"
    )