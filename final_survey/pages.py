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
    wait_for_all_groups = False
    group_by_arrival_time = True
    body_text = "Kindly wait to be randomly matched with other participants."

    #  Ensure page is only displayed for players who still need to play 5 rounds
    def is_displayed(self):
        return not self.participant.vars.get("has_synced", False)

    # @staticmethod
    # def group_by_arrival_time_method(subsession, waiting_players):
        
    #     eligible = [p for p in waiting_players]    # Create a list of players in SyncTop page
    #     group_size = 3
        
    #     # Create group
    #     if (len(eligible)) >= group_size:
    #         # Randomly pick 9 from the list of available players
    #         selected = random.sample(eligible, group_size)

    #         # Determine group index by checking how many groups have been created so far
    #         existing_groups = subsession.get_groups()
    #         group_index = len(existing_groups)

    #         # Assign priming/baseline treatment
    #         is_priming = group_index % 2 == 1  # Odd = priming, even = baseline

    #          # Create a shared identifier for this 9‑player “super‑group”
    #         group_id_9 = f"g9_{selected[0].id_in_subsession}"
    #         # Write group metadata into each participant’s vars for later rounds
    #         for p in selected:
    #             p.participant.vars["group_index"] = group_index
    #             p.participant.vars["group_id_9"] = group_id_9
    #             p.participant.vars["group_members"] = [q.id_in_subsession for q in selected]
    #             p.participant.vars["has_synced"] = True
    #             p.participant.vars["is_priming"] = is_priming 
    #             # Also assign on player object for easy access
    #             p.is_priming = is_priming

    #         # Server‑side debug log
    #         print(f"[DEBUG] round 1 – formed 9‑block {group_id_9}")

    #         # Initialize period counter for the group
    #         for p in selected:
    #             if 'periods_played' not in p.participant.vars:
    #                 p.participant.vars['periods_played'] = 0    # Initialize period count

    #         print(f"[DEBUG] formed 9‑block {group_id_9} → {'Priming' if is_priming else 'Baseline'}")

    #         # Returning the list lets oTree create this group and move on
    #         return selected
        
    #     # Fewer than nine → keep waiting
    #     return None

    # Handles actions before moving to the next page, including timeout handling. 
    @staticmethod
    def before_next_page(player, timeout_happened):

        # ==================================================================

        # Access participant data
        participant = player.participant

        # If a player times out, mark them as a dropout
        if self.timeout_happened:
            participant.is_dropout = True   # Mark participant as dropped out
            player.dropout = True           # Mark player as dropped out

        # Mark the participant as synced
        participant.vars["has_synced"] = True

        # ----- added part -----------

        # Reference to the player's group
        group = self.player.group

        # Increment period for the next round
        self.player.participant.vars['periods_played'] += 1

        # Reference to the participant object
        participant = self.player.participant

    def vars_for_template(self):
        return{
            "group_index": self.participant.vars.get("group_index", "N/A"),
            "is_priming": self.participant.vars.get("is_priming", None),
        }


class CalculatePage(BasePage):
    # Set autosubmit count
    timeout_seconds = 5

    # Determine whether this page is displayed for a participant
    def is_displayed(self):
        return True

    def vars_for_template(self):
        return {
            'timeout_seconds': self.timeout_seconds
        }

    # Handles logic before transitioning to the next page
    def before_next_page(self):

        # Reference to the player's group
        group = self.player.group

        # Increment period for the next round
        self.player.participant.vars['periods_played'] += 1

        # Reference to the participant object
        participant = self.player.participant

# Page shown while waiting for other participants to join and complete mini assessment
class WaitingPage(BaseWaitPage):
    # template_name = 'fund_vanishes/WaitingPage.html'
    body_text = "Kindly wait to be randomly matched with other participants."

    @staticmethod
    def after_all_players_arrive(group: Group):
        players = group.get_players()
        random.shuffle(players)
        for idx, p in enumerate(players):
            subgroup_id = (idx // 3) + 1
            id_in_subgroup = (idx % 3) + 1
            p.participant.vars["subgroup_id"] = subgroup_id
            p.participant.vars["id_in_subgroup"] = id_in_subgroup
            print(f"[DEBUG] Assigned Player {p.id_in_group} to Subgroup {subgroup_id} as {p.participant.vars['id_in_subgroup']}")

    def vars_for_template(self):
        return{
            "group_index": self.participant.vars.get("group_index", "N/A")
        }


# Submit Proposal Page: All players propose an allocation, then store
class ProposerPage(BasePage):
    # Store data collected in this page at the group level
    form_model = 'player'  
    # Collect allocation values from participants
    form_fields = ['s1', 's2', 's3']  
    # Set timeout count
    timeout_seconds = 60
    # Allow for subroup independence
    group_by_arrival_time = False

    # Provide player ID for template rendering
    def vars_for_template(self):
        subgroup_id = self.participant.vars.get("subgroup_id")
        id_in_subgroup = self.participant.vars.get("id_in_subgroup")

        # Get current player's period for templating
        self.player.participant.vars['periods_played'] += 1
        p_period = self.player.participant.vars['periods_played']
        # print(f"Round {self.round_number} | Group {self.group.id_in_subsession} | Subgroup {self.player.participant.vars['subgroup_id']}")
        
        return {
            'id': self.player.id_in_group,
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'timeout_seconds': self.timeout_seconds,
            'period': p_period,
            "group_index": self.participant.vars.get("group_index", "N/A")
        }

    # Store the proposer's id and submitted allocation before proceeding
    def before_next_page(self, timeout_happened = False):
        subgroup_id = self.player.participant.vars.get('subgroup_id')
        proposer_id = self.player.id_in_group  

        # Determine the proposal based on timeout or real input
        if timeout_happened:
            allocation = {"s1": -10, "s2": -10, "s3": -10}
            self.participant.vars["timed_out"] = True
            self.drop_out_detected = True
            store_decision(self.player, "ProposerPage", "Timeout - Auto Proposal", allocation)
        else:
            allocation = {
                "s1": self.player.s1,
                "s2": self.player.s2,
                "s3": self.player.s3,
            }
            store_decision(self.player, "ProposerPage", "Submitted Proposal", allocation)

        # Load existing subgroup proposals from JSON field
        subgroup_proposals = json.loads(self.group.subgroup_proposals_str)

        # Add this player's proposal to the correct subgroup
        subgroup_key = str(subgroup_id)                     # Retrieve subgroup_id
        if subgroup_key not in subgroup_proposals:
            subgroup_proposals[subgroup_key] = []

        subgroup_proposals[subgroup_key].append({           # Add proposal
            "proposer_id": proposer_id,
            "proposal": allocation
        })

        # # Save updated proposals JSON string
        self.group.subgroup_proposals_str = json.dumps(subgroup_proposals)
        print(f"[DEBUG] Subgroup {subgroup_id} proposals so far: {subgroup_proposals[subgroup_key]}")

        # # If 3 proposals collected for the subgroup, select one randomly
        # if len(subgroup_proposals[subgroup_key]) == 3:
        #     # Load existing selected proposals (for all subgroups)
        #     selected_proposals = json.loads(self.group.selected_proposals_str)
        #     # Pick a random proposal from the current subgroup
        #     selected = random.choice(subgroup_proposals[subgroup_key])
        #     # Store it under the current subgroup ID
        #     selected_proposals[subgroup_key] = selected
        #     # Save updated selection back to the group field
        #     self.group.selected_proposals_str = json.dumps(selected_proposals)

        #     print(f"[DEBUG] Selected proposal for Subgroup {subgroup_id}: {selected}")
            
    # Validate input data
    def error_message(self, values):
        # Condition 1: All proposals (s1, s2, s3) are within 0 to 30 range 
        if any(values[key] < 0 or values[key] > 30 for key in ['s1', 's2', 's3']):
            return "Each proposal must be between 0 and 30."
        # Condition 2: Sum of all proposed values equal exactly 30
        if sum([values['s1'], values['s2'], values['s3']]) != 30:
            return "The total allocation must sum to exactly 30."

class SelectingPage(WaitPage):
    wait_for_all_groups = False
    timeout_seconds = 15

    def get_players_for_group(self):
        # Only wait for players in the same subgroup
        subgroup_id = self.player.participant.vars.get("subgroup_id")
        return [p for p in self.group.get_players() if p.participant.vars.get("subgroup_id") == subgroup_id]

    def is_ready(self):
        # Get subgroup ID
        subgroup_id = self.player.participant.vars.get("subgroup_id")
        players_in_subgroup = [
            p for p in self.group.get_players()
            if p.participant.vars.get("subgroup_id") == subgroup_id
        ]
        all_arrived = all(p._waiting_for_page() == self.__class__.__name__ for p in players_in_subgroup)
        return all_arrived or self.group.drop_out_detected

    @staticmethod
    def after_all_players_arrive(group: Group):
        # Load existing proposals
        subgroup_proposals = json.loads(group.subgroup_proposals_str)
        selected_proposals = json.loads(group.selected_proposals_str or '{}')

        # Identify all unique subgroup IDs in the group
        subgroup_ids = set(p.participant.vars.get("subgroup_id") for p in group.get_players())

        for subgroup_id in subgroup_ids:
            subgroup_key = str(subgroup_id)
            proposals = subgroup_proposals.get(subgroup_key, [])

            # Only select if not already selected and all 3 proposals were collected
            if subgroup_key not in selected_proposals and len(proposals) == 3:
                selected = random.choice(proposals)
                selected_proposals[subgroup_key] = selected
                print(f"[DEBUG] ✅ Subgroup {subgroup_id} selected proposal: {selected}")

        # Save updated selections
        group.selected_proposals_str = json.dumps(selected_proposals)


    # @staticmethod
    # def check_dropout_or_select(group: Group):
    #     # Don't select random proposal if dropout is detected
    #     if group.drop_out_detected:
    #         # If a dropout is detected, flag all players to be redirected
    #         for p in group.get_players():
    #             p.participant.vars['go_to_dropout_notice'] = True
    #         print("[SelectingPage] Dropout detected — participants flagged for redirect.")
    #         return  # exit early — no selection

    def before_next_page(self):
        if self.timeout_happened:
            print(f"[WaitOrTimeoutPage] Timeout for participant {self.participant.code}")
        else:
            print(f"[WaitOrTimeoutPage] Proceeding after all arrived: {self.participant.code}")

    def vars_for_template(self):
        return{
            "timeout_seconds": self.timeout_seconds,
            "subgroup_id": self.participant.vars.get("subgroup_id")
        }



# Display selected proposal
class SelectedProposalPage(BasePage):
    # Set autosubmit count
    timeout_seconds = 10

    # Retrieve the stored proposer ID from group model and display
    def vars_for_template(self):
        subgroup_id = self.player.participant.vars.get("subgroup_id")
        id_in_subgroup = self.player.participant.vars.get("id_in_subgroup")
        subgroup_key = str(subgroup_id)

        # Load selected proposals dictionary
        selected_proposals = json.loads(self.group.selected_proposals_str)

        # Return default display if no selection yet
        if subgroup_key not in selected_proposals:
            return {
                "player_id": self.player.id_in_group,
                'subgroup_id': subgroup_id,
                'id_in_subgroup': id_in_subgroup,
                "selected_proposer_id": "Unknown", 
                "selected_proposal": {}, 
                "relevant_proposal": {},
                "timeout_occurred": False,
                "timeout_seconds": self.timeout_seconds
            }

        selected_proposal = selected_proposals[subgroup_key]
        proposer_id = selected_proposal.get("proposer_id")
        relevant_proposal = selected_proposal.get("proposal", {})

        # Check if proposer timed out
        timeout_flag = False
        for p in self.group.get_players():
            if p.id_in_group == proposer_id and p.participant.vars.get("timed_out", False):
                timeout_flag = True
                break

        return {
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'selected_proposer_id': f"Participant {proposer_id}" if proposer_id else "Unknown",
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
    timeout_seconds = 60

    # Pass proposal data to the template
    def vars_for_template(self):
        subgroup_id = self.player.participant.vars.get("subgroup_id")
        id_in_subgroup = self.player.participant.vars.get("id_in_subgroup")
        subgroup_key = str(subgroup_id)

        # Load selected proposals per subgroup
        selected_proposals = json.loads(self.group.selected_proposals_str)

        if subgroup_key not in selected_proposals:
            print(f"[DEBUG] No selected proposal found for subgroup {subgroup_key}")
            selected_proposal = {}
            relevant_proposal = {}
            proposer_display = "Unknown"
        else:
            selected_proposal = selected_proposals[subgroup_key]
            relevant_proposal = selected_proposal.get("proposal", {})
            proposer_id = selected_proposal.get("proposer_id")
            proposer_display = f"Participant {proposer_id}" if proposer_id else "Unknown"
            print(f"\n[DEBUG] VoterPage - Subgroup {subgroup_key} selected proposal: {selected_proposal}")

        return {
            'id': self.player.id_in_group,
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'selected_proposer_id': proposer_display,
            'selected_allocation': relevant_proposal,
            'timeout_seconds': self.timeout_seconds
        }

    def before_next_page(self):
        # TIMEOUT: Handle case for when a timeout/dropout occurs    
        if self.timeout_happened:
            self.player.vote = False
            self.drop_out_detected = True
            self.participant.vars["timed_out"] = True
            store_decision(self.player, "VoterPage", "Timeout - Auto Vote", {"vote": False})
        else:
            store_decision(self.player, "VoterPage", "Voted", {"vote": self.player.vote})

# Select random proposal once all players have submitted
class VoterWaitPage(BaseWaitPage):
    def before_next_page(self):
        subgroup_id = self.player.participant.vars.get("subgroup_id")
        subgroup_key = str(subgroup_id)

        # Load all votes (group-level JSON string)
        votes_by_subgroup = json.loads(self.group.all_votes_str)

        # Debug print
        print(f"[DEBUG] Votes so far: {votes_by_subgroup}")

        if subgroup_key in votes_by_subgroup:
            subgroup_votes = votes_by_subgroup[subgroup_key]
            print(f"[DEBUG] Subgroup {subgroup_key} has {len(subgroup_votes)} votes")

            # Confirm that all 3 subgroup members have voted
            if len(subgroup_votes) == 3:
                print(f"[CONFIRMED] All 3 players in Subgroup {subgroup_key} have voted.")
                # Optional: compute approval, store result, etc.


class ResultsPage(BasePage):

    timeout_seconds = 30

    def vars_for_template(self):
        subgroup_id = self.player.participant.vars.get("subgroup_id")
        id_in_subgroup = self.player.participant.vars.get("id_in_subgroup")
        subgroup_key = str(subgroup_id)

        # Load selected proposals
        selected_proposals = json.loads(self.group.selected_proposals_str)

        # Fallback if no proposal found
        if subgroup_key not in selected_proposals:
            return {
                'subgroup_id': subgroup_id,
                'id_in_subgroup': id_in_subgroup,
                'selected_proposer_id': "Unknown",
                'relevant_proposal': {},
                'total_votes': 0,
                'approved': False,
                'player_earnings': {},
                'your_earnings': 0,
                'period': self.participant.vars.get('periods_played', 0),
                'player_id': self.player.id_in_group,
                'timeout_seconds': self.timeout_seconds
            }

        selected_proposal = selected_proposals[subgroup_key]
        relevant_proposal = selected_proposal.get("proposal", {})
        proposer_id = selected_proposal.get("proposer_id")
        proposer_display = f"Participant {proposer_id}" if proposer_id else "Unknown"

        # Voting Results: only from players in the same subgroup
        subgroup_players = [p for p in self.group.get_players()
                            if p.participant.vars.get("subgroup_id") == subgroup_id]
        total_votes = sum(p.vote for p in subgroup_players)
        proposal_approved = total_votes >= 2
        self.group.approved = proposal_approved  # Optional if needed later

        # Earnings Results
        player_earnings = {}
        for p in subgroup_players:
            current_period = p.participant.vars.get("periods_played", 0)
            player_key = f's{p.id_in_group}'
            earnings = cu(relevant_proposal.get(player_key, 0)) if proposal_approved else cu(0)
            p.earnings = earnings
            player_earnings[f'Participant {p.id_in_group}'] = earnings

            print(f"\n[DEBUG] Before storing earnings, all_earnings for Player {p.id_in_group}: {p.all_earnings}")
            p.store_earnings(p.id_in_group, current_period, earnings)
            print(f"\n[DEBUG] After storing earnings, all_earnings for Player {p.id_in_group}: {p.all_earnings}")

        # Handle final earnings only if in last round (optional)
        if self.group.current_period == 5:
            for p in self.group.get_players():
                p.final_earnings()

        # Period for display
        p_period = self.participant.vars.get('periods_played', 0)

        return {
            'selected_proposer_id': proposer_display,
            'relevant_proposal': relevant_proposal,
            'total_votes': total_votes,
            'approved': proposal_approved,
            'player_earnings': player_earnings,
            'your_earnings': int(self.player.earnings),
            'period': p_period,
            'player_id': self.player.id_in_group,
            'timeout_seconds': self.timeout_seconds
        }

# Ensures that all players complete their periods before stopping the game
class SyncBottom(BaseWaitPage):

    wait_for_all_groups = False
    body_text = 'Please wait for the other groups to finish voting...'

    # Ensure players return to SyncTop if they haven't completed 5 periods
    def is_displayed(self):
        return self.participant.vars.get('periods_played', 0) < Constants.no_periods  

    @staticmethod
    def after_all_players_arrive(group: Group):

        # Access session data
        session = group.subsession.session  

        # Get the group_index of the current group (assumes everyone in group shares the same one)
        group_index = group.get_players()[0].participant.vars.get('group_index')

        # Filter players who belong to the same 9-block group
        same_group_players = [
            p for p in group.subsession.get_players()
            if p.participant.vars.get('group_index') == group_index
        ]

        # Check if all players have  completed 5 periods
        all_finished = all(p.participant.vars.get('periods_played', 0) >= Constants.no_periods for p in same_group_players)
        print(f"\n[DEBUG] 9-block group {group_index} completed? → {all_finished}")

        if not all_finished:
            print(f"[DEBUG] → Not all players in group {group_index} finished. Sending them back to SyncTop.\n")
            for p in same_group_players:
                if p.participant.vars.get('periods_played', 0) < Constants.no_periods:
                    p.participant.vars['next_period'] = True
        else:
            print(f"[DEBUG] ✅ All players in group {group_index} have finished.\n")

        # Set group-level flag
        group.session_finish = all_finished  # only this group's status
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
    timeout_seconds = 120

    def is_displayed(self):
        # Display only if player selected for priming treatment
        return self.participant.vars.get("is_priming", False) and self.round_number == 1

    def vars_for_template(self):
        # Pass the player's gender selection to template
        return {
            "selected_gender": self.participant.vars.get("selected_gender", "Not specified"),
            "gender_expression": self.participant.vars.get("gender_expression", "Not specified"),
            "group_index": self.participant.vars.get("group_index", "N/A"),
            'timeout_seconds': self.timeout_seconds
        }
    
    def before_next_page(self):
        # Record Response
        store_survey_response(self.player, "Priming", self.form_fields)


class Baseline(Page):
    form_model = 'player'
    form_fields = ['qp1', 'qp3']
    timeout_seconds = 120

    def is_displayed(self):
        # Display only if player selected for baseline treatment
        return not self.participant.vars.get("is_priming") and self.participant.vars.get('periods_played', 0) >= Constants.no_periods 

    def vars_for_template(self):
        # Pass the player's gender selection to template
        return {
            "selected_gender": self.participant.vars.get("selected_gender", "Not specified"),
            "gender_expression": self.participant.vars.get("gender_expression", "Not specified"),
            "group_index": self.participant.vars.get("group_index", "N/A"),
            'timeout_seconds': self.timeout_seconds
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

    # Final Survey
    Part1a,             # Voting and Proposing Considerations
    Part1b,             # Retaliation, mwc, mwc_others
    Part1c,             # atq 1, 2, 3 (ie. math questions)
    Part1d,             # Age, Risk
    Part1e,             # Occupation, Volunteer, (Volunteer Hours)
    Part2a,             # Econ Courses, Party Like, Party, Party Prox
    Part2b,             # Plop_Unempl, Plop_Comp, Plop_Incdist, Plop_Priv, Plop_Luckeffort
    Part3,              # Religion, (Specify Religion)
    Part4,              # Parents' Place of Birth/Citizenship
    Part5,              # mwc_bonus, mwc_bonus_others, enjoy
    Part6,              # bonus question
    
    # Display Total Earnings 
    DropoutNotice,                      # Display to dropout player
    DropoutNoticeOtherPlayers,          # Display to all other players
    PaymentInfo,      
]
