NUM_PLAYERS = 5
NUM_PICKS = 11

PROJECT_ID = "168510284961"

TELEGRAM_CHAT_ID = -4673138846

TELEGRAM_URL = "https://api.telegram.org/bot7829344666:AAGLCcj0F4lIvpiRGvyBsIE0gCiv_skFypI/sendMessage"

API_URL = "https://v3.football.api-sports.io/"

# This are just to note, not used in the code
YEAR = 2022

# These are just to note, they are not used in the code
PREMIER_LEAGUE_LEAGUE_ID = 39
WORLD_CUP_LEAGUE_ID = 1

ALL_EVENTS = [
    ("Goal", "Goalkeeper", 10),
    ("Goal", "Defender", 7),
    ("Goal", "Midfielder", 6),
    ("Goal", "Attacker", 5),
    ("Assist", "Goalkeeper", 3),
    ("Assist", "Defender", 3),
    ("Assist", "Midfielder", 3),
    ("Assist", "Attacker", 3),
    ("Clean Sheet", "Goalkeeper", 5),
    ("Clean Sheet", "Defender", 4),
    ("Penalty", "Goalkeeper", 3),
    ("Penalty", "Defender", 2),
    ("Penalty", "Midfielder", 2),
    ("Penalty", "Attacker", 2),
    ("Penalty Save", "Goalkeeper", 2),
    ("Penalty Save", "Defender", 10),
    ("Penalty Save", "Midfielder", 10),
    ("Penalty Save", "Attacker", 10),
    ("Own Goal", "Goalkeeper", -1),
    ("Own Goal", "Defender", -2),
    ("Own Goal", "Midfielder", -2),
    ("Own Goal", "Attacker", -2),
    ("Missed Penalty", "Goalkeeper", -2),
    ("Missed Penalty", "Defender", -2),
    ("Missed Penalty", "Midfielder", -2),
    ("Missed Penalty", "Attacker", -2),
    ("Red Card", "Goalkeeper", -2),
    ("Red Card", "Defender", -2),
    ("Red Card", "Midfielder", -2),
    ("Red Card", "Attacker", -2)
]

MAX_PICKS = {
    "Goalkeeper": 1,
    "Defender": 5,
    "Midfielder": 5,
    "Attacker": 3
}

MIN_PICKS = {
    "Goalkeeper": 1,
    "Defender": 3,
    "Midfielder": 3,
    "Attacker": 1
}

GAMEWEEKS = {
    'Group Stage - 1': 1, 
    'Group Stage - 2': 2, 
    'Group Stage - 3': 3,
    'Round of 16': 4, 
    'Quarter-finals': 5, 
    'Semi-finals': 6, 
    '3rd Place Final': 7,
    'Final': 8
}