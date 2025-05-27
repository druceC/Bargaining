from os import environ

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,  # Set to a positive value if paying participants
    doc=""
)

SESSION_CONFIGS = [
    {
        'name': 'fund_vanishes',  # Make sure this matches your actual app folder
        'display_name': "Fund Vanishes Experiment",
        # 'num_demo_participants': 3,  # Adjust based on your experiment
        'app_sequence': ['fund_vanishes'],  # Ensure only existing apps are listed
        # Re-direct participant back to the Prolific website for completion code
        'completionlink':'https://app.prolific.co/submissions/complete?cc=11111111'
    },
]

LANGUAGE_CODE = 'en'

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
OTREE_REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "user": "5000/minute",
    }
}

# Prevent WebSockets from closing prematurely
OTREE_WEBSOCKETS_PING_INTERVAL_SECONDS = 30
OTREE_WEBSOCKETS_CLOSE_TIMEOUT_SECONDS = 60


# ------------------------------------------------------------------------------------------------------------------------


# Prolific Integration
ROOMS = [
    dict(
        name='fund_vanishes',
        display_name='Fund Vanishes Experiment',
        # participant_label_file='_rooms/your_study.txt',
        # use_secure_urls=True,
    ),
    dict(
        name='fund_vanishes',
        display_name='Fund Vanishes Experiment',
        # participant_label_file='_rooms/your_study.txt',
        # use_secure_urls=True,
    ),
]