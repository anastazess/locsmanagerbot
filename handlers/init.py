from handlers.start import router as start_router
from handlers.admin import router as admin_router
from handlers.team import router as team_router
from handlers.market import router as market_router
from handlers.transfers import router as transfers_router
from handlers.browse import router as browse_router

all_routers = [start_router, admin_router, team_router, market_router, transfers_router, browse_router]