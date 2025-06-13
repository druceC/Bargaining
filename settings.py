from os import environ

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,  # Set to a positive value if paying participants
    doc=""
)

SESSION_CONFIGS = [
    {
        'name': 'experiment',                        # App folder
        'display_name': "Fund Vanishes Experiment",
        'num_demo_participants': 36,                    
        # 'app_sequence': ['filter_app','fund_vanishes'],              # Ensure only existing apps are listed
        'app_sequence':['fund_vanishes'],
        # 'group_by_arrival_time': True,                  # Enable dynamic grouping
        'study_id': 'Study001',
        'player_session_id': 'Pilot1',
    },
]

LANGUAGE_CODE = 'en'

DEBUG = False

REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False  # Set to True if using points-based rewards

# SESSION_FIELDS = []
PARTICIPANT_FIELDS = ['final_payment','next_period','skip_this_oTree_round','periods','rounds']
SESSION_FIELDS = ["num_players","list_players_waiting","list_players_session", "number_oTree_round_matching","finish"]

# Admin settings
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD', 'password123')  # Change this for security

DEMO_PAGE_INTRO_HTML = """ 
Welcome to the Fund Vanishes Experiment!
"""

# oTree Core Settings
SECRET_KEY = 'your_secret_key_here'

INSTALLED_APPS = ['otree']

# Storage Settings
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    }
}

# Use InMemoryChannelLayer instead of Redis to avoid WebSocket errors
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Ensure ASGI is correctly set up
WSGI_APPLICATION = 'otree.asgi.application'
ASGI_APPLICATION = 'otree.asgi.application'

# Increase WebSocket timeout settings
# OTREE_REST_FRAMEWORK = {
#     "DEFAULT_THROTTLE_RATES": {
#         "user": "5000/minute",
#     }
# }

# Prevent WebSockets from closing prematurely
# OTREE_WEBSOCKETS_PING_INTERVAL_SECONDS = 30
# OTREE_WEBSOCKETS_CLOSE_TIMEOUT_SECONDS = 60

# Timeout
# Timeout duration in seconds
# 'Proposal': {
#     'timeout_seconds': 10,
# }

# # Timeout duration in seconds
# 'Voting': {
#     'timeout_seconds': 5,
# }
