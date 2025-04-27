# fund_vanishes/utils.py

import csv
import datetime
from django.core.files.storage import default_storage
from pathlib import Path

# CSV files for storage
INTRO_CSV = Path(__file__).resolve().parent / 'meta_data.csv'
GAME_CSV = Path(__file__).resolve().parent / 'game_data.csv'
SURVEY_CSV = Path(__file__).resolve().parent / 'survey_data.csv'
EARNINGS_CSV = Path(__file__).resolve().parent / 'earnings_data.csv'
LOGS_CSV = Path(__file__).resolve().parent / 'logs_data.csv'

# META DATA  ------------------------------------------------------------------------------

# Ensure headers exist for is_priming CSV
def ensure_intro_headers():
    if not default_storage.exists(INTRO_CSV):
        with default_storage.open(INTRO_CSV, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", "Session_Code", "Participant_ID", "Group_ID", "Prolific_ID", "Period", "Player_ID", "Treatment"
            ])

# Store is_priming info in a consistent CSV format
def store_intro(player):
    ensure_intro_headers()

    with default_storage.open(INTRO_CSV, mode='a') as file:
        writer = csv.writer(file)

        treatment = "baseline"
        if player.is_priming == 1:
            treatment = "priming"

        writer.writerow([
            datetime.datetime.now().isoformat(),                # Timestamp
            player.session.code,                                # Session Code
            player.participant.id_in_session,                   # Participant ID
            player.group.id_in_subsession,                      # Group ID
            player.prolific_id,
            # player.round_number,                              # Round Number
            player.participant.vars.get('periods_played', 0),   # Period/Game
            player.id_in_group,                                 # Player ID
            treatment                                           # Treatment
        ])

# GAME DATA ------------------------------------------------------------------------------

def ensure_csv_headers():
    # Creates the CSV file with headers if it does not exist
    if not default_storage.exists(GAME_CSV):
        with default_storage.open(GAME_CSV, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", "Session_Code", "Participant_ID", "Group_ID", "Treatment", "Round", "Page", "Action", "Value"
            ])

# Logs participant actions and decisions into a CSV file.
def store_decision(player, page_name, action, data_dict):
    
    # Ensure headers exist
    ensure_csv_headers()  

    with default_storage.open(GAME_CSV, mode='a') as file:
        writer = csv.writer(file)

        treatment = "baseline"
        if player.is_priming == 1:
            treatment = "priming"

        for field, value in data_dict.items():
            writer.writerow([
                datetime.datetime.now().isoformat(),                # Timestamp
                player.session.code,                                # Session Code
                player.participant.id_in_session,                   # Participant ID
                player.group.id_in_subsession,                      # Group ID
                treatment,                                          # Treatment
                player.round_number,                                # Round number
                # player.participant.vars.get('periods_played', 0),   # Period/Game of play
                page_name,                                          # Page name
                action,                                             # Action (e.g., "Submitted Proposal", "Voted")
                value                                               # Vote on Proposal
            ])

# SURVEY DATA  ------------------------------------------------------------------------------

def ensure_survey_csv_headers():
    """Creates the survey CSV file with headers if it does not exist."""
    if not default_storage.exists(SURVEY_CSV):
        with default_storage.open(SURVEY_CSV, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Session_Code", "Participant_ID", "Group_ID", "Treatment", "Round", "Survey Page", "Question", "Response"])

def store_survey_response(player, page_name, form_fields):
    """Logs participant survey responses into a separate CSV file."""
    ensure_survey_csv_headers()  # Ensure headers exist

    with default_storage.open(SURVEY_CSV, mode='a') as file:  # Use 'a' to append responses
        writer = csv.writer(file)
    
        treatment = "baseline"
        if player.is_priming == 1:
            treatment = "priming"

        for field in form_fields:
            response = getattr(player, field, None)  # Get survey response
            
            # Skip questions that haven't been answered
            if response is None:
                continue

            writer.writerow([
                datetime.datetime.now().isoformat(),  # Timestamp
                player.session.code,                  # Session Code
                player.participant.id_in_session,     # Participant ID
                player.group.id_in_subsession,        # Group ID
                treatment,                            # Treatment
                player.round_number,                  # Round number
                page_name,                            # Survey page name
                field,                                # Question (form field)
                response                              # Response value
            ])

# EARNINGS DATA  ------------------------------------------------------------------------------

def ensure_earnings_csv_headers():
    """Creates the earnings CSV file with headers if it does not exist."""
    if not default_storage.exists(FILES["earnings"]):
        with default_storage.open(FILES["earnings"], mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp",
                "Session_Code",
                "Participant_ID",
                "Selected_Periods",
                "Final_Payment",
                "Total_Bonus"
            ])

def store_earnings(player, earnings_data):
    """Logs final earnings and selected periods for a participant."""
    ensure_earnings_csv_headers()  # Ensure headers exist

    with default_storage.open(FILES["earnings"], mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.datetime.now().isoformat(),                                # Timestamp
            player.session.code,                                                # Session Code
            player.participant.id_in_session,                                   # Participant ID
            ",".join(map(str, earnings_data.get("selected_periods", []))),      # Selected Periods (comma-separated)
            earnings_data.get("final_payment", 0),                              # Final Payment
            earnings_data.get("total_bonus", 0)                                 # Total Bonus
        ])


# LOGS, DROPOUTS ------------------------------------------------------------------------------

