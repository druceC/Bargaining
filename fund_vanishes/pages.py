# Handle logic for experiment pages (welcome, proposal, voting, results)

from otree.api import *
from otree.api import Page
from .models import Player
from .utils import store_intro, store_survey_response, store_decision, store_earnings
# from .survey import Player
from .models import Constants
from .models import Group
from .models import Subsession
from otree.api import BaseSubsession
from pathlib import Path
from datetime import datetime
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

# ---------------------------------------------------------------------------------------------------

# INTRO QUESTIONS

# Dropout detection for normal pages (all game pages inherit from this)
class BasePage(Page):
    def is_displayed(self):
        # Don't show page if dropout is detected
        return not self.group.drop_out_detected
    
    # def app_after_this_page(self, upcoming_apps):
    #     if self.group.drop_out_detected:
    #         return 'fund_vanishes/DropoutNotice'

# Dropout detection for WaitPages
class BaseWaitPage(WaitPage):
    def is_displayed(self):
        # Don't show page if dropout is detected
        return not self.group.drop_out_detected
    
    # def app_after_this_page(self, upcoming_apps):
    #     if self.group.drop_out_detected:
    #         return 'fund_vanishes/DropoutNotice'

class WelcomePage(Page):
    def is_displayed(self):
        return self.round_number == 1

class ExperimentInstructions(Page):
    def is_displayed(self):
        return self.round_number == 1

class SampleInstructions(Page):
    def is_displayed(self):
        return self.round_number == 1

# Mini quiz to ensure understanding of game instructions
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
            print(f"Total failed attempts: {self.player.total_num_failed_attempts}") 
            # Redirect to failed page after 3 attempts
            if self.player.total_num_failed_attempts >= 3:
                self.participant.vars['redirect_to_failed'] = True 
                return 
            return errors  # Returns error messages to be displayed to the participant
    
    
    # def before_next_page(self):
    #     if self.player.total_num_failed_attempts >= 3:
    #         self.participant.vars['redirect_to_failed'] = True  
    
    # Redirect to failed.html
    # def app_after_this_page(self, upcoming_apps):
    #     if self.participant.vars.get('redirect_to_failed', False):
    #         return 'fund_vanishes/FailedPage'  # Replace with your actual app/page path

# Show this page if player fails the quiz
# Displays failure message if the player fails the quiz after 3 attempts
class FailedPage(Page):
    def is_displayed(self):
        return self.participant.vars.get('redirect_to_failed', False) 
    

# ---------------------------------------------------------------------------------------------------

# PRELIMINARY QUESTIONS

class IntroQuestions(Page):             # Page for Prolific ID Input
    form_model = 'player'
    form_fields = ['prolific_id']

    def is_displayed(self):
        # Initialize surveyStep
        if 'surveyStep' not in self.participant.vars:
            self.participant.vars['surveyStep'] = 1
        return self.round_number == 1

    def before_next_page(self):
        # Progress bar for next page
        self.participant.vars['surveyStep'] += 1
        # To prevent duplicates
        if not self.participant.vars.get("intro_saved", False):
            store_intro(self.player)
            self.participant.vars["intro_saved"] = True


class Nationality(Page):
    form_model = 'player'
    form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit', 'primlang']

    # @staticmethod
    def is_displayed(self):
        return self.round_number == 1

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
        return self.round_number == 1

    def vars_for_template(self):
        return {
            "survey_step": 2,
            "total_steps": INTRO_QUESTIONS  
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
        return self.round_number == 1
    
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
        
        # Assign the provided gender label into "selected_gender" variable or a custom one if 'gen' == '4'
        if str(self.player.gen).strip() == "4":
            self.participant.vars["selected_gender"] = self.player.other_gender  # Custom term
        else:
            self.participant.vars["selected_gender"] = self.GENDER_CHOICES.get(str(self.player.gen), "Not specified")

        # Save gender_cgi for templating in priming/baselin
        self.participant.vars["gender_expression"] = self.player.gen_cgi


class Income(Page):
    form_model = 'player'
    form_fields = ['inc','inc_hh']
    
    def is_displayed(self):
        return self.round_number == 1
    
    def vars_for_template(self):
        return {
            "survey_step": 4,
            "total_steps": INTRO_QUESTIONS  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Income", self.form_fields)


# ---------------------------------------------------------------------------------------------------

# GAME PAGES

# Synchronization page that ensures all players are randomly regrouped each period
class SyncTop(BaseWaitPage):

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
        if self.timeout_happened:
            participant.is_dropout = True   # Mark participant as dropped out
            player.dropout = True           # Mark player as dropped out


class CalculatePage(BasePage):
    # Set autosubmit count
    timeout_seconds = 5

    # Determine whether this page is displayed for a participant
    def is_displayed(self):
        for player in self.subsession.get_players():
            next_period = self.player.participant.vars.get('next_period', False)
            skip_round = self.player.participant.vars.get('skip_this_oTree_round', False)
            
            return next_period and not skip_round

    def vars_for_template(self):
        return {
            'timeout_seconds': self.timeout_seconds
        }

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
class WaitingPage(BaseWaitPage):
    # template_name = 'fund_vanishes/WaitingPage.html'
    body_text = "Kindly wait to be randomly matched with other participants."

    # def after_all_players_arrive(self):
    #     """Assigns one proposer and two voters randomly"""
    #     players = self.group.get_players()
    #     proposer = random.choice(players)  # Select one player as proposer
    #     proposer.player_role = "Proposer"

    #     for p in players:
    #         if p != proposer:
    #             p.player_role = "Voter"  # The remaining players are voters

# Submit Proposal Page: All players propose an allocation, then store
class ProposerPage(BasePage):
    # Store data collected in this page at the group level
    form_model = 'group'  
    # Collect allocation values from participants
    form_fields = ['s1', 's2', 's3']  
    # Set timeout count
    timeout_seconds = 10

    # Provide player ID for template rendering
    def vars_for_template(self):
        return {
            'id': self.player.id_in_group,
            'timeout_seconds': self.timeout_seconds
        }

    # Store the proposer's id and submitted allocation before proceeding
    def before_next_page(self, timeout_happened = False):
        proposer_id = self.player.id_in_group  

        # TIMEOUT: Handle case for when a timeout/dropout occurs    
        if self.timeout_happened:
            # Default failed allocation for timeout
            self.group.s1 = -10
            self.group.s2 = -10
            self.group.s3 = -10

            # Set allocation dict
            allocation = {
                "s1":self.group.s1,
                "s2":self.group.s2,
                "s3":self.group.s3
            }

            # Dropout flag
            self.drop_out_detected = True

            # Set timeout flag
            self.participant.vars["timed_out"] = True  

            # Store the proposal in the group for later voting
            self.group.store_proposal(proposer_id, allocation)

            # Store default allocation in csv 
            store_decision(self.player, "ProposerPage", "Timeout - Auto Proposal", allocation)

            # Debugging print
            proposals = json.loads(self.group.all_proposals_str)
            print(f"\n[DEBUG] Current stored proposals after Player {proposer_id} submission: {proposals}")

        # Submit user's proposal
        else:
            # Set allocation dict
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

# Timeout matching with AreYouThere
class SelectingPage(WaitPage):
    # template_name = 'fund_vanishes/SelectingPage.html'
    wait_for_all_groups = False
    timeout_seconds = 15 

    # Override to proceed if either (1) Timeout has elapsed or (2) All players have arrived
    
    # Override is ready: Proceed from wait page when either (1) all players are ready or (2) dropout detected
    def is_ready(self):
        print(f"[SelectingPage] Dropout detected? {self.group.drop_out_detected}")
        return self.group.all_players_ready() or self.group.drop_out_detected

    after_all_players_arrive = 'check_dropout_or_select'

    @staticmethod
    def check_dropout_or_select(group: Group):
        # Don't select random proposal if dropout is detected
        if group.drop_out_detected:
            # If a dropout is detected, flag all players to be redirected
            for p in group.get_players():
                p.participant.vars['go_to_dropout_notice'] = True
            return  # exit early — no selection
        else:
            # Load all submitted proposals from JSON string
            proposals = json.loads(group.all_proposals_str)
            # IF exactly 3 proposals were submitted, randomly select one
            if len(proposals) == 3:
                group.select_random_proposal()

    def before_next_page(self):
        if self.timeout_happened:
            print(f"[WaitOrTimeoutPage] Timeout for participant {self.participant.code}")
        else:
            print(f"[WaitOrTimeoutPage] Proceeding after all arrived: {self.participant.code}")

    def vars_for_template(self):
        return{
            "timeout_seconds": self.timeout_seconds
        }


# Select random proposal once all players have submitted
# class SelectingPage(WaitPage):
#     # Set the wait page to automatically advance when all players are ready
#     # wait_for_all_groups = True

#     wait_for_all_groups = False
#     after_all_players_arrive = 'check_dropout_or_select'
#     # Timeout for waitpage (timeout would indicate dropout)


#     # Check if a dropout happened or select a random proposal
#     @staticmethod 
#     def check_dropout_or_select(group: Group):
#         if group.drop_out_detected:
#             # If a dropout is detected, flag all players to be redirected
#             for p in group.get_players():
#                 p.participant.vars['go_to_dropout_notice'] = True
#             return  # exit early — no selection
#         else:
#             # Load all submitted proposals from JSON string
#             proposals = json.loads(group.all_proposals_str)
#             # IF exactly 3 proposals were submitted, randomly select one
#             if len(proposals) == 3:
#                 group.select_random_proposal()
    
#     def is_displayed(self):
#         # If we're already sending them to DropoutNotice, don't show this WaitPage
#         return not self.participant.vars.get('go_to_dropout_notice', False)
    
#     # Decide which page to go to after this page
#     def after_this_page(self):
#         # If flagged for dropout, redirect to DropoutNotice
#         if self.participant.vars.get('go_to_dropout_notice', False):
#             return DropoutNoticeOtherPlayers
    
#     # Override is ready: Proceed from wait page when either (1) all players are ready or (2) dropout detected
#     def is_ready(self):
#         print(f"[SelectingPage] Dropout detected? {self.group.drop_out_detected}")
#         return self.group.all_players_ready() or self.group.drop_out_detected
    
#     def live_method(self, data):
#         # Respond to client pings with current dropout status
#         return {
#             "dropout": self.group.drop_out_detected
#         }

    # def before_next_page(self):
    #     # DETECT DROPOUT: If a dropout was detected, set go_to_dropout_notice for everyone
    #     if self.group.drop_out_detected:
    #         for p in self.group.get_players():
    #             p.participant.vars['go_to_dropout_notice'] = True
    #         return  # Exit early, no need to select proposal

    #     # REGULAR CASE: Normal proposal selection
    #     proposals = json.loads(self.group.all_proposals_str)

    #     # Ensure a proposal has been selected
    #     if len(proposals) == 3:
    #         self.group.select_random_proposal()
        
    #     # Retrieve and store chosen proposal
    #     selected_proposal = json.loads(self.group.selected_proposal)
    #     store_decision(self.player, "SelectingPage", "Selected Proposal", selected_proposal)




# Display selected proposal
class SelectedProposalPage(BasePage):
    # Set autosubmit count
    timeout_seconds = 10

    # Retrieve the stored proposer ID from group model and display
    def vars_for_template(self):

        # Ensure proposer ID exists before formatting output
        if not self.group.selected_proposal or self.group.selected_proposal == "{}":
            return {
                "player_id": self.player.id_in_group,
                "selected_proposer_id": "Unknown", 
                "selected_proposal": {}, 
                "relevant_proposal": {},
                "timeout_occurred": False,
                "timeout_seconds": self.timeout_seconds
            }

        # Retrieve the stored proposer ID from group model and display
        proposer_display = self.group.selected_proposer_id

        # Ensure proposer ID exists before formatting output
        selected_proposal = json.loads(self.group.selected_proposal)
        # Print selected proposal when the page loads
        print(f"\n[DEBUG] Displaying selected proposal: {selected_proposal}\n")

        # Extract only the "proposal" part from the JSON
        relevant_proposal = selected_proposal.get("proposal",{})
        # Print selected proposal for debugging
        print(f"\n[DEBUG] Displaying selected proposal: {relevant_proposal}\n")

        proposer_id = selected_proposal.get("proposer_id", None)

        # Find out if that proposer timed out
        timeout_flag = False
        for p in self.group.get_players():
            if p.id_in_group == proposer_id and p.participant.vars.get("timed_out", False):
                timeout_flag = True
                break

        return {
            'selected_proposer_id': proposer_display,
            'selected_proposal': selected_proposal,
            'relevant_proposal': relevant_proposal,
            'player_id': self.player.id_in_group,
            'timeout_occurred': timeout_flag,
            'timeout_seconds': self.timeout_seconds
        }


# Voting Page: Players vote on the selected proposal
class VoterPage(BasePage):
    form_model = 'player'  
    form_fields = ['vote'] 
    timeout_seconds = 15

    # Pass proposal data to the template
    def vars_for_template(self):
        selected_proposal = json.loads(self.group.selected_proposal)    # Convert JSON to dict
        print(f"\n[DEBUG] Selected proposal on VoterPage: {selected_proposal}")
        
        relevant_proposal = selected_proposal.get("proposal",{})        # Extract allocation
        print("[DEBUG] relevant_proposal =", relevant_proposal)
        return {
            'id': self.player.id_in_group,
            'selected_proposer_id': self.group.selected_proposer_id,
            'selected_allocation': relevant_proposal,                  # Pass extracted allocation
            'timeout_seconds': self.timeout_seconds
        }

    def before_next_page(self):
        # TIMEOUT: Handle case for when a timeout/dropout occurs    
        if self.timeout_happened:
            # Set default vote
            vote_decision = {"vote": False}
            self.player.vote = False         # Save it to the database too
            # Set dropout flag
            self.drop_out_detected = True
            # Set timeout flag
            self.participant.vars["timed_out"] = True
            # Store default vote in csv
            store_decision(self.player, "VoterPage", "Timeout - Auto Vote", vote_decision)
        else:
            # Log voting decisions of players
            vote_decision = {"vote": self.player.vote}
            store_decision(self.player, "VoterPage", "Voted", vote_decision)

# Select random proposal once all players have submitted
class VoterWaitPage(BaseWaitPage):
    def before_next_page(self):
        votes = json.loads(self.group.all_votes_str)
        # Ensure all 3 players have voted
        print(len(votes))
        if len(votes) == 3:
            print("Confirmed \n")


class ResultsPage(BasePage):

    timeout_seconds = 5

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
            'period': p_period,
            'player_id': self.player.id_in_group, 
            'timeout_seconds': self.timeout_seconds
        }

# Ensures that all players complete their periods before stopping the game
class SyncBottom(BaseWaitPage):

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

# ---------------------------------------------------------------------------------------------------

# DROPOUT NOTICE PAGES

class AreYouThere(BasePage):
    timeout_seconds = 15
    # timeout_seconds = 10
    # template_name = "your_app_name/AreYouTherePage.html"

    def is_displayed(self):
        return (
            self.participant.vars.get("timed_out", False)
            and not self.group.drop_out_finalized
        )

    def before_next_page(self):
        if self.timeout_happened:
            # The player did NOT click "Yes, I'm here!"
            self.participant.vars['timed_out'] = True
            # Also set the GROUP-LEVEL dropout flag
            self.group.drop_out_detected = True
            self.participant.vars["dropout"] = True
            self.group.drop_out_finalized = True
        else:
            # Reset the flag for future rounds or pages
            self.participant.vars["timed_out"] = False

# Welcome Page to Survey
class DropoutNotice(Page):
    timeout_seconds = 15
    
    # Show this page to all remaining players if a dropout is detected in the group
    def is_displayed(self):
        # Show ONLY if dropout detected AND not yet finalized
        # return self.group.drop_out_detected and not self.group.drop_out_finalized
        return self.participant.vars.get("dropout", False)

    # def before_next_page(self):
    #     # Mark that dropout has been handled
    #     self.group.drop_out_finalized = True

    def vars_for_template(self):
        rounds_played = self.subsession.round_number  # Current round number

        # if rounds_played < 2:
        #     payment_message = (
        #         "Since fewer than 2 rounds were played, your final payment will be based on 1 randomly selected round."
        #     )
        # else:
        #     payment_message = (
        #         "Since 2 or more rounds were played, your final payment will be based on 2 randomly selected rounds."
        #     )
        payment_message = (
            "Since you have dropped out of the game, no payment shall be issued."
        )

        return {
            "rounds_played": rounds_played,
            "payment_message": payment_message,
            "timeout_seconds": self.timeout_seconds
        }

class DropoutNoticeOtherPlayers(Page):
    timeout_seconds = 15
    
    # Show this page to all remaining players if a dropout is detected in the group
    def is_displayed(self):
        # Show ONLY if dropout detected AND not yet finalized
        return self.group.drop_out_detected and not self.participant.vars.get("dropout", False)

    def before_next_page(self):
        # Mark that dropout has been handled
        self.group.drop_out_finalized = True

    def vars_for_template(self):
        rounds_played = self.subsession.round_number  # Current round number

        if rounds_played == 0:
            payment_message = (
                "No rounds were completed for this session. You will receive the fixed participation fee."
            )

        elif rounds_played < 2:
            payment_message = (
                "Since fewer than 2 rounds were played, your final payment will be based on 1 randomly selected round."
            )
        else:
            payment_message = (
                "Since 2 or more rounds were played, your final payment will be based on 2 randomly selected rounds."
            )

        return {
            "rounds_played": rounds_played,
            "payment_message": payment_message,
            "timeout_seconds": self.timeout_seconds
        }

# ---------------------------------------------------------------------------------------------------

# EARNINGS PAGE

class PaymentInfo(Page):

    # Adjust payment

    def is_displayed(self):
        # Payment info is only displayed when (1) All periods have been played or (2) Dropout is detected
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods or self.group.drop_out_detected
        # True

    def vars_for_template(self):
        final_earnings_data = self.player.final_earnings()
        
        # Make final adjustments to final payment if necessary (ie. dropouts)
        if self.participant.vars.get("dropout", False):
            # Update base fee to 0 for dropoutee
            final_earnings_data["base_fee"] = 0
            # Update final payment to 0 for dropoutee
            final_earnings_data["final_payment"] = 0

    

        return {
            "is_dropout": self.participant.vars.get("dropout", False),
            "selected_periods": final_earnings_data["selected_periods"],
            "final_payment": final_earnings_data["final_payment"],
            # "period_earnings": final_earnings_data["period_earnings"],
            "total_bonus": final_earnings_data["total_bonus"],
            "survey_fee": final_earnings_data["survey_fee"],
            "base_fee": final_earnings_data["base_fee"]
        }

    def before_next_page(self):
        # Record Earnings
        store_earnings(player, {
            "selected_periods": final_earnings_data["selected_periods"],
            "final_payment": final_earnings_data["final_payment"],
            "total_bonus": final_earnings_data["total_bonus"],
            "survey_fee": final_earnings_data["survey_fee"],
            "base_fee": final_earnings_data["base_fee"]
        })

    # Completion Link for Prolific

    # def js_vars(player):
    #     return dict(
    #         # completionlink=player.subsession.session.config['completionlink']
    # )
    # pass

# 

# ---------------------------------------------------------------------------------------------------

# PRIMING / BASELINE

class Priming(Page):
    form_model = 'player'
    form_fields = ['qp1', 'qp3']

    def is_displayed(self):
        # Display only if player selected for priming treatment
        return self.participant.vars.get("is_priming", False) and self.round_number == 1

    def vars_for_template(self):
        # Pass the player's gender selection to template
        return {
            "selected_gender": self.participant.vars.get("selected_gender", "Not specified"),
            "gender_expression": self.participant.vars.get("gender_expression", "Not specified"),
        }
    
    def before_next_page(self):
        # Record Response
        store_survey_response(self.player, "Priming", self.form_fields)


class Baseline(Page):
    form_model = 'player'
    form_fields = ['qp1', 'qp3']

    def is_displayed(self):
        # Display only if player selected for baseline treatment
        return not self.participant.vars.get("is_priming") and self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def vars_for_template(self):
        # Pass the player's gender selection to template
        return {
            "selected_gender": self.participant.vars.get("selected_gender", "Not specified"),
            "gender_expression": self.participant.vars.get("gender_expression", "Not specified"),
        }
    
    def before_next_page(self):
        # Record Response
        store_survey_response(self.player, "Baseline", self.form_fields)

# ---------------------------------------------------------------------------------------------------

# SURVEY PAGES

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


class Part1e(Page):
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
        store_survey_response(self.player, "Part1e", self.form_fields)
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


class Part2b(Page):
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
        store_survey_response(self.player, "Part2b", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part3(Page):
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
        store_survey_response(self.player, "Part3", self.form_fields)


class Part4(Page):
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
        store_survey_response(self.player, "Part4", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part5(Page):
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
        store_survey_response(self.player, "Part5", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part6(Page):
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
        store_survey_response(self.player, "Part6", self.form_fields)
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


# ---------------------------------------------------------------------------------------------------

# PAGE SEQUENCE

page_sequence = [

    WelcomePage,

    # Preliminary Questions
    # IntroQuestions, 
    # Nationality,    
    # Education,      
    # Gender,       
    # Income,         

    # Game Instructions
    ExperimentInstructions,
    SampleInstructions,
    QuizPage,
    FailedPage,

    # Priming Treatment

    # Main game loop - 5 times per player
    SyncTop,              # Where groups of 9 are set
    # Priming,            # Move this after synctop

    CalculatePage,        # Grouping Page - Continue

    WaitingPage,          # Wait Page 1    
    ProposerPage,         
    AreYouThere,          # Declare Dropout - If no response    # Timeout = 15 seconds
    # DropoutNotice,        

    SelectingPage,        # Wait Page 2                         # Timeout = 15 seconds
    # DropoutNoticeOtherPlayers,  
    SelectedProposalPage, 

    VoterPage,            # Players vote accept / reject
    AreYouThere,          # Declare Dropout - If no response
    # DropoutNotice,

    VoterWaitPage,        # Wait Page 3 (Detect Dropout)
    # DropoutNoticeOtherPlayers, 
    ResultsPage,          # Show if proposal is accepted / rejected
    SyncBottom,           # Redirect back to SyncTop until all periods compelted

    # Baseline Treatment
    # SurveyPage,
    # Baseline,       

    # Survey
    # Part1a,             # Voting and Proposing Considerations
    # Part1b,             # Retaliation, mwc, mwc_others
    # Part1c,             # atq 1, 2, 3 (ie. math questions)
    # Part1d,             # Age, Risk
    # Part1e,             # Occupation, Volunteer, (Volunteer Hours)
    # Part2a,             # Econ Courses, Party Like, Party, Party Prox
    # Part2b,             # Plop_Unempl, Plop_Comp, Plop_Incdist, Plop_Priv, Plop_Luckeffort
    # Part3,              # Religion, (Specify Religion)
    # Part4,              # Parents' Place of Birth/Citizenship
    # Part5,              # mwc_bonus, mwc_bonus_others, enjoy
    # Part6,              # bonus question
    
    # Display Total Earnings 
    DropoutNotice,                      # Display to dropout player
    DropoutNoticeOtherPlayers,          # Display to all other players
    PaymentInfo,      
]

