from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb(is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="👤 Моя команда", callback_data="my_team")],
        [InlineKeyboardButton(text="🏪 Маркет игроков", callback_data="market")],
        [InlineKeyboardButton(text="📋 Свободные агенты", callback_data="free_agents")],
        [InlineKeyboardButton(text="🔄 Трейды (входящие)", callback_data="incoming_trades")],
        [InlineKeyboardButton(text="📥 Аренды (входящие)", callback_data="incoming_loans")],
        [InlineKeyboardButton(text="📜 История трансферов", callback_data="transfer_history")],
        [InlineKeyboardButton(text="🏆 Инвайты на турниры", callback_data="tournament_invites")],
        [InlineKeyboardButton(text="👀 Просмотр команд", callback_data="browse_teams")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_btn(callback_data="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data)]
    ])


def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать команду", callback_data="adm_create_team")],
        [InlineKeyboardButton(text="➕ Создать игрока", callback_data="adm_create_player")],
        [InlineKeyboardButton(text="➕ Создать тренера", callback_data="adm_create_coach")],
        [InlineKeyboardButton(text="👤 Назначить менеджера", callback_data="adm_set_manager")],
        [InlineKeyboardButton(text="💰 Установить бюджет", callback_data="adm_set_budget")],
        [InlineKeyboardButton(text="📌 Добавить игрока в команду", callback_data="adm_add_player_team")],
        [InlineKeyboardButton(text="📌 Назначить тренера команде", callback_data="adm_assign_coach")],
        [InlineKeyboardButton(text="💸 Снять зарплаты", callback_data="adm_deduct_salaries")],
        [InlineKeyboardButton(text="🏆 Создать турнир", callback_data="adm_create_tournament")],
        [InlineKeyboardButton(text="📨 Отправить инвайт на турнир", callback_data="adm_send_invite")],
        [InlineKeyboardButton(text="🗑 Удалить команду", callback_data="adm_delete_team")],
        [InlineKeyboardButton(text="🗑 Удалить игрока", callback_data="adm_delete_player")],
        [InlineKeyboardButton(text="📊 Все игроки", callback_data="adm_all_players")],
        [InlineKeyboardButton(text="📊 Все команды", callback_data="adm_all_teams")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])


SETUP_ROLES = {
    "AWP": ["AWP", "Entry", "Closer", "Support", "IGL"],
    "AWP-IGL": ["AWP-IGL", "Entry", "Entry-2", "Closer", "Support"],
    "NO AWP": ["IGL", "Entry", "Entry-2", "Closer", "Support"],
}


def setup_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="AWP", callback_data="setup_AWP")],
        [InlineKeyboardButton(text="AWP-IGL", callback_data="setup_AWP-IGL")],
        [InlineKeyboardButton(text="NO AWP", callback_data="setup_NO AWP")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")],
    ])


def team_manage_kb(team_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Ростер", callback_data=f"roster_{team_id}")],
        [InlineKeyboardButton(text="🪑 Бенч", callback_data=f"bench_{team_id}")],
        [InlineKeyboardButton(text="🎯 Сетап (роли)", callback_data=f"setup_{team_id}")],
        [InlineKeyboardButton(text="🔄 Сменить тип сетапа", callback_data="change_setup")],
        [InlineKeyboardButton(text="🏪 Выставить игрока на маркет", callback_data="put_market")],
        [InlineKeyboardButton(text="❌ Снять с маркета", callback_data="remove_market")],
        [InlineKeyboardButton(text="🪑 Забенчить игрока", callback_data="bench_player")],
        [InlineKeyboardButton(text="✅ Вернуть с бенча", callback_data="unbench_player")],
        [InlineKeyboardButton(text="🔁 Предложить трейд", callback_data="offer_trade")],
        [InlineKeyboardButton(text="📥 Предложить аренду", callback_data="offer_loan")],
        [InlineKeyboardButton(text="↩️ Вернуть с аренды", callback_data="return_loan")],
        [InlineKeyboardButton(text="🚪 Отпустить игрока", callback_data="release_player")],
        [InlineKeyboardButton(text="💰 Изменить зарплату", callback_data="change_salary")],
        [InlineKeyboardButton(text="🏋️ Тренер", callback_data=f"coach_{team_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])


def confirm_kb(action: str, item_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="my_team"),
        ]
    ])