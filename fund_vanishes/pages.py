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
import time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fund_vanishes.settings")
from django.core.files.storage import default_storage

# Set-up questions
NUM_ROUNDS = 5

# Timeout variables
PROPOSAL_TIMEOUT = 60                  # Proposer Page 
VOTE_TIMEOUT = 60                      # Voter Page
PROPOSAL_TIMEOUT_2 = 30                # 2nd Chance Proposer Page
VOTE_TIMEOUT_2 = 30                    # 2nd Chance Voter Page
RESULTS_TIMEOUT = 30                   # Results Page timeout

# Variables for progress bar 
INTRO_QUESTIONS = 4
SURVEY_PAGES = 12

# ---------------------------------------------------------------------------------------------------

# INTRO QUESTIONS

# Dropout detection for normal pages (all game pages inherit from this)
class BasePage(Page):
    def is_displayed(self):
        # Don't show page if dropout is detected
        return not self.group.drop_out_detected
        # return not self.participant.vars.get("dropout", False)

# Dropout detection for WaitPages
class BaseWaitPage(WaitPage):
    def is_displayed(self):
        # Don't show page if dropout is detected
        # return not self.group.drop_out_detected
        return not self.participant.vars.get("dropout", False)

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

# Show this page if player fails the quiz
# Displays failure message if the player fails the quiz after 3 attempts
class FailedPage(Page):
    def is_displayed(self):
        return self.participant.vars.get('redirect_to_failed', False) 

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
        self.player.participant.vars['periods_played'] += 2

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
    body_text = "Waiting for other participants..."

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


class GameStarts(Page):
    def is_displayed(self):
        return self.round_number == 1


# Submit Proposal Page: All players propose an allocation, then store
class ProposerPage(BasePage):
    # Store data collected in this page at the group level
    form_model = 'player'  
    # Collect allocation values from participants
    form_fields = ['s1', 's2', 's3']  
    # Set timeout count
    timeout_seconds = PROPOSAL_TIMEOUT
    # Allow for subroup independence
    group_by_arrival_time = False

    # Provide player ID for template rendering
    def vars_for_template(self):
        # Ensure that timeout is absolute
        if "expiry_timestamp_proposer" not in self.participant.vars:
            self.participant.vars["expiry_timestamp_proposer"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestamp_proposer"] - time.time()))

        # Subgroup ID
        subgroup_id = self.participant.vars.get("subgroup_id")
        # ID of player within subgroup
        id_in_subgroup = self.participant.vars.get("id_in_subgroup")

        # Get current player's period for templating
        if self.player.participant.vars['periods_played'] == 0:
            self.player.participant.vars['periods_played']+=1
        p_period = self.player.participant.vars['periods_played']
        # print(f"Round {self.round_number} | Group {self.group.id_in_subsession} | Subgroup {self.player.participant.vars['subgroup_id']}")
        
        return {
            'id': self.player.id_in_group,
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'timeout_seconds': self.timeout_seconds,
            'period': p_period,
            "group_index": self.participant.vars.get("group_index", "N/A"),
            "remaining_seconds": remaining
        }

    # Store the proposer's id and submitted allocation before proceeding
    def before_next_page(self, timeout_happened = False):
        # proposer_id = id_in_subgroup

        # Clean up timeout
        self.participant.vars.pop("expiry_timestamp_proposer", None)
        
        # Determine the proposal based on timeout or real input
        if self.timeout_happened:
            allocation = {"s1": -10, "s2": -10, "s3": -10}
            # allocation = {"s1": None, "s2": None, "s3": None}
            self.drop_out_detected = True
            self.participant.vars["timed_out"] = True
            store_decision(self.player, "ProposerPage", "Timeout - Auto Proposal", allocation)
            # self.player.participant.vars['periods_played'] -=1

            # Declare dropout
            # self.participant.vars["dropout"] = True
            # self.group.drop_out_detected = True
            # self.group.drop_out_finalized = True

            # Notify other players
            # for p in self.group.get_players():
            #     if p.participant.id != self.participant.id:  # exclude dropout
            #         p.participant.vars["go_to_notice"] = True
        else:
            allocation = {
                "s1": self.player.s1,
                "s2": self.player.s2,
                "s3": self.player.s3,
            }
            store_decision(self.player, "ProposerPage", "Submitted Proposal", allocation)

        subgroup_id = self.player.participant.vars.get('subgroup_id')
        id_in_subgroup = self.player.participant.vars.get('id_in_subgroup')
        proposer_id = self.player.participant.vars.get('id_in_subgroup')

        # Load existing subgroup proposals from JSON field
        subgroup_proposals = json.loads(self.group.subgroup_proposals_str)

        # Add this player's proposal to the correct subgroup
        subgroup_key = str(subgroup_id)                     # Retrieve subgroup_id
        if subgroup_key not in subgroup_proposals:
            subgroup_proposals[subgroup_key] = []

        subgroup_proposals[subgroup_key].append({           # Add proposal
            "proposer_id": id_in_subgroup,
            "proposal": allocation
        })

        # # Save updated proposals JSON string
        self.group.subgroup_proposals_str = json.dumps(subgroup_proposals)
        print(f"[DEBUG] Subgroup {subgroup_id} proposals so far: {subgroup_proposals[subgroup_key]}")
            
    # Validate input data
    def error_message(self, values):
        # Condition 1: All proposals (s1, s2, s3) are within 0 to 30 range 
        if any(values[key] < 0 or values[key] > 30 for key in ['s1', 's2', 's3']):
            return "Each proposal must be between 0 and 30."
        # Condition 2: Sum of all proposed values equal exactly 30
        if sum([values['s1'], values['s2'], values['s3']]) != 30:
            return "The total allocation must sum to exactly 30."


# Submit Proposal Page: All players propose an allocation, then store
class ProposerPage2(BasePage):
    # Store data collected in this page at the group level
    form_model = 'player'  
    # Collect allocation values from participants
    form_fields = ['s1', 's2', 's3']  
    # Set timeout count
    timeout_seconds = PROPOSAL_TIMEOUT_2
    # Allow for subroup independence
    group_by_arrival_time = False

    def is_displayed(self):
        return (
            self.participant.vars.get("timed_out", False) and not self.group.drop_out_finalized
        )

    # Provide player ID for template rendering
    def vars_for_template(self):
        # Ensure timeout is absolute
        if "expiry_timestamp_proposer2" not in self.participant.vars:
            self.participant.vars["expiry_timestamp_proposer2"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestamp_proposer2"] - time.time()))

        subgroup_id = self.participant.vars.get("subgroup_id")
        id_in_subgroup = self.participant.vars.get("id_in_subgroup")

        # Get current player's period for templating
        # self.player.participant.vars['periods_played'] -=2
        p_period = self.player.participant.vars['periods_played']
        # print(f"Round {self.round_number} | Group {self.group.id_in_subsession} | Subgroup {self.player.participant.vars['subgroup_id']}")
        
        return {
            'id': self.player.id_in_group,
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'timeout_seconds': self.timeout_seconds,
            'period': p_period,
            "group_index": self.participant.vars.get("group_index", "N/A"),
            "remaining_seconds": remaining
        }

    # Store the proposer's id and submitted allocation before proceeding
    def before_next_page(self, timeout_happened = False):
        # proposer_id = id_in_subgroup

        # Clean up timeout
        self.participant.vars.pop("expiry_timestamp_proposer2", None)

        # Determine the proposal based on timeout or real input
        if self.timeout_happened:
            allocation = {"s1": -10, "s2": -10, "s3": -10}
            # allocation = {"s1": None, "s2": None, "s3": None}
            self.drop_out_detected = True
            self.participant.vars["timed_out"] = True
            store_decision(self.player, "ProposerPage2", "Timeout - Auto Proposal", allocation)

            # Declare dropout
            self.participant.vars["dropout"] = True
            self.group.drop_out_detected = True
            self.group.drop_out_finalized = True

            # Notify other players
            for p in self.group.get_players():
                if p.participant.id != self.participant.id:  # exclude dropout
                    p.participant.vars["go_to_notice"] = True
        else:
            # self.player.participant.vars['periods_played'] += 1
            # Undeclare dropout
            self.drop_out_detected = False
            self.participant.vars["timed_out"] = False
            self.participant.vars["dropout"] = False
            self.group.drop_out_detected = False
            self.group.drop_out_finalized = False

            allocation = {
                "s1": self.player.s1,
                "s2": self.player.s2,
                "s3": self.player.s3,
            }
            store_decision(self.player, "ProposerPage2", "Submitted Proposal", allocation)


        subgroup_id = self.player.participant.vars.get('subgroup_id')
        id_in_subgroup = self.player.participant.vars.get('id_in_subgroup')
        proposer_id = self.player.participant.vars.get('id_in_subgroup')

        # Load existing subgroup proposals from JSON field
        subgroup_proposals = json.loads(self.group.subgroup_proposals_str)

        # Overwrite any existing proposal from this proposer
        subgroup_key = str(subgroup_id)                     # Retrieve subgroup_id
        if subgroup_key not in subgroup_proposals:
            subgroup_proposals[subgroup_key] = []

        # Overwrite logic: Remove any existing proposal from this proposer
        subgroup_proposals[subgroup_key] = [
           p for p in subgroup_proposals[subgroup_key] if p["proposer_id"] != id_in_subgroup 
        ]

        # Append the new proposal
        subgroup_proposals[subgroup_key].append({           # Add proposal
            "proposer_id": id_in_subgroup,
            "proposal": allocation
        })

        # # Save updated proposals as JSON
        self.group.subgroup_proposals_str = json.dumps(subgroup_proposals)
        print(f"[DEBUG] Subgroup {subgroup_id} proposals so far: {subgroup_proposals[subgroup_key]}")
            
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

    def is_displayed(self):
        return not self.participant.vars.get("dropout", False)

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
        # Define the timeout proposal to check against
        TIMEOUT_PROPOSAL = {"s1": -10, "s2": -10, "s3": -10}

        # Load existing proposals
        subgroup_proposals = json.loads(group.subgroup_proposals_str)
        selected_proposals = json.loads(group.selected_proposals_str or '{}')

        # Get unique subgroup IDs in the group
        subgroup_ids = set(p.participant.vars.get("subgroup_id") for p in group.get_players())

        for subgroup_id in subgroup_ids:
            subgroup_key = str(subgroup_id)
            proposals = subgroup_proposals.get(subgroup_key, [])

            # Filter out timeout proposals
            valid_proposals = [
                p for p in proposals if p["proposal"] != TIMEOUT_PROPOSAL
            ]

            # Only select if 3 proposals were collected (none of which are timeouts)
            if subgroup_key not in selected_proposals and len(valid_proposals) == 3:
                selected = random.choice(valid_proposals)
                selected_proposals[subgroup_key] = selected
                print(f"[DEBUG] ✅ Subgroup {subgroup_id} selected proposal: {selected}")
            else:
                print(f"[DEBUG] ⚠️ Skipping subgroup {subgroup_id}. Collected: {len(proposals)} | Valid: {len(valid_proposals)}")

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

    def vars_for_template(self):
        if "expiry_timestamp_selecting" not in self.participant.vars:
            self.participant.vars["expiry_timestamp_selecting"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestamp_selecting"] - time.time()))

        return{
            "timeout_seconds": self.timeout_seconds,
            "subgroup_id": self.participant.vars.get("subgroup_id"),
            "remaining_seconds": remaining
        }

    def before_next_page(self):
        # Clean up timeout
        self.participant.vars.pop("expiry_timestamp_selecting", None)

        if self.timeout_happened:
            print(f"[WaitOrTimeoutPage] Timeout for participant {self.participant.code}")
        else:
            print(f"[WaitOrTimeoutPage] Proceeding after all arrived: {self.participant.code}")




# Display selected proposal
class SelectedProposalPage(BasePage):
    # Set autosubmit count
    timeout_seconds = 10

    # Retrieve the stored proposer ID from group model and display
    def vars_for_template(self):
        # Ensure timeout is absolute
        if "expiry_timestamp_selected" not in self.participant.vars:
            self.participant.vars["expiry_timestamp_selected"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestamp_selected"] - time.time()))
        
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
                "timeout_seconds": self.timeout_seconds,
                "remaining_seconds": remaining
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
            'timeout_seconds': self.timeout_seconds,
            "remaining_seconds": remaining
        }
    
    def before_next_page(self):
        # Clean up timeout
        self.participant.vars.pop("expiry_timestamp_selected", None)

# Voting Page: Players vote on the selected proposal
class VoterPage(BasePage):
    form_model = 'player'  
    form_fields = ['vote'] 
    timeout_seconds = VOTE_TIMEOUT

    def is_displayed(self):
        return not self.participant.vars.get("dropout", False) and not self.group.drop_out_detected

    # Pass proposal data to the template
    def vars_for_template(self):
        # Ensure timeout is absolute
        if "voter_expiry_timestamp" not in self.participant.vars:
            self.participant.vars["voter_expiry_timestamp"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["voter_expiry_timestamp"] - time.time()))

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
            proposer_num = int(proposer_display.split()[-1])            # Extract the number
            print(f"\n[DEBUG] VoterPage - Subgroup {subgroup_key} selected proposal: {selected_proposal}")

        return {
            'id': self.player.id_in_group,
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'selected_proposer_id': proposer_display,
            'selected_proposer_num': proposer_num,
            'selected_allocation': relevant_proposal,
            'timeout_seconds': self.timeout_seconds,
            'remaining_seconds': remaining
        }

    def before_next_page(self):
        # Clean up timeout
        self.participant.vars.pop("voter_expiry_timestamp", None)

        # TIMEOUT: Handle case for when a timeout/dropout occurs    
        if self.timeout_happened:
            self.player.vote = False
            self.drop_out_detected = True
            self.participant.vars["timed_out"] = True
            
            # Declare dropout
            # self.participant.vars["dropout"] = True
            # self.group.drop_out_detected = True
            # self.group.drop_out_finalized = True

            # Notify other players
            # for p in self.group.get_players():
            #     if p.participant.id != self.participant.id:  # exclude dropout
            #         p.participant.vars["go_to_notice"] = True

            store_decision(self.player, "VoterPage", "Timeout - Auto Vote", {"vote": False})
        else:
            store_decision(self.player, "VoterPage", "Voted", {"vote": self.player.vote})


# Voting Page: Players vote on the selected proposal
class VoterPage2(BasePage):
    form_model = 'player'  
    form_fields = ['vote'] 
    timeout_seconds = VOTE_TIMEOUT_2

    # Only display if timeout is detected
    def is_displayed(self):
        return (
            self.participant.vars.get("timed_out", False) and not self.group.drop_out_finalized
        )

    # Pass proposal data to the template
    def vars_for_template(self):
        # Ensure timeout is absolute
        if "expiry_timestamp_voter2" not in self.participant.vars:
            self.participant.vars["expiry_timestamp_voter2"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestam_voter2"] - time.time()))

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
            proposer_num = int(proposer_display.split()[-1])            # Extract the number
            print(f"\n[DEBUG] VoterPage - Subgroup {subgroup_key} selected proposal: {selected_proposal}")

        return {
            'id': self.player.id_in_group,
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'selected_proposer_id': proposer_display,
            'selected_proposer_num': proposer_num,
            'selected_allocation': relevant_proposal,
            'timeout_seconds': self.timeout_seconds,
            'remaining_seconds': remaining
        }

    def before_next_page(self):
        # Clean up timeout
        self.participant.vars.pop("expiry_timestamp_voter2", None)

        # TIMEOUT: Handle case for when a timeout/dropout occurs    
        if self.timeout_happened:
            self.player.vote = False
            self.drop_out_detected = True
            self.participant.vars["timed_out"] = True
            
            # Declare dropout
            self.participant.vars["dropout"] = True
            self.group.drop_out_detected = True
            self.group.drop_out_finalized = True

            # Notify other players
            for p in self.group.get_players():
                if p.participant.id != self.participant.id:  # exclude dropout
                    p.participant.vars["go_to_notice"] = True

            store_decision(self.player, "VoterPage2", "Timeout - Auto Vote", {"vote": False})
        else:
            # Undeclare dropout and reset timeout flag
            self.drop_out_detected = False
            self.participant.vars["timed_out"] = False
            self.participant.vars["dropout"] = False
            self.group.drop_out_detected = False
            self.group.drop_out_finalized = False

            # Store decision
            store_decision(self.player, "VoterPage2", "Voted", {"vote": self.player.vote})



# Select random proposal once all players have submitted
class VoterWaitPage(WaitPage):
    def is_displayed(self):
        return not self.participant.vars.get("dropout", False) and not self.group.drop_out_detected

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

    form_model = 'player'  
    timeout_seconds = RESULTS_TIMEOUT

    def is_displayed(self):
        return not self.participant.vars.get("dropout", False) and not self.group.drop_out_detected

    def vars_for_template(self):
        # Ensure timeout is absolute
        if "expiry_timestamp_results" not in self.participant.vars:
            self.participant.vars["expiry_timestamp_results"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestamp_results"] - time.time()))

        # Get subgroup info for player
        subgroup_id = self.participant.vars.get("subgroup_id")          # Retrieve ID of the subgroup within the group
        id_in_subgroup = self.participant.vars.get("id_in_subgroup")    # Retrieve player's ID within their subgroup
        subgroup_key = str(subgroup_id)                                 # Convert subgroup_id to string to use as dict key§

        # Load selected proposals
        selected_proposals = json.loads(self.group.selected_proposals_str)

        # Case 1: Fallback if no proposal found ---------------------------------------------
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
                'period': period,
                'player_id': self.player.id_in_group,
                'timeout_seconds': self.timeout_seconds,
                'remaining_seconds': remaining
            }

        # Case 2: Regular Case  ---------------------------------------------

        # Retrieve proposal and proposer for the subgroup
        selected_proposal = selected_proposals[subgroup_key]
        relevant_proposal = selected_proposal.get("proposal", {})
        proposer_id = selected_proposal.get("proposer_id")
        proposer_display = f"Participant {proposer_id}" if proposer_id else "Unknown"

        # Get players in the same subgroup
        subgroup_players = [p for p in self.group.get_players()
                            if p.participant.vars.get("subgroup_id") == subgroup_id]

        # Count votes and check if proposal is approved
        total_votes = sum(p.vote for p in subgroup_players)
        proposal_approved = total_votes >= 2
        self.group.approved = proposal_approved    # Store approval status

        # Earnings Results
        player_earnings = {}                       # Track subgroup earnings

        # Collect vote info for each player in subgroup
        player_votes = []
        for p in subgroup_players:
            vote_text = "Yes" if p.vote else "No"
            player_label = f"Player {p.participant.vars.get('id_in_subgroup', '?')}"
            player_votes.append({
                'label': player_label,
                'vote': vote_text,
                'is_yes': p.vote == 1  # Used to determine color
            })

        for p in subgroup_players:
            # Get number of periods this player has already played
            current_period = p.participant.vars.get("periods_played", 0)
            # Construct a key based on their ID within the subgroup
            player_id_subgroup = p.participant.vars.get("id_in_subgroup")
            player_key = f's{player_id_subgroup}'
            # player_key = f's{id_in_subgroup}'
            # If the proposal was approved, fetch that player's earnings from the proposal dict
            earnings = cu(relevant_proposal.get(player_key, 0)) if proposal_approved else cu(0)
            # Set the player's current round earnings to the computed amount
            p.earnings = earnings
            # Store this player's earnings in a summary dictionary for debugging/logging
            player_earnings[f'Participant {p.id_in_group}'] = earnings

            print(f"\n[DEBUG] Before storing earnings, all_earnings for Player {id_in_subgroup}: {p.all_earnings}")
            
            # Store the player's earnings
            p.store_earnings(self.player.id_in_group, current_period, earnings)
            
            print(f"\n[DEBUG] After storing earnings, all_earnings for Player {id_in_subgroup}: {p.all_earnings}")

        # Handle final earnings only if in last round (optional)
        if self.group.current_period == 5:
            for p in self.group.get_players():
                p.final_earnings()

        # # Period for display
        p_period = self.participant.vars.get('periods_played', 0)

        player_rows = []
        for p in subgroup_players:
            sid = p.participant.vars.get("id_in_subgroup")
            label = f"Player {sid}" + (" (You)" if sid == id_in_subgroup else "")
            token_amount = relevant_proposal.get(f"s{sid}", 0)
            vote = "Yes" if p.vote else "No"
            vote_color = "red" if p.vote else "green"

            player_rows.append({
                'label': label,
                'tokens': token_amount,
                'vote': vote,
                'vote_color': vote_color,
            })

        #     # Store earnings for the player
        #     current_period = p.participant.vars.get("periods_played", 0)
        #     p.earnings = cu(token_amount if proposal_approved else 0)
        #     # Make sure to store using ID in group
        #     p.store_earnings(p.id_in_group, current_period, p.earnings)


        return {
            'subgroup_id': subgroup_id,
            'id_in_subgroup': id_in_subgroup,
            'selected_proposer_id': proposer_display,
            'relevant_proposal': relevant_proposal,
            'total_votes': total_votes,
            'approved': proposal_approved,
            # 'player_earnings': player_earnings,
            'your_earnings': int(self.player.earnings),
            'period': p_period,
            'timeout_seconds': self.timeout_seconds,
            'remaining_seconds': remaining,
            'player_votes': player_votes,
            # 'player_rows': player_rows,
            'player_rows': sorted(player_rows, key=lambda row: int(row['label'].split()[1])),
        }
    
    def before_next_page(self):
        # Clean up timeout
        self.participant.vars.pop("expiry_timestamp_results", None)
        # Increment Period
        self.player.participant.vars['periods_played'] += 1

# Ensures that all players complete their periods before stopping the game
class SyncBottom(BaseWaitPage):

    wait_for_all_groups = False
    body_text = 'Please wait for the other groups to finish voting...'

    # Ensure players return to SyncTop if they haven't completed 5 periods
    def is_displayed(self):
        return self.participant.vars.get('periods_played', 0) < Constants.no_periods and not self.participant.vars.get("dropout", False) and not self.group.drop_out_detected

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
        return True  # Keep the page displayed
        # return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False) and not self.group.drop_out_detected

    def before_next_page(self):
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1

# ---------------------------------------------------------------------------------------------------

# DROPOUT NOTICE PAGES

class AreYouThere(BasePage):
    timeout_seconds = 15

    def is_displayed(self):
        return (
            self.participant.vars.get("timed_out", False) and not self.group.drop_out_finalized
        )

    def vars_for_template(self):
        # Ensure that timeout is absolute
        if "expiry_timestamp" not in self.participant.vars:
            self.participant.vars["expiry_timestamp"] = time.time() + self.timeout_seconds
        remaining = max(0, int(self.participant.vars["expiry_timestamp"] - time.time()))

        return {
            'remaining_seconds': remaining
        }

    def before_next_page(self):
        if self.timeout_happened:
            # The player did NOT click "Yes, I'm here!"
            self.participant.vars['timed_out'] = True
            # Also set the GROUP-LEVEL dropout flag
            self.group.drop_out_detected = True
            self.participant.vars["dropout"] = True
            self.group.drop_out_finalized = True
        else:
            # Clean up timeout
            self.participant.vars.pop("expiry_timestamp", None)
            pass
            # # Reset the flag for future rounds or pages
            # self.participant.vars["timed_out"] = False


# Welcome Page to Survey
class DropoutNotice(Page):
    timeout_seconds = 30
    
    # Show this page to 
    def is_displayed(self):
        return self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        rounds_played = self.subsession.round_number  # Current round number

        payment_message = (
            "Since you have dropped out of the game, no payment shall be issued."
        )

        return {
            "rounds_played": rounds_played,
            "payment_message": payment_message,
            "timeout_seconds": self.timeout_seconds
        }


class DropoutNoticeOtherPlayers(Page):
    timeout_seconds = 30
    
    # Show this page to all remaining players if a dropout is detected in the group
    def is_displayed(self):
        return self.group.drop_out_detected and not self.participant.vars.get("dropout", False)

    def before_next_page(self):
        # Mark that dropout has been handled
        self.group.drop_out_finalized = True

    def vars_for_template(self):
        rounds_played = self.subsession.round_number  # Current round number

        if rounds_played == 1:
            payment_message = (
                "No rounds were completed for this session. You will receive the fixed participation fee."
            )

        elif rounds_played < 3:
            payment_message = (
                "Since fewer than 2 rounds were completed, your final payment will be based on the 1 round completed."
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
            # Update total_bonus to 0 for dropoutee
            final_earnings_data["total_bonus"] = 0
    

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
        store_earnings(self.player, {
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

class Part1(Page):
    form_model = 'player'
    form_fields = ['cmt_propr', 'cmt_vtr']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        self.participant.vars["surveyStep"] = self.participant.vars.get("surveyStep", 1)
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)
    
    def vars_for_template(self):
        return {
            "survey_step": 1,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Save participant data to CSV when they submit responses
        store_survey_response(self.player, "Part1", self.form_fields)
        
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part2(Page):
    form_model = 'player'
    form_fields = ['age', 'risk','occ']

    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False) 
    
    def vars_for_template(self):
        return {
            "survey_step": 2,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part2", self.form_fields)
        # Increase progress bar
        self.participant.vars['surveyStep'] += 1


class Part3(Page):
    form_model = 'player'
    form_fields = ['power_q1a', 'power_q1b', 'power_q2', 'power_q3']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 3,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part3", self.form_fields)
        # Increase survey step when the player moves to the next page
        # self.participant.vars['surveyStep'] += 1


class Part4(Page):
    form_model = 'player'
    form_fields = ['atq_1', 'atq_2', 'atq_3']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            "survey_step": 4,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part4", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part5(Page):
    form_model = 'player'
    form_fields = ['econ', 'party_like', 'party', 'other_party','party_prox']
    # form_fields = ['econ', 'party_like', 'party', 'party_prox']

    def is_displayed(self):
        # Display page only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 5,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }
    
    def before_next_page(self):
        if self.player.party_like != '1':
            self.player.party = ''
            self.player.party_prox = ''

        if self.player.party != '4':
            self.player.other_party = ''

        # Record response
        store_survey_response(self.player, "Part5", self.form_fields)
        # Increase survey step when the player moves to the next page
        # If user didn't select "I use a different term"


class Part6(Page):
    form_model = 'player'
    # form_fields = ['plop_unempl', 'plop_comp', 'plop_incdist']
    form_fields = ['plop_unempl', 'plop_comp', 'plop_incdist','plop_priv', 'plop_luckeffort', 'democracy_obedience']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            "survey_step": 6,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part6", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Part7(Page):
    form_model = 'player'
    form_fields = ['rel', 'rel_spec','rel_other']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 7,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        if self.player.rel != '1':
            self.player.rel_spec = ''
        
        if self.player.rel_spec != '7':
            self.player.rel_other = ''
        # Record response
        store_survey_response(self.player, "Part7", self.form_fields)


class GenderAttitudes(Page):
    form_model = 'player'
    form_fields = ['gender_q1', 'gender_q2', 'gender_q3', 'gender_q4']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True 
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 8,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "GenderAttitudes", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class MWC(Page):
    form_model = 'player'
    form_fields = ['mwc', 'mwc_others']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True and self.player.id_in_group % 2 == 1  # odd-numbered players
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False) and self.player.id_in_group % 2 == 1  # odd-numbered players

    def vars_for_template(self):
        return {
            "survey_step": 9,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        } 
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "MWC", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class MWC_BONUS(Page):
    form_model = 'player'
    form_fields = ['mwc_bonus', 'mwc_bonus_others']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True and self.player.id_in_group % 2 == 0
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False) and self.player.id_in_group % 2 == 0

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 9,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "MWC_BONUS", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class SchwartzHierarchy(Page):
    form_model = 'player'
    form_fields = ['social_power', 'wealth', 'authority', 'humble', 'influential']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        field_descriptions = {
            "social_power": "control over others, dominance",
            "wealth": "material possessions, money",
            "authority": "the right to lead or command",
            "humble": "modest, self-effacing",
            "influential": "having an impact on people and events"
        }
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 10,
            "total_steps": SURVEY_PAGES,  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "SchwartzHierarchy", self.form_fields)
        # Increase survey step when the player moves to the next page
        # self.participant.vars['surveyStep'] += 1


class Part8(Page):
    form_model = 'player'
    form_fields = ['retaliation', 'retaliation_other']

    # @staticmethod
    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            "survey_step": 11,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        } 
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Part8", self.form_fields)
        # Increase survey step when the player moves to the next page
        self.participant.vars['surveyStep'] += 1


class Bonus(Page):
    form_model = 'player'
    form_fields = ['bonus','enjoy']

    def is_displayed(self):
        # Display only if offer was accepted
        # return True
        return self.participant.vars.get('periods_played', 0) >= Constants.no_periods and not self.participant.vars.get("dropout", False)

    def vars_for_template(self):
        return {
            # "survey_step": self.participant.vars.get("surveyStep", 1),
            "survey_step": 12,
            "total_steps": SURVEY_PAGES  # Adjust based on survey length
        }

    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Bonus", self.form_fields)
        # Increase survey step when the player moves to the next page
        # self.participant.vars['surveyStep'] += 1


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

    # Main game loop - 5 times per player
    SyncTop,              # Where groups of 9 are set
    Priming,              # Only show for priming treatment groups

    CalculatePage,        # Grouping Page - Continue

    WaitingPage,          # Wait Page 1  
    GameStarts,  
    ProposerPage,         
    AreYouThere,          # Declare Dropout - If no response    # Timeout = 15 seconds   
    ProposerPage2,  

    SelectingPage,        # Wait Page 2                         # Timeout = 15 seconds

    VoterPage,            # Players vote accept / reject
    AreYouThere,          # Declare Dropout - If no response
    VoterPage2,  

    VoterWaitPage,        # Wait Page 3 (Detect Dropout) 
    ResultsPage,          # Show if proposal is accepted / rejected
    SyncBottom,           # Redirect back to SyncTop until all periods compelted

    SurveyPage,
    Baseline,             # Only show for baseline treatment groups

    # Final Survey
    Part1,                  # Voting and Proposing Considerations
    Part2,                  # Age, Risk, Occupation
    Part3,                  # Power index
    Part4,                  # atq 1, 2, 3 (ie. math questions)
    Part5,                  # Econ Courses, Party Like, Party, Party Prox
    Part6,                  # plop_unempl, plop_comp, plop_incdist, plop_priv, plop_luckeffort, democracy_obedience
    Part7,                  # Religion, (Specify Religion)
    GenderAttitudes,        # Gender attitudes
    MWC,                    # Assign to even ID players
    MWC_BONUS,              # Assign to odd ID players
    SchwartzHierarchy,      # Schwartz hierarchy
    Part8,                  # Retaliation, Retaliation_Other
    Bonus,                  # bonus + enjoy question
    
    # Display Total Earnings 
    DropoutNotice,                      # Display to dropout player
    DropoutNoticeOtherPlayers,          # Display to all other players
    PaymentInfo,      
]
