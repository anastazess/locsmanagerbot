import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            tag TEXT NOT NULL,
            budget REAL DEFAULT 0,
            manager_tg_id INTEGER,
            manager_username TEXT,
            setup_type TEXT DEFAULT 'AWP'
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            team_id INTEGER,
            role TEXT,
            salary REAL DEFAULT 0,
            is_benched INTEGER DEFAULT 0,
            is_on_market INTEGER DEFAULT 0,
            market_price REAL DEFAULT 0,
            loaned_from_team_id INTEGER,
            loan_salary REAL DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (loaned_from_team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            team_id INTEGER UNIQUE,
            salary REAL DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS transfer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            from_team_id INTEGER,
            to_team_id INTEGER,
            transfer_type TEXT,
            price REAL DEFAULT 0,
            salary REAL DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS trade_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            offered_player_id INTEGER,
            requested_player_id INTEGER,
            offered_salary REAL DEFAULT 0,
            requested_salary REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS loan_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            player_id INTEGER,
            loan_salary REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'upcoming'
        );

        CREATE TABLE IF NOT EXISTS tournament_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            team_id INTEGER,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );

        CREATE TABLE IF NOT EXISTS admin_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await db.commit()


# ============ TEAMS ============

async def create_team(name: str, tag: str, budget: float = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO teams (name, tag, budget) VALUES (?, ?, ?)",
            (name, tag, budget)
        )
        await db.commit()
        return cursor.lastrowid


async def get_team(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        return await cursor.fetchone()


async def get_team_by_manager(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM teams WHERE manager_tg_id = ?", (tg_id,))
        return await cursor.fetchone()


async def get_all_teams():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM teams")
        return await cursor.fetchall()


async def set_manager(team_id: int, tg_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE teams SET manager_tg_id = ?, manager_username = ? WHERE id = ?",
            (tg_id, username, team_id)
        )
        await db.commit()


async def set_team_budget(team_id: int, budget: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE teams SET budget = ? WHERE id = ?", (budget, team_id))
        await db.commit()


async def update_team_budget(team_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE teams SET budget = budget + ? WHERE id = ?", (amount, team_id))
        await db.commit()


async def set_team_setup(team_id: int, setup_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE teams SET setup_type = ? WHERE id = ?", (setup_type, team_id))
        await db.commit()


async def delete_team(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM players WHERE team_id = ?", (team_id,))
        await db.execute("DELETE FROM coaches WHERE team_id = ?", (team_id,))
        await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        await db.commit()


# ============ PLAYERS ============

async def create_player(nickname: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO players (nickname) VALUES (?)", (nickname,)
        )
        await db.commit()
        return cursor.lastrowid


async def get_player(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        return await cursor.fetchone()


async def get_team_players(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM players WHERE team_id = ?", (team_id,))
        return await cursor.fetchall()


async def get_active_roster(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM players WHERE team_id = ? AND is_benched = 0", (team_id,)
        )
        return await cursor.fetchall()


async def get_benched_players(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM players WHERE team_id = ? AND is_benched = 1", (team_id,)
        )
        return await cursor.fetchall()


async def get_free_agents():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM players WHERE team_id IS NULL AND is_on_market = 0"
        )
        return await cursor.fetchall()


async def get_market_players():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, t.name as team_name, t.tag as team_tag FROM players p "
            "LEFT JOIN teams t ON p.team_id = t.id WHERE p.is_on_market = 1"
        )
        return await cursor.fetchall()


async def add_player_to_team(player_id: int, team_id: int, salary: float = 0, role: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET team_id = ?, salary = ?, role = ?, is_on_market = 0, is_benched = 0 WHERE id = ?",
            (team_id, salary, role, player_id)
        )
        await db.commit()


async def remove_player_from_team(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET team_id = NULL, salary = 0, role = NULL, is_benched = 0, "
            "is_on_market = 0, loaned_from_team_id = NULL, loan_salary = 0 WHERE id = ?",
            (player_id,)
        )
        await db.commit()


async def set_player_role(player_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET role = ? WHERE id = ?", (role, player_id))
        await db.commit()


async def set_player_salary(player_id: int, salary: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE players SET salary = ? WHERE id = ?", (salary, player_id))
        await db.commit()


async def bench_player(player_id: int, benched: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET is_benched = ?, role = NULL WHERE id = ?",
            (1 if benched else 0, player_id)
        )
        await db.commit()


async def put_on_market(player_id: int, price: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET is_on_market = 1, market_price = ? WHERE id = ?",
            (price, player_id)
        )
        await db.commit()


async def remove_from_market(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET is_on_market = 0, market_price = 0 WHERE id = ?",
            (player_id,)
        )
        await db.commit()


async def set_player_loan(player_id: int, to_team_id: int, from_team_id: int, loan_salary: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE players SET team_id = ?, loaned_from_team_id = ?, loan_salary = ?, is_benched = 0 WHERE id = ?",
            (to_team_id, from_team_id, loan_salary, player_id)
        )
        await db.commit()


async def return_from_loan(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        player = await get_player(player_id)
        if player and player['loaned_from_team_id']:
            await db.execute(
                "UPDATE players SET team_id = ?, loaned_from_team_id = NULL, loan_salary = 0 WHERE id = ?",
                (player['loaned_from_team_id'], player_id)
            )
            await db.commit()


async def delete_player(player_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM players WHERE id = ?", (player_id,))
        await db.commit()


# ============ COACHES ============

async def create_coach(nickname: str, team_id: int = None, salary: float = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO coaches (nickname, team_id, salary) VALUES (?, ?, ?)",
            (nickname, team_id, salary)
        )
        await db.commit()
        return cursor.lastrowid


async def get_team_coach(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM coaches WHERE team_id = ?", (team_id,))
        return await cursor.fetchone()


async def get_free_coaches():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM coaches WHERE team_id IS NULL")
        return await cursor.fetchall()


async def assign_coach_to_team(coach_id: int, team_id: int, salary: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE coaches SET team_id = ?, salary = ? WHERE id = ?",
            (team_id, salary, coach_id)
        )
        await db.commit()


async def remove_coach_from_team(coach_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE coaches SET team_id = NULL, salary = 0 WHERE id = ?", (coach_id,)
        )
        await db.commit()


# ============ TRANSFER HISTORY ============

async def add_transfer_record(player_id, from_team_id, to_team_id, transfer_type, price=0, salary=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO transfer_history (player_id, from_team_id, to_team_id, transfer_type, price, salary) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (player_id, from_team_id, to_team_id, transfer_type, price, salary)
        )
        await db.commit()


async def get_transfer_history(team_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if team_id:
            cursor = await db.execute(
                "SELECT th.*, p.nickname as player_nick, "
                "t1.name as from_team_name, t2.name as to_team_name "
                "FROM transfer_history th "
                "LEFT JOIN players p ON th.player_id = p.id "
                "LEFT JOIN teams t1 ON th.from_team_id = t1.id "
                "LEFT JOIN teams t2 ON th.to_team_id = t2.id "
                "WHERE th.from_team_id = ? OR th.to_team_id = ? "
                "ORDER BY th.timestamp DESC LIMIT 20",
                (team_id, team_id)
            )
        else:
            cursor = await db.execute(
                "SELECT th.*, p.nickname as player_nick, "
                "t1.name as from_team_name, t2.name as to_team_name "
                "FROM transfer_history th "
                "LEFT JOIN players p ON th.player_id = p.id "
                "LEFT JOIN teams t1 ON th.from_team_id = t1.id "
                "LEFT JOIN teams t2 ON th.to_team_id = t2.id "
                "ORDER BY th.timestamp DESC LIMIT 50"
            )
        return await cursor.fetchall()


# ============ TRADE OFFERS ============

async def create_trade_offer(from_team_id, to_team_id, offered_player_id, requested_player_id,
                              offered_salary=0, requested_salary=0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO trade_offers (from_team_id, to_team_id, offered_player_id, "
            "requested_player_id, offered_salary, requested_salary) VALUES (?, ?, ?, ?, ?, ?)",
            (from_team_id, to_team_id, offered_player_id, requested_player_id,
             offered_salary, requested_salary)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_trades(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT to2.*, p1.nickname as offered_nick, p2.nickname as requested_nick, "
            "t1.name as from_team_name, t2.name as to_team_name "
            "FROM trade_offers to2 "
            "LEFT JOIN players p1 ON to2.offered_player_id = p1.id "
            "LEFT JOIN players p2 ON to2.requested_player_id = p2.id "
            "LEFT JOIN teams t1 ON to2.from_team_id = t1.id "
            "LEFT JOIN teams t2 ON to2.to_team_id = t2.id "
            "WHERE to2.to_team_id = ? AND to2.status = 'pending'",
            (team_id,)
        )
        return await cursor.fetchall()


async def get_trade(trade_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM trade_offers WHERE id = ?", (trade_id,))
        return await cursor.fetchone()


async def update_trade_status(trade_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE trade_offers SET status = ? WHERE id = ?", (status, trade_id)
        )
        await db.commit()


# ============ LOAN OFFERS ============

async def create_loan_offer(from_team_id, to_team_id, player_id, loan_salary) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO loan_offers (from_team_id, to_team_id, player_id, loan_salary) "
            "VALUES (?, ?, ?, ?)",
            (from_team_id, to_team_id, player_id, loan_salary)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_loans_for_team(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT lo.*, p.nickname as player_nick, "
            "t1.name as from_team_name, t2.name as to_team_name "
            "FROM loan_offers lo "
            "LEFT JOIN players p ON lo.player_id = p.id "
            "LEFT JOIN teams t1 ON lo.from_team_id = t1.id "
            "LEFT JOIN teams t2 ON lo.to_team_id = t2.id "
            "WHERE lo.to_team_id = ? AND lo.status = 'pending'",
            (team_id,)
        )
        return await cursor.fetchall()


async def get_loan(loan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM loan_offers WHERE id = ?", (loan_id,))
        return await cursor.fetchone()


async def update_loan_status(loan_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE loan_offers SET status = ? WHERE id = ?", (status, loan_id)
        )
        await db.commit()


# ============ TOURNAMENTS ============

async def create_tournament(name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tournaments (name) VALUES (?)", (name,)
        )
        await db.commit()
        return cursor.lastrowid


async def get_tournaments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tournaments")
        return await cursor.fetchall()


async def get_tournament(t_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tournaments WHERE id = ?", (t_id,))
        return await cursor.fetchone()


async def send_tournament_invite(tournament_id: int, team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tournament_invites (tournament_id, team_id) VALUES (?, ?)",
            (tournament_id, team_id)
        )
        await db.commit()


async def get_team_invites(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT ti.*, t.name as tournament_name FROM tournament_invites ti "
            "JOIN tournaments t ON ti.tournament_id = t.id "
            "WHERE ti.team_id = ? AND ti.status = 'pending'",
            (team_id,)
        )
        return await cursor.fetchall()


async def update_invite_status(invite_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tournament_invites SET status = ? WHERE id = ?", (status, invite_id)
        )
        await db.commit()


# ============ SALARY DEDUCTION ============

async def deduct_all_salaries():
    """Снимает зарплаты всех игроков и тренеров с бюджетов команд."""
    results = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        teams = await (await db.execute("SELECT * FROM teams")).fetchall()
        for team in teams:
            team_id = team['id']
            total_salary = 0

            players = await (await db.execute(
                "SELECT * FROM players WHERE team_id = ?", (team_id,)
            )).fetchall()
            for p in players:
                if p['loaned_from_team_id']:
                    total_salary += p['loan_salary']
                else:
                    total_salary += p['salary']

            coach = await (await db.execute(
                "SELECT * FROM coaches WHERE team_id = ?", (team_id,)
            )).fetchone()
            if coach:
                total_salary += coach['salary']

            await db.execute(
                "UPDATE teams SET budget = budget - ? WHERE id = ?",
                (total_salary, team_id)
            )
            results.append({
                'team_name': team['name'],
                'total_salary': total_salary,
                'new_budget': team['budget'] - total_salary
            })
        await db.commit()
    return results


# ============ ALL PLAYERS ============

async def get_all_players():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT p.*, t.name as team_name FROM players p LEFT JOIN teams t ON p.team_id = t.id"
        )
        return await cursor.fetchall()