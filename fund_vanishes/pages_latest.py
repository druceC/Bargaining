# Handle logic for experiment pages (welcome, proposal, voting, results)

from otree.api import *
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
class SyncTop(WaitPage):
    # Wsait only within current group, not across all groups
    wait_for_all_groups = False
    # after_all_players_arrive = after_all_players_arrive()
    # group_by_arrival_time = True                # Needed to form group of 9 dynamically
    body_text = "Kindly wait to be randomly matched with other participants."

    def is_displayed(self):
        # Print number of periods played by each participant
        print(f"[DEBUG] Number of Periods Played by {self.participant.id}: {self.participant.vars.get('periods_played', 0)}")

        # Show this page only if participant hasn't played all rounds yet
        return self.participant.vars.get('periods_played', 0) < Constants.no_periods

    # def after_all_players_arrive(subsession: Subsession):
    #     waiting = subsession.get_players()
    #     random.shuffle(waiting)
    #     group_matrix = [waiting[i:i+9] for i in range(0, len(waiting), 9)]
    #     subsession.set_group_matrix(group_matrix)

    # @staticmethod
    def after_all_players_arrive(group, **kwargs):
        subsession = group.subsession       # Reference to current subsession
        session = subsession.session        # Reference to session object

        # Initialize list containing players who reached reached SyncTop if not already set
        if "ready_players" not in session.vars:
            session.vars["ready_players"] = []

        # ONLY include players in the group who have reached SyncTop
        for p in group.get_players():
            # If player is not yet in the list, append
            if p.id_in_subsession not in session.vars["ready_players"]:
                session.vars["ready_players"].append(p.id_in_subsession)

        print(f"[DEBUG] {len(session.vars['ready_players'])} players have reached SyncTop: {session.vars['ready_players']}")

        # GROUPING LOGIC ------------------------------------------------------------------------------------

        # Wait until 9 players have reached SyncTop
        if len(session.vars["ready_players"]) < 9:
            print("[DEBUG] Waiting for more players to reach SyncTop...")
            return  # Do not proceed until we have 9 players

        # 1. GROUPINGS 
        # Once 9 players have reached, create the supergroup only once
        if "initial_supergroup_ids" not in session.vars:
        # Step 1: Initialize the supergroup only once
            all_players = subsession.get_players()
            ready_ids = session.vars["ready_players"][:9]
            session.vars["initial_supergroup_ids"] = ready_ids
            print(f"[DEBUG] Supergroup locked in: {ready_ids}")

        # Get current players in the subsession
        all_players = subsession.get_players()

        # Identify supergroup players
        try: 
            supergroup_players = [
                next(p for p in all_players if p.id_in_subsession == pid)
                for pid in session.vars["initial_supergroup_ids"]
            ]
        except StopIteration:
            print("[ERROR] Some supergroup players not found in subsession — skipping grouping.")
            return

        # 2. SUB-GROUPS OF 3: Shuffle supergroup into subgroups of 3 (reshuffle every round)
        if len(session.vars["initial_supergroup_ids"]) >= 9:
            random.shuffle(supergroup_players)
            subgroups = [supergroup_players[i:i + 3] for i in range(0, 9, 3)]

            # Step 4: Handle other players in the subession who are NOT in the supergroup
            inactive_players = [p for p in all_players if p.id_in_subsession not in session.vars["initial_supergroup_ids"]]
            singleton_groups = [[p] for p in inactive_players]

            # Set the full group matrix
            full_group_matrix = subgroups + singleton_groups
            subsession.set_group_matrix(full_group_matrix)

            # For debugging
            print(f"[DEBUG] Round {subsession.round_number}: New subgroups formed:")
            for i, group in enumerate(full_group_matrix):
                labels = [p.participant.label or f"P{p.id_in_subsession}" for p in group]
                print(f"  Group {i + 1}: {labels}")

            # Mark grouping as complete
            session.vars["grouping_completed"] = True

            # Mark all players who just passed SyncTop to increment periods
            for p in group.get_players():
                if p.participant.vars.get('periods_played', 0) < Constants.no_periods:
                    p.participant.vars['periods_played'] += 1
                    p.participant.vars['next_period'] = True

     
    @staticmethod
    def before_next_page(player, timeout_happened):

        # Access participant data
        participant = player.participant

        # If a player times out, mark them as a dropout
        if timeout_happened:
            participant.is_dropout = True   # Mark participant as dropped out
            player.dropout = True           # Mark player as dropped out

        # Prevent proceeding if grouping isn't completed
        if not player.session.vars.get("grouping_completed", False):
            print(f"[DEBUG] Player {participant.id_in_session} is waiting for grouping to complete.")
            return  # Half progression

# Page to perform logic to track and increment custom "period" counter for each participant
class CalculatePage(Page):
    
    # Show page only if next_period is True and skip_round is false
    def is_displayed(self):
        # for player in self.subsession.get_players():

        # Retrieve custom flags
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

        # Initialize period counter if not set yet (starts at 0)
        if 'periods' not in self.player.participant.vars:
            self.player.participant.vars['periods'] = 0  # Ensure it starts from 0

        # Increment the player's period count
        self.player.participant.vars['periods'] += 1

        # Update the group's period to match the participant's period
        group.current_period = self.player.participant.vars['periods']
        # group.current_period = self.round_number

        # ---------------------

        # Optional: Reference to the participant object
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

    def after_all_players_arrive(self):
        self.group.set_subgroups()

    # def after_all_players_arrive(self):
    #     """Assigns one proposer and two voters randomly"""
    #     players = self.group.get_players()
    #     proposer = random.choice(players)  # Select one player as proposer
    #     proposer.player_role = "Proposer"

    #     for p in players:
    #         if p != proposer:
    #             p.player_role = "Voter"  # The remaining players are voters

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
        print(f"[DEBUG] {self.player.participant.label} reached {self.__class__.__name__} in round {self.round_number}")

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

    # Only wait for players within the same group (sub-group of 3)
    wait_for_all_groups = False
    body_text = "Waiting for other players to submit their proposals..."

    def after_all_players_arrive(self):
        # Load all proposals submitted so far
        proposals = json.loads(self.group.all_proposals_str)

        # Ensure all 3 group members have submitted proposals before selecting
        if len(proposals) == 3:
            self.group.select_random_proposal()

        # Debug: Show selected proposal (should now exist)
        print(f"[DEBUG] Selected proposal: {self.group.selected_proposal}")

    
    def before_next_page(self):
        # Debugging: Print round number
        print(f"[DEBUG] {self.player.participant.label} reached {self.__class__.__name__} in round {self.round_number}")
        # Retrieve and store chosen proposal
        selected_proposal = json.loads(self.group.selected_proposal)
        store_decision(self.player, "SelectingPage", "Selected Proposal", selected_proposal)


# Display selected proposal
class SelectedProposalPage(Page):
    # Retrieve the stored proposer ID from group model and display
    def before_next_page(self):
        print(f"[DEBUG] {self.player.participant.label} reached {self.__class__.__name__} in round {self.round_number}")

    def vars_for_template(self):
        # Ensure proposer ID exists before formatting output
        if not self.group.selected_proposal or self.group.selected_proposal == "{}":
            return {"selected_proposer_id": "Unknown", "selected_proposal": {}, "relevant_proposal": {}}

        # Retrieve the stored proposer ID from group model and display
        proposer_display = self.group.selected_proposer_id
        # proposer_display = f"Participant {proposer_id}" if proposer_id else "Unknown"

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
            'relevant_proposal': relevant_proposal,      # Correct allocation dictionary
            'player_id': self.player.id_in_group
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
            'selected_allocation': relevant_proposal,                  # Pass extracted allocation
        }

    def before_next_page(self):
        # Print round number
        print(f"[DEBUG] {self.player.participant.label} reached {self.__class__.__name__} in round {self.round_number}")
        # Log voting decisions of players
        vote_decision = {"vote": self.player.vote}
        store_decision(self.player, "VoterPage", "Voted", vote_decision)

# Select random proposal once all players have submitted
class VoterWaitPage(WaitPage):
    body_text = 'Waiting for other players to finish voting...'

    def before_next_page(self):
        # Print round number
        print(f"[DEBUG] {self.player.participant.label} reached {self.__class__.__name__} in round {self.round_number}")
        # Load votes
        votes = json.loads(self.group.all_votes_str)
        # Ensure all 3 players have voted
        print(len(votes))
        if len(votes) == 3:
            print("Confirmed \n")


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
            # 'period': p_period,                                                                 # original
            'period': self.round_number,
            'player_id': self.player.id_in_group, 
        }
    
    def before_next_page(self):
        # Get round number for debugging
        print(f"[DEBUG] {self.player.participant.label} reached {self.__class__.__name__} in round {self.round_number}")

# Ensures that all players complete their periods before stopping the game
class SyncBottom(WaitPage):

    # Only wait for members in the same group 
    wait_for_all_groups = False
    body_text = 'Waiting for other players to finish before starting the next round...'

    # Ensure players return to SyncTop if they haven't completed 5 periods
    def is_displayed(self):
        return self.participant.vars.get('periods_played', 0) < Constants.no_periods  

    @staticmethod
    def after_all_players_arrive(group, **kwargs):
        subsession = group.subsession           # Reference to current subsession
        session = subsession.session            # reference to session object

        ready_ids = session.vars.get("ready_players", [])
        # Filter only active participants
        active_players = [
            p for p in subsession.get_players() 
            if p.id_in_subsession in ready_ids
        ]

        # ✅ Check if all 9 active players are done
        all_finished = all(p.participant.vars.get('periods_played', 0) >= Constants.no_periods for p in active_players)

        print(f"\n[DEBUG] Checking if 9 active players have completed 5 rounds: {all_finished}")

        if not all_finished:
            print("\n[DEBUG] Not all active players finished, REPEATING GAME LOOP.\n")
            for p in active_players:
                if p.participant.vars.get('periods_played', 0) < Constants.no_periods:
                    p.participant.vars['next_period'] = True

        session.finish = all_finished
        # Check if all players have  completed 5 periods
        # all_finished = all(p.participant.vars.get('periods_played', 0) >= Constants.no_periods for p in subsession.get_players())

        # print(f"\n[DEBUG] Checking if all players have completed 5 rounds: {all_finished}")

        # If everyone has finished, mark session as finished
        # session.finish = all_finished

        # if not all_finished:
        #     print("\n[DEBUG] Not all players finished, REPEATING GAME LOOP.\n")

        #     # If not all have finished, ensure they go back to SyncTop
        #     for p in subsession.get_players():
        #         if p.participant.vars.get('periods_played', 0) < Constants.no_periods:
        #             p.participant.vars['next_period'] = True  # Ensure game continues

        # session.finish = all_finished  
        
        
        # Only stop when everyone is done
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

# EARNINGS PAGE

class PaymentInfo(Page):

    def is_displayed(self):
        # Ensure PaymentInfo is only displayed when the player has finished all 5 periods.
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods 
        # return self.participant.vars.get('periods_played', 0) >= NUM_ROUNDS
        # return self.participant.vars.get(self.round_number) >= NUM_ROUNDS
        # return self.round_number >= NUM_ROUNDS
        print("Number of rounds played: " + self.participant.vars.get('periods_played', 0)) 
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

    def before_next_page(self):
        # Record Earnings
        store_earnings(player, {
            "selected_periods": final_earnings_data["selected_periods"],
            "final_payment": final_earnings_data["final_payment"],
            "total_bonus": final_earnings_data["total_bonus"]
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
    # ExperimentInstructions,
    # SampleInstructions,
    QuizPage,
    FailedPage,

    # Priming Treatment
    # Priming,

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
    SyncBottom, # Redirect back to SyncTop until all periods compelted

    # Baseline Treatment
    # SurveyPage,
    # Baseline,       

    # Survey
    # Part1a,         # Voting and Proposing Considerations
    # Part1b,         # Retaliation, mwc, mwc_others
    # Part1c,         # atq 1, 2, 3 (ie. math questions)
    # Part1d,         # Age, Risk
    # Part1e,         # Occupation, Volunteer, (Volunteer Hours)
    # Part2a,         # Econ Courses, Party Like, Party, Party Prox
    # Part2b,         # Plop_Unempl, Plop_Comp, Plop_Incdist, Plop_Priv, Plop_Luckeffort
    # Part3,          # Religion, (Specify Religion)
    # Part4,          # Parents' Place of Birth/Citizenship
    # Part5,          # mwc_bonus, mwc_bonus_others, enjoy
    # Part6,         # bonus question
    
    # Display Total Earnings 
    PaymentInfo,      
]

