from fastapi import APIRouter
import users
import pools
import entries
import picks
import auth
import audit
import message_board
import teams
import schedule
import admin
import rules
import billing
import platform_admin_api

router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(pools.router)
router.include_router(entries.router)
router.include_router(picks.router)
router.include_router(audit.router)
router.include_router(message_board.router)
router.include_router(teams.router, prefix="/teams", tags=["teams"])
router.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
router.include_router(admin.router)
router.include_router(rules.router)
router.include_router(billing.router)
router.include_router(platform_admin_api.router)
