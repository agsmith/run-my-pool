"""
Constants for the comprehensive test suite.
"""

# Season structure
NFL_2025_WEEK_COUNT = 17
NFL_2025_GAME_COUNT = 256
NFL_2025_TEAM_COUNT = 32

# Week 1 kickoff times (UTC ISO strings)
WEEK1_THURSDAY_KICKOFF_UTC = "2025-09-05T00:20:00"  # DAL @ PHI (Thu 8:20pm ET)
WEEK1_FRIDAY_KICKOFF_UTC = "2025-09-06T00:00:00"  # KC @ LAC (Fri 8:00pm ET)
WEEK1_SUNDAY_LOCK_UTC = "2025-09-07T17:00:00"  # Pool lock_time: Sun 1pm ET
WEEK1_SUNDAY_SNF_UTC = "2025-09-08T00:20:00"  # Sunday Night Football
WEEK1_MONDAY_MNF_UTC = "2025-09-09T00:15:00"  # Monday Night Football

# Scale
SEASON_USER_COUNT = 750
SEASON_ENTRY_COUNT = 2000

# Entry distribution: first 500 users get 3 entries, last 250 get 2 entries
# 500 * 3 + 250 * 2 = 1500 + 500 = 2000
ENTRIES_PER_USER_FIRST_BATCH = 3
ENTRIES_PER_USER_SECOND_BATCH = 2
USER_FIRST_BATCH_SIZE = 500

# Cohort-based pick strategy elimination schedule
# Cohort 0: always picks home team (winners) — survives all 17 weeks
# Cohort 1: picks away team in weeks 1–2 (away = loser) — eliminated after week 2
# Cohort 2: picks away team in week 8 (away = loser) — eliminated after week 8
COHORT_1_ELIMINATED_AFTER_WEEK = 2
COHORT_2_ELIMINATED_AFTER_WEEK = 8

# All 32 NFL team abbreviations for the 2025 season
ALL_TEAM_ABBRVS = [
    "ARI",
    "ATL",
    "BAL",
    "BUF",
    "CAR",
    "CHI",
    "CIN",
    "CLE",
    "DAL",
    "DEN",
    "DET",
    "GB",
    "HOU",
    "IND",
    "JAX",
    "KC",
    "LAC",
    "LAR",
    "LV",
    "MIA",
    "MIN",
    "NE",
    "NO",
    "NYG",
    "NYJ",
    "PHI",
    "PIT",
    "SEA",
    "SF",
    "TB",
    "TEN",
    "WSH",
]
