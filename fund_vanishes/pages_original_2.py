# Handle logic for experiment pages (welcome, proposal, voting, results)

from otree.api import *
from .models import Player
# from .survey import Player
# from .survey import page_sequence as survey_pages
from .models import Constants
from .models import Group
from .models import Subsession
from otree.api import BaseSubsession
from pathlib import Path
import random
import datetime
import json
import csv
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fund_vanishes.settings")
from django.core.files.storage import default_storage

# Set-up Questions
NUM_ROUNDS = 5
TIME_LIMIT = 60                  # Time limit per round in seconds

# Variables for Progress Bar 
INTRO_QUESTIONS = 4
SURVEY_PAGES = 11

# CSV files (saved in the same directory as pages.py)
CSV_FILE_PATH = Path(__file__).resolve().parent / 'game_decisions.csv'
SURVEY_CSV_FILE_PATH = Path(__file__).resolve().parent / 'survey_data.csv'
INTRO_CSV = Path(__file__).resolve().parent / 'is_priming_log.csv'


# -------------------------------------------------------------------

# INTRO QUESTIONS STORAGE

# Ensure headers exist for is_priming CSV
def ensure_csv_headers():
    if not default_storage.exists(INTRO_CSV):
        with default_storage.open(INTRO_CSV, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", "Participant_ID", "Group_ID", "Round", "Period", "Player_ID", "Group_ID", "Field", "Value"
            ])

# Store is_priming info in a consistent CSV format
def store_intro(player):
    ensure_intro_headers()

    with default_storage.open(INTRO_CSV, mode='a') as file:
        writer = csv.writer(file)

        writer.writerow([
            datetime.datetime.now().isoformat(),          # Timestamp
            player.participant.id_in_session,             # Participant ID
            player.round_number,                          # Round number
            player.participant.vars.get('periods_played', 0),  # Period/Game
            player.id_in_group,                           # Player ID
            player.group.id_in_subsession,                # Group ID
            "is_priming",                                 # Field
            player.is_priming                             # Value
        ])

# GAME DATA STORAGE

def ensure_csv_headers():
    # Creates the CSV file with headers if it does not exist
    if not default_storage.exists(CSV_FILE_PATH):
        with default_storage.open(CSV_FILE_PATH, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", "Participant_ID", "Group_ID", "Round", "Period", "Page", "Action", "Field", "Value"
            ])

# Logs participant actions and decisions into a CSV file.
def store_decision(player, page_name, action, data_dict):
    
    # Ensure headers exist
    ensure_csv_headers()  

    with default_storage.open(CSV_FILE_PATH, mode='a') as file:
        writer = csv.writer(file)

        for field, value in data_dict.items():
            writer.writerow([
                datetime.datetime.now().isoformat(),  # Timestamp
                player.participant.id_in_session,     # Participant ID
                player.group.id_in_subsession,        # Group ID
                player.round_number,                  # Round number
                player.participant.vars.get('periods_played', 0),  # Period/Game of play
                page_name,                            # Page name
                action,                               # Action (e.g., "Submitted Proposal", "Voted")
                field,                                # Field Name
                value                                 # Value (Decision made)
            ])

# PRIMING / BASELINE DATA STORAGE

def ensure_survey_csv_headers():
    """Creates the survey CSV file with headers if it does not exist."""
    if not default_storage.exists(SURVEY_CSV_FILE_PATH):
        with default_storage.open(SURVEY_CSV_FILE_PATH, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Participant_ID", "Group_ID", "Round", "Survey Page", "Question", "Response"])

def store_survey_response(player, page_name, form_fields):
    """Logs participant survey responses into a separate CSV file."""
    ensure_survey_csv_headers()  # Ensure headers exist

    with default_storage.open(SURVEY_CSV_FILE_PATH, mode='a') as file:  # Use 'a' to append responses
        writer = csv.writer(file)

        for field in form_fields:
            response = getattr(player, field, None)  # Get survey response
            
            # Skip questions that haven't been answered
            if response is None:
                continue

            writer.writerow([
                datetime.datetime.now().isoformat(),  # Timestamp
                player.participant.id_in_session,     # Participant ID
                player.group.id_in_subsession,        # Group ID
                player.round_number,                  # Round number
                page_name,                            # Survey page name
                field,                                # Question (form field)
                response                              # Response value
            ])

# -------------------------------------------------------------------

# SURVEY DATA STORAGE

def ensure_survey_csv_headers():
    """Creates the survey CSV file with headers if it does not exist."""
    if not default_storage.exists(SURVEY_CSV_FILE_PATH):
        with default_storage.open(SURVEY_CSV_FILE_PATH, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Participant_ID", "Group_ID", "Round", "Survey Page", "Question", "Response"])

def store_survey_response(player, page_name, form_fields):
    """Logs participant survey responses into a separate CSV file."""
    ensure_survey_csv_headers()  # Ensure headers exist

    with default_storage.open(SURVEY_CSV_FILE_PATH, mode='a') as file:  # Use 'a' to append responses
        writer = csv.writer(file)

        for field in form_fields:
            response = getattr(player, field, None)  # Get survey response
            
            # Skip questions that haven't been answered
            if response is None:
                continue

            writer.writerow([
                datetime.datetime.now().isoformat(),  # Timestamp
                player.participant.id_in_session,     # Participant ID
                player.group.id_in_subsession,        # Group ID
                player.round_number,                  # Round number
                page_name,                            # Survey page name
                field,                                # Question (form field)
                response                              # Response value
            ])

# -------------------------------------------------------------------

# First screen where participants are welcomed and given general instructions
class WelcomePage(Page):
    def is_displayed(self):
        return self.round_number == 1

# Explain experiment instructions
class ExperimentInstructions(Page):
    def is_displayed(self):
        return self.round_number == 1

# Welcome Page to Survey
class ProlificID(Page):
    def is_displayed(self):
        if 'surveyStep' not in self.participant.vars:
            self.participant.vars['surveyStep'] = 0
        return self.round_number == 1
        # return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def before_next_page(self):
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


# Welcome Page to Survey
class IntroQuestions(Page):
    form_model = 'player'
    form_fields = ['prolific_id']

    def is_displayed(self):
        if 'surveyStep' not in self.participant.vars:
            self.participant.vars['surveyStep'] = 0
        return self.round_number == 1
        # return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def before_next_page(self):
        store_survey_response(self.player, "ProlificID", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


# Explain experiment instructions
class SampleInstructions(Page):
    def is_displayed(self):
        return self.round_number == 1

# Mini quiz to ensure understanding before starting
class QuizPage(Page):
    form_model = 'player'
    form_fields = ['q1_quiz', 'q2_quiz', 'q3_quiz']

    def is_displayed(self):
        # Ensures that the quiz is only displayed in the first round
        return self.player.round_number == 1

    def error_message(self, values):
        """
        Validates quiz answers and provides feedback on incorrect responses.
        Also increments failed attempt counters.
        """
        solutions = dict(q1_quiz=2, q2_quiz=1, q3_quiz=2)  # Correct answers for each question
        
        # Generates error messages for incorrect answers
        errors = {field: 'Incorrect answer' for field in solutions if values.get(field) != solutions[field]}
        
        # Track individual failed attempts
        if values.get("q1_quiz") != 2:
            self.player.q1_num_failed_attempts += 1
        if values.get("q2_quiz") != 1:
            self.player.q2_num_failed_attempts += 1
        if values.get("q3_quiz") != 2:
            self.player.q2_num_failed_attempts += 1
        
        # Track total failed attempts across all questions
        if errors:
            self.player.total_num_failed_attempts += 1
            return errors  # Returns error messages to be displayed to the participant
    
    # Redirect to failed.html if player fails quiz 3 times, otherwise go to waiting page
    def before_next_page(self):
        if self.player.total_num_failed_attempts >= 3:
            self.participant.vars['redirect_to_failed'] = True  

# ---------------------------------------------------------------------------------------------------

# PRELIMINARY QUESTIONS


class Nationality(Page):
    form_model = 'player'
    form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit', 'primlang']

    # @staticmethod
    def is_displayed(self):
        return True and self.round_number == 1

    def vars_for_template(self):
        return {
            "survey_step": 1,
            "total_steps": INTRO_QUESTIONS
        }

    def before_next_page(self):
        # Record responses
        store_survey_response(self.player, "Nationality", self.form_fields)

        if self.player.spbrn != '2':        # If not 'No'
            self.player.cntbrn = ''         # Clear the field
        
        if self.player.spcit != '2':        # If not 'No'
            self.player.other_cit = ''      # Clear the field
    

class Education(Page):
    form_model = 'player'
    form_fields = ['degree']
     
    def is_displayed(self):
        return True and self.round_number == 1

    def vars_for_template(self):
        return {
            "survey_step": 2,
            "total_steps": INTRO_QUESTIONS  # Adjust based on survey length
        }

    def before_next_page(self):
        # Store responses
        store_survey_response(self.player, "Education", self.form_fields)


class Gender(Page):
    form_model = 'player'
    form_fields = ['sex', 'gen', 'other_gender', 'gen_cgi',]

    # Gender choices mapping
    GENDER_CHOICES = {
        "1": "man or male",
        "2": "woman or female",
        "3": "non-binary or genderqueer",
        "4": "I use a different term",
        "5": "I prefer not to answer"
    }

    def is_displayed(self):
        return True and self.round_number == 1
    
    def vars_for_template(self):
        return {
            "survey_step": 3,
            "total_steps": INTRO_QUESTIONS 
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Gender", self.form_fields)
        
        # If user didn't select "I use a different term"
        if self.player.gen != '4':
            self.player.other_gender = ''
        
        # Use the provided gender label or a custom one if 'gen' == '4'
        if str(self.player.gen).strip() == "4":
            self.participant.vars["selected_gender"] = self.player.other_gender  # Custom term
        else:
            self.participant.vars["selected_gender"] = self.GENDER_CHOICES.get(str(self.player.gen), "Not specified")


class Income(Page):
    form_model = 'player'
    form_fields = ['inc','inc_hh']
    
    def is_displayed(self):
        return True and self.round_number == 1
    
    def vars_for_template(self):
        return {
            "survey_step": 4,
            "total_steps": INTRO_QUESTIONS  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Income", self.form_fields)


# ---------------------------------------------------------------------------------------------------

# Synchronization page that ensures all players are randomly regrouped each period
class SyncTop(WaitPage):

    # Ensures that all groups wait before proceeding
    wait_for_all_groups = True  
    body_text = "Kindly wait to be randomly matched with other participants."

    #  Ensure page is only displayed for players who still need to play 5 rounds
    def is_displayed(self):
        return self.participant.vars.get('periods_played', 0) < Constants.no_periods  

    # Regroups players randomly at the start of each period and ensures each player participates for exactly 5 periods
    @staticmethod
    def after_all_players_arrive(subsession):

        # Access session data
        session = subsession.session

        # Check if players have reached their 5-period limit
        for p in subsession.get_players():
            if 'periods_played' not in p.participant.vars:
                p.participant.vars['periods_played'] = -1  # Initialize period count

            if 'next_period' not in p.participant.vars:
                p.participant.vars['next_period'] = False

        # Only regroup players who haven't played 5 periods
        active_players = [p for p in subsession.get_players() if p.participant.vars['periods_played'] < Constants.no_periods]

        if active_players:
            subsession.group_randomly()
            for p in active_players:
                p.participant.vars['periods_played'] += 1  # Increment period count
                p.participant.vars['next_period'] = True   # ✅ Ensure the next period flag is updated

        print(f"\n[DEBUG] Periods played: {[(p.id_in_group, p.participant.vars['periods_played']) for p in subsession.get_players()]}\n")


    # Handles actions before moving to the next page, including timeout handling. 
    @staticmethod
    def before_next_page(player, timeout_happened):

        # Access participant data
        participant = player.participant

        # If a player times out, mark them as a dropout
        if timeout_happened:
            participant.is_dropout = True   # Mark participant as dropped out
            player.dropout = True           # Mark player as dropped out


class CalculatePage(Page):
    # Determine whether this page is displayed for a participant
    def is_displayed(self):
        for player in self.subsession.get_players():
            next_period = self.player.participant.vars.get('next_period', False)
            skip_round = self.player.participant.vars.get('skip_this_oTree_round', False)
            
            return next_period and not skip_round

    # Handles logic before transitioning to the next page
    def before_next_page(self):
    # def before_next_page(player, timeout_happened):
        # Reference to the player's group
        group = self.player.group

        # ---------------------
        
        # # Initialize period count at the start of the first round
        # if self.player.round_number == 1:
        #     self.player.participant.periods = 0
        
        # # Increment the participant's period count
        # self.player.participant.periods += 1
        # group.current_period = self.player.participant.periods  # Update group's current period
        
        # ---------------------

        if 'periods' not in self.player.participant.vars:
            self.player.participant.vars['periods'] = 0  # Ensure it starts from 0

        # Increment AFTER checking initialization
        self.player.participant.vars['periods'] += 1

        # Update the group's period tracker
        group.current_period = self.player.participant.vars['periods']

        # ---------------------

        # Reference to the participant object
        participant = self.player.participant

        # # Mark the participant as a dropout if they exceeded the timeout
        # if timeout_happened:
        #     participant.is_dropout = True
        #     self.player.dropout = True

    # @staticmethod
    # def get_timeout_seconds(self):
    #     participant = self.player.participant
    #     if participant.is_dropout:
    #         return 1  # instant timeout, 1 second
    #     else:
    #         return C.TIMELIMIT * 3

# Page shown while waiting for other participants to join and complete mini assessment
class WaitingPage(WaitPage):
    body_text = "Kindly wait to be randomly matched with other participants."

    # def after_all_players_arrive(self):
    #     """Assigns one proposer and two voters randomly"""
    #     players = self.group.get_players()
    #     proposer = random.choice(players)  # Select one player as proposer
    #     proposer.player_role = "Proposer"

    #     for p in players:
    #         if p != proposer:
    #             p.player_role = "Voter"  # The remaining players are voters

# Displays failure message if the player fails the quiz after 3 attempts
class FailedPage(Page):
    def is_displayed(self):
        return self.participant.vars.get('redirect_to_failed', False)  

# Submit Proposal Page: All players propose an allocation, then store
class ProposerPage(Page):
    # Store data collected in this page at the group level
    form_model = 'group'  
    # Collect allocation values from participants
    form_fields = ['s1', 's2', 's3']  

    # Provide player ID for template rendering
    def vars_for_template(self):
        return {'id': self.player.id_in_group}

    # Store the proposer's id and submitted allocation before proceeding
    def before_next_page(self):
        proposer_id = self.player.id_in_group  
        allocation = {
            "s1":self.group.s1,
            "s2":self.group.s2,
            "s3":self.group.s3
        }
        # Store the proposal in the group for later voting
        self.group.store_proposal(proposer_id, allocation)

        # Store the proposal to csv before selection
        store_decision(self.player, "ProposerPage", "Submitted Proposal", allocation)

        # Debugging print
        proposals = json.loads(self.group.all_proposals_str)
        print(f"\n[DEBUG] Current stored proposals after Player {proposer_id} submission: {proposals}")

        # Select a proposal for voting after 3 submissions
        if len(proposals) == 3:
            self.group.select_random_proposal()
            print("Confirmed \n")

    # Validate input data
    def error_message(self, values):
        # Condition 1: All proposals (s1, s2, s3) are within 0 to 30 range 
        if any(values[key] < 0 or values[key] > 30 for key in ['s1', 's2', 's3']):
            return "Each proposal must be between 0 and 30."
        # Condition 2: Sum of all proposed values equal exactly 30
        if sum([values['s1'], values['s2'], values['s3']]) != 30:
            return "The total allocation must sum to exactly 30."

# Select random proposal once all players have submitted
class SelectingPage(WaitPage):
    # template_name = 'fund_vanishes/templates/fund_vanishes/SelectingPage.html'  # Custom HTML for styling
    # template_name = 'SelectingPage.html'  
    
    # Set the wait page to automatically advance when all players are ready
    wait_for_all_groups = True  
    
    def before_next_page(self):
        proposals = json.loads(self.group.all_proposals_str)

        # Ensure a proposal has been selected
        if len(proposals) == 3:
            self.group.select_random_proposal()
        
        # Retrieve and store chosen proposal
        selected_proposal = json.loads(self.group.selected_proposal)
        store_decision(self.player, "SelectingPage", "Selected Proposal", selected_proposal)


# Display selected proposal
class SelectedProposalPage(Page):
    # Retrieve the stored proposer ID from group model and display
    def vars_for_template(self):
        # Ensure proposer ID exists before formatting output
        if not self.group.selected_proposal or self.group.selected_proposal == "{}":
            return {"selected_proposer_id": "Unknown", "selected_proposal": {}, "relevant_proposal": {}}

        # Retrieve the stored proposer ID from group model and display
        proposer_id = self.group.selected_proposer_id
        proposer_display = f"Participant {proposer_id}" if proposer_id else "Unknown"

        # Ensure proposer ID exists before formatting output
        selected_proposal = json.loads(self.group.selected_proposal)
        
        # Print selected proposal when the page loads
        print(f"\n[DEBUG] Displaying selected proposal: {selected_proposal}\n")

        # Extract only the "proposal" part from the JSON
        relevant_proposal = selected_proposal.get("proposal",{})
        # Print selected proposal for debugging
        print(f"\n[DEBUG] Displaying selected proposal: {relevant_proposal}\n")

        # Return variables that will be used in the page template
        return {
            'selected_proposer_id': proposer_display,
            'selected_proposal': selected_proposal,      # Returns full proposal dict (for debugging)
            'relevant_proposal': relevant_proposal      # Correct allocation dictionary
        }

# Voting Page: Players vote on the selected proposal
class VoterPage(Page):
    form_model = 'player'  
    form_fields = ['vote'] 

    # Pass proposal data to the template
    def vars_for_template(self):
        selected_proposal = json.loads(self.group.selected_proposal)    # Convert JSON to dict
        relevant_proposal = selected_proposal.get("proposal",{})        # Extract allocation
        return {
            'id': self.player.id_in_group,
            'selected_proposer_id': self.group.selected_proposer_id,
            'selected_allocation': relevant_proposal                    # Pass extracted allocation
        }

    def before_next_page(self):
        # Log voting decisions of players
        vote_decision = {"vote": self.player.vote}
        store_decision(self.player, "VoterPage", "Voted", vote_decision)

# Select random proposal once all players have submitted
class VoterWaitPage(WaitPage):
    def before_next_page(self):
        votes = json.loads(self.group.all_votes_str)
        # Ensure all 3 players have voted
        print(len(votes))
        if len(votes) == 3:
            print("Confirmed \n")

# Explain experiment instructions
class DecisionPage(Page):
    def is_displayed(self):
        return self.round_number == 1

class ResultsPage(Page):
    
    def vars_for_template(self):
       
        # Proposal Details ------------------------------------------------------------------
        
        proposer_id = self.group.selected_proposer_id
        proposer_display = f"Participant {proposer_id}" if proposer_id else "Unknown"
        
        # Extract only the "proposal" part from the JSON
        selected_proposal = json.loads(self.group.selected_proposal)
        relevant_proposal = selected_proposal.get("proposal",{})

        # Voting Results ------------------------------------------------------------------
        
        total_votes = sum([p.vote for p in self.group.get_players()])
        proposal_approved = total_votes >= 2
        self.group.approved = proposal_approved
        
        # Earnings Results ------------------------------------------------------------------
        # Players get earnings if proposal is approved
        player_earnings = {}
    
        if proposal_approved:
            for p in self.group.get_players():
                # Construct key to match player's ID with the proposal
                player_id = f's{p.id_in_group}' 
                # Retrieve earnings from proposal, default to 0 if missing
                earnings = cu(relevant_proposal.get(player_id, 0))                # COMMENTED OUT
                # Assign earnings to the player's model
                p.earnings = earnings  
                # Store earnings for display in the template
                player_earnings[f'Participant {p.id_in_group}'] = earnings  # Store for template          # COMMENTED OUT
                print(f"\n[DEBUG] Before storing earnings, all_earnings for Player {p.id_in_group}: {p.all_earnings}")
                # p.store_earnings(self.group.current_period, player_earnings[f'Participant {p.id_in_group}'])
                p.store_earnings(p.id_in_group, self.group.current_period, player_earnings[f'Participant {p.id_in_group}'])
                print(f"\n[DEBUG] After storing earnings, all_earnings for Player {p.id_in_group}: {p.all_earnings}")
                # p.store_earnings(p.id_in_group, self.group.current_period, player_earnings[f'Participant {p.id_in_group}'])
        else:
            for p in self.group.get_players():
                p.earnings = cu(0)  # Set to Currency(0)
                player_earnings[f'Participant {p.id_in_group}'] = cu(0)  # Store for template             # COMMENTED OUT  
                # Store player's earnings for this period
                print(f"\n[DEBUG] Before storing earnings, all_earnings for Player {p.id_in_group}: {p.all_earnings}")
                # p.store_earnings(self.group.current_period, player_earnings[f'Participant {p.id_in_group}'])
                p.store_earnings(p.id_in_group, self.group.current_period, player_earnings[f'Participant {p.id_in_group}'])
                print(f"\n[DEBUG] After storing earnings, all_earnings for Player {p.id_in_group}: {p.all_earnings}")
                # p.store_earnings(p.id_in_group, self.group.current_period, player_earnings[f'Participant {p.id_in_group}'])

        # ✅ Debugging print to check if the variable exists (for server logs)
        print("current_period:", self.group.current_period)
        print("player_earnings:", player_earnings)

        # Player period for display
        p_period = self.participant.vars.get('periods_played', 0)

        # Calculate final earnings if in the final period
        if self.group.current_period == 5:
            for p in self.group.get_players():
                p.final_earnings()

        # Return variables that will be used in template
        return {
            # Randomly selected proposer and his/her proposal
            'selected_proposer_id': proposer_display,
            'relevant_proposal': relevant_proposal,     
            # Number of 'Yes' votes from players
            'total_votes': total_votes,  
            # Boolean indicating if the the proposal is approved
            'approved': proposal_approved,
            # Shows how much everyone earned in the game
            'player_earnings': player_earnings,
            # Shows how much the relevant player, personally earned for visibility
            'your_earnings': int(self.player.earnings),
            # Show current period played by player
            'period': p_period 
        }

# Ensures that all players complete their periods before stopping the game
class SyncBottom(WaitPage):

    wait_for_all_groups = True
    body_text = 'Please wait for the other groups to finish voting...'

    # Ensure players return to SyncTop if they haven't completed 5 periods
    def is_displayed(self):
        return self.participant.vars.get('periods_played', 0) < Constants.no_periods  

    @staticmethod
    def after_all_players_arrive(subsession: Subsession):

        # Access session data
        session = subsession.session  

        # Check if all players have  completed 5 periods
        all_finished = all(p.participant.vars.get('periods_played', 0) >= Constants.no_periods for p in subsession.get_players())

        print(f"\n[DEBUG] Checking if all players have completed 5 rounds: {all_finished}")

        # If everyone has finished, mark session as finished
        session.finish = all_finished

        if not all_finished:
            print("\n[DEBUG] Not all players finished, REPEATING GAME LOOP.\n")

            # If not all have finished, ensure they go back to SyncTop
            for p in subsession.get_players():
                if p.participant.vars.get('periods_played', 0) < Constants.no_periods:
                    p.participant.vars['next_period'] = True  # Ensure game continues

        session.finish = all_finished  # Only stop when everyone is done
        # # If ALL players are ready to proceed
        # if not_all == False:
        #     for p in subsession.get_players():
        #         # Reset the skip flag for each participant
        #         p.participant.skip_this_oTree_round = False

        #         # Update the session's matching round to move to the next one
        #         session.number_oTree_round_matching = p.round_number + 1

        #         # Retrieve the player's group
        #         group = p.group

        #         # Check if the player has reached the maximum number of periods
        #         if (p.participant.periods == 5) and (p.participant.skip_this_oTree_round == False):
        #             session.finish = True  # Mark the session as finished
        #         else:
        #             session.finish = False  # Continue the session

        # # If at least one player is NOT ready
        # elif not_all == True:
        #     session.finish = False  # Ensure session continues
        #     for p in subsession.get_players():
        #         if p.participant.next_period == False:
        #             # Player is NOT ready → do not skip this round
        #             p.participant.skip_this_oTree_round = False
        #         elif p.participant.next_period == True:
        #             # Player is ready → they skip the current round
        #             p.participant.skip_this_oTree_round = True

    # ----------------- Handling Dropouts -----------------
    
    @staticmethod
    def get_timeout_seconds(player):
        """
        Determines the timeout duration for players. If a player is marked as a dropout,
        they are instantly timed out (1 second). Otherwise, the normal time limit applies.
        """
        participant = player.participant
        if participant.is_dropout:
            return 1  # Instant timeout (1 second) for dropouts
        else:
            return C.TIMELIMIT * 3  # Normal timeout duration (multiplied by 3)

    # # Handle timeouts and mark dropouts
    # @staticmethod
    # def before_next_page(player, timeout_happened):
    #     participant = player.participant
    #     if timeout_happened:
    #         participant.is_dropout = True 
    #         player.dropout = True          

# Welcome Page to Survey
class SurveyPage(Page):
    form_model = 'player'
    form_fields = ['feedback']

    def is_displayed(self):
        # Initialize surveyStep in participant.vars if it does not exist
        if 'surveyStep' not in self.participant.vars:
            self.participant.vars['surveyStep'] = 0
        # return True  # Keep the page displayed
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def before_next_page(self):
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


# MODIFIED PAYMENT INFO PAGE -----------------------------------

class PaymentInfo(Page):

    def is_displayed(self):
        """Ensure PaymentInfo is only displayed when the player has finished all 5 periods."""
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  
        # True

    def vars_for_template(self):
        final_earnings_data = self.player.final_earnings()
        # Extract token for each round
        # Calculate payment for each round

        return {
            "selected_periods": final_earnings_data["selected_periods"],
            "final_payment": final_earnings_data["final_payment"],
            # "period_earnings": final_earnings_data["period_earnings"],
            "total_bonus":final_earnings_data["total_bonus"]
        }

    def js_vars(player):
        return dict(
            completionlink=
              player.subsession.session.config['completionlink']
    )
    pass

# 

# PRIMING / BASELINE QUESTIONS ---------------------------------

class Priming(Page):
    form_model = 'player'
    form_fields = ['qp1', 'qp2', 'qp3']

    def is_displayed(self):
        # Display only if player selected for priming treatment
        # return self.player.is_priming
        return self.participant.vars.get("is_priming", False) and self.round_number == 1
        # return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def vars_for_template(self):
        # Pass the player's gender selction to template
        return {
            "selected_gender": self.participant.vars.get("selected_gender", "Not specified")
        }
    
    def before_next_page(self):
        # Record Response
        store_survey_response(self.player, "Priming", self.form_fields)


class Baseline(Page):
    form_model = 'player'
    form_fields = ['qp1', 'qp2', 'qp3']

    def is_displayed(self):
        # Display only if player selected for baseline treatment
        # return not self.player.is_priming
        return not self.participant.vars.get("is_priming") and self.participant.vars.get('periods_played', 0) >= Constants.no_periods 
        # return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def vars_for_template(self):
        # Pass the player's gender selction to template
        return {
            "selected_gender": self.participant.vars.get("selected_gender", "Not specified")
        }
    
    def before_next_page(self):
        # Record Response
        store_survey_response(self.player, "Baseline", self.form_fields)


# SURVEY PAGES -------------------------------------------------

class Part1a(Page):
    form_model = 'player'
    form_fields = ['cmt_propr', 'cmt_vtr']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        self.participant.vars["surveyStep"] = self.participant.vars.get("surveyStep", 1)
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 
    
    def vars_for_template(self):
        return {
            "survey_step": 1,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Save participant data to CSV when they submit responses
        store_survey_response(self.player, "Part1a", self.form_fields)
        
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

class Part1b(Page):
    form_model = 'player'
    form_fields = ['retaliation', 'retaliation_other', 'mwc', 'mwc_others']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def vars_for_template(self):
        return {
            "survey_step": 2,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        } 
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part1b", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part1c(Page):
    form_model = 'player'
    form_fields = ['atq_1', 'atq_2', 'atq_3']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods

    def vars_for_template(self):
        return {
            "survey_step": 3,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part1c", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

class Part1d(Page):
    form_model = 'player'
    # form_fields = ['age', 'sex', 'gen', 'other_gender', 'gen_cgi', 'risk']
    form_fields = ['age', 'risk']

    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  
    
    def vars_for_template(self):
        return {
            "survey_step": 4,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part1d", self.form_fields)
        # Increase progress bar
        self.participant.vars['surveyStep'] += 1

class Part3b(Page):
    form_model = 'player'
    form_fields = ['occ', 'volunt', 'volunt_hrs']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 5,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # If doesn't do volunteer, set volunteer hours as 0
        if self.player.volunt != '1':
            self.player.volunt_hrs = ''
        # Store responses
        store_survey_response(self.player, "Part3b", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

class Part2a(Page):
    form_model = 'player'
    form_fields = ['econ', 'party_like', 'party', 'party_prox']
    # form_fields = ['econ', 'party_like', 'party', 'party_prox']

    def is_displayed(self):
        # Display page only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 6,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }
    
    def before_next_page(self):
        if self.player.party_like != '1':
            self.player.party = ''
            self.player.party_prox = ''

        # Record response
        store_survey_response(self.player, "Part2a", self.form_fields)
        # Increase survey step when the player moves to the next page
        # If user didn't select "I use a different term"

class Part4b(Page):
    form_model = 'player'
    # form_fields = ['plop_unempl', 'plop_comp', 'plop_incdist']
    form_fields = ['plop_unempl', 'plop_comp', 'plop_incdist','plop_priv', 'plop_luckeffort']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            "survey_step": 7,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part4b", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

# class Part4c(Page):
#     form_model = 'player'
#     form_fields = ['plop_priv', 'plop_luckeffort']

#     # @staticmethod
#     def is_displayed(self):
#         # Display only if offer was accepted
#         # return True
#         return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

#     def vars_for_template(self):
#         return {
#             "survey_step": self.participant.vars.get("surveyStep", 1),
#             "total_steps": SURVEY_PAGES  # Adjust based on survey length
#         }

#     def before_next_page(self):
#         # Record response
#         store_survey_response(self.player, "Part4c", self.form_fields)
#         # Increase survey step when the player moves to the next page
#         self.participant.vars['surveyStep'] += 1

class Part5(Page):
    form_model = 'player'
    form_fields = ['rel', 'rel_spec']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 8,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        if self.player.rel != '1':
            self.player.rel_spec = ''
        # Record response
        store_survey_response(self.player, "Part5", self.form_fields)

class Part7(Page):
    form_model = 'player'
    form_fields = ['mth_spbrn', 'mth_cntbrn', 'fth_spbrn', 'fth_cntbrn']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 9,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part7", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

class Part9(Page):
    form_model = 'player'
    form_fields = ['mwc_bonus', 'mwc_bonus_others', 'enjoy']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 10,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part9", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

class Part10(Page):
    form_model = 'player'
    form_fields = ['bonus']

    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 11,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part10", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

class Fin(Page):
    form_model = 'player'

    # @staticmethod
    def vars_for_template(player):
        return dict(
            pay=int(player.participant.payoff)
        )

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods  


# SEQUENCE SECTION -------------------------------------

# Priming
page_sequence = [

    WelcomePage,

    # Preliminary Questions
    IntroQuestions, 
    Nationality,    
    Education,      
    Gender,       
    Income,         

    # Game Instructions
    ExperimentInstructions,
    SampleInstructions,
    QuizPage,
    FailedPage,

    # Priming Treatment
    Priming,

    # Main game loop - 5 times per player
    SyncTop,
    CalculatePage,
    WaitingPage,
    ProposerPage,
    SelectingPage,
    SelectedProposalPage,
    VoterPage,
    VoterWaitPage,
    ResultsPage,
    SyncBottom,     # Redirect back to SyncTop until all periods compelted

    # Baseline Treatment
    Baseline,       

    # Survey
    SurveyPage,     
    Part1a,         # Voting and Proposing Considerations
    Part1b,         # Retaliation, mwc, mwc_others
    Part1c,         # atq 1, 2, 3 (ie. math questions)
    Part1d,         # Age, Risk
    Part3b,         # Occupation, Volunteer, (Volunteer Hours)
    Part2a,         # Econ Courses, Party Like, Party, Party Prox
    Part4b,         # Plop_Unempl, Plop_Comp, Plop_Incdist, Plop_Priv, Plop_Luckeffort
    Part5,          # Religion, (Specify Religion)
    Part7,          # Parents' Place of Birth/Citizenship
    Part9,          # mwc_bonus, mwc_bonus_others, enjoy
    Part10,         # bonus question
    # Display Total Earnings 
    PaymentInfo,        
]


# Regroup,
# Add page for ExemptVoter
# ExemptVoterPage,

# Baseline
page_sequence_baseline = [
    # Introduction Phase
    # SurveyPage,
    WelcomePage,
    ProlificID,
    ExperimentInstructions,
    SampleInstructions,
    QuizPage,
    FailedPage,

    # Main game loop - 5 times (periods) per player
    SyncTop,
    CalculatePage,
    WaitingPage,
    ProposerPage,
    SelectingPage,
    SelectedProposalPage,
    VoterPage,
    VoterWaitPage,
    ResultsPage,
    SyncBottom, # Redirect back to SyncTop until all periods compelted

    # Baseline
    PrimingBaseline,

    # Survey
    SurveyPage,
    Part1a, 
    Part1b, 
    Part1c, 
    Part1d, 
    Part3b,
    Part2a, 
    Part4b,
    Part5,
    Part7,
    Part9,
    # Proceed to payment and final survey once player is done with 5 periods
    PaymentInfo,        
]

