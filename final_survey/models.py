# Defines players, groups, session logic, and game state
import json
import csv
import os
import random
from otree.api import *
from .utils import store_intro
from datetime import datetime
import pycountry

# ------------------------

# Variables and helper functions for drop-down selection questions

# Get list of all country names using pycountry
COUNTRIES = sorted([country.name for country in pycountry.countries])
COUNTRIES.insert(0, "Other (please specify)")  # Append to the beginning of the list

def load_language_choices():
    filepath = os.path.join(os.path.dirname(__file__), 'iso_639_3.csv')
    choices = []

    with open(filepath, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row['Code'].strip()
            name = row['Language'].strip()
            if code and name:
                choices.append((code, name))

    # Add "other" option to the beginning of list
    choices.insert(0, (000, "Other (please specify)")) 

    return choices

# -----------------------

class Constants(BaseConstants):
    name_in_url = 'final_survey'
    players_per_group = None                # Commented out for dynamic group formation 
    num_rounds = 5                          # Overall round loop
    no_periods = 5                          # Custom counter
    total_tokens = 30
    token_value = 0.4                       # 4 tokens = 1 USD

def creating_session(subsession):
    session = subsession.session

    session.list_players_waiting = '[]'

    #   PRIMING/BASELINE ASSIGNMENT =================================================

    # Ensure every participant has a period count
    for player in subsession.get_players():     
        # Shorter reference
        participant = player.participant 

        # Assign prolific_id safely
        player.prolific_id = participant.label or participant.vars.get('prolific_id', 'NA')

        # Randomly assign player for either priming or baseline treatment
        # if "is_priming" not in participant.vars:            
        #     participant.vars["is_priming"] = random.choice([True, False])
        player.is_priming = player.participant.vars.get('is_priming', False)
        
        # Ensure this carries over to the player's instance for this round
        # player.is_priming = participant.vars["is_priming"]
        store_intro(player)

        # print(f"Player {player.id_in_group} in group {player.group.id_in_subsession} → {'Priming' if player.is_priming else 'Baseline'}")

        player.participant.is_dropout = False               # No dropouts initially
        player.participant.seed = random.randint(1,100)     # Random seed for experiments
       
        # Assign roles only in the first round
        if "player_role" not in participant.vars:
            participant.vars["player_role"] = random.choice(["Proposer", "Voter"])  

        # Restore role for each new Player instance
        player.player_role = participant.vars["player_role"]
        
        # Ensure players have period tracking initialized
        if 'periods_played' not in player.participant.vars:
            player.participant.vars['periods_played'] = 0   # ✅ Initialize periods to 0

        # Initialize 'next_period' to avoid KeyError
        if 'next_period' not in player.participant.vars:
            player.participant.vars['next_period'] = False


class Subsession(BaseSubsession):
    creating_session = creating_session

    @staticmethod
    def group_by_arrival_time_method(subsession, waiting_players):
        
        eligible = [p for p in waiting_players]    # Create a list of players in SyncTop page
        group_size = 3

        # Create group
        if (len(eligible)) >= group_size:
            # Randomly pick 9 from the list of available players
            selected = random.sample(eligible, group_size)

            # Determine group index by checking how many groups have been created so far
            existing_groups = subsession.get_groups()
            group_index = len(existing_groups)  # 1-based index

            # Assign priming/baseline treatment
            is_priming = group_index % 2 == 1  # Odd = priming, even = baseline

             # Create a shared identifier for this 9‑player “super‑group”
            group_id_9 = f"g9_{selected[0].id_in_subsession}"
            # Write group metadata into each participant’s vars for later rounds
            for p in selected:
                p.participant.vars["group_id_9"] = group_id_9
                p.participant.vars["group_members"] = [q.id_in_subsession for q in selected]
                p.participant.vars["has_synced"] = True
                p.participant.vars["is_priming"] = is_priming 
                p.participant.vars["group_index"] = group_index 
                # Also assign on player object for easy access
                p.is_priming = is_priming

            # Server‑side debug log
            print(f"[DEBUG] round 1 – formed 9‑block {group_id_9}")

            # Initialize period counter for the group
            for p in selected:
                if 'periods_played' not in p.participant.vars:
                    p.participant.vars['periods_played'] = 0    # Initialize period count

            print(f"[DEBUG] formed 9‑block {group_id_9} → {'Priming' if is_priming else 'Baseline'}")

            # Returning the list lets oTree create this group and move on
            return selected
        
        # Fewer than nine → keep waiting
        return None
    pass

    # @staticmethod
    # def group_by_arrival_time_method(self, waiting_players):

    #     # ROUND 1 ONLY: Form groups of 9 and assign subgroups
    #     if self.round_number == 1:
    #         # Filter out dropouts
    #         eligible = [p for p in waiting_players if not p.participant.vars.get("dropout", False)]
            
    #         # Only group when exactly 9 players have arrived
    #         if len(waiting_players) >= 3:
    #             selected = waiting_players[:3]
    #             random.shuffle(selected)

    #             # # Assign 3-player subgroups within the 9
    #             # for i, p in enumerate(selected):
    #             #     # Use first player's ID as group-of-9 ID for efficiency
    #             #     p.group_id_9 = selected[0].id_in_subsession  # Use 1st player's ID as group ID
    #             #     # Divide into subgroups of 3 players
    #             #     p.subgroup_id = (i // 3) + 1  # Subgroups: 1, 2, 3

    #             print(f"[DEBUG] Group of 9 formed: {[p.participant.code for p in selected]}")
    #             # Return the selected group to proceed.
    #             return selected
    pass

    

# Group-level data
class Group(BaseGroup):
    
    # STATE TRACKING ---------------------------------------------------------
    
    # Group Period
    current_period = models.IntegerField(initial=0)
    group_id_9 = models.IntegerField()      # Store the ID of the group of 9
    subgroup_id = models.IntegerField()     # Store the subgroup ID (1, 2, or 3)
    session_finish = models.BooleanField(initial=False)

    # Dropout Detection
    drop_out_detected = models.BooleanField(initial=False)
    drop_out_finalized = models.BooleanField(initial=False)  # NEW FIELD

    # Function to create subgroups
    def set_subgroups(self):
        players = self.get_players()
        random.shuffle(players)
        subgroups = [players[i:i+3] for i in range(0, len(players), 3)]
        for i, subgroup in enumerate(subgroups):
            for p in subgroup:
                p.subgroup_id = i + 1  # Optional: tag each player with their subgroup ID

    def check_dropout_or_select(self):
        if self.drop_out_detected:
            for p in self.get_players():
                p.participant.vars['go_to_dropout_notice'] = True
        else:
            proposals = json.loads(self.all_proposals_str)
            if len(proposals) == 3:
                self.select_random_proposal()

    # SUBMIT PROPOSAL PAGE ---------------------------------------------------------
    
    # Stores all proposals for this period as a JSON string (list of dictionaries)
    all_proposals_str = models.LongStringField(initial="[]")
    # Stores all votes for this period 
    all_votes_str = models.LongStringField(initial="[]")
    
    # Function to store each new proposal instance (ie. proposer ID and allocation proposed)
    def store_proposal(self, proposer_id, proposal):
        # Store as dict (id-proposal)
        # Store as dict (period number[sub id-proposal dict])
       
        proposals = json.loads(self.all_proposals_str)                      # Convert JSON string to list
        proposals.append({"proposer": proposer_id, "proposal": proposal})   # Append new proposal
        self.all_proposals_str = json.dumps(proposals)                      # Convert back to JSON string

        # Print submitted proposals in the terminal
        print(f"\n[DEBUG] New proposal submitted by Player {proposer_id}: {proposal}")
        print(f"[DEBUG] All submitted proposals so far: {proposals}\n")

    # Function to retrieve all proposals as a list of dictionaries
    def get_all_proposals(self):
        return json.loads(self.all_proposals_str)

     # Function to get number of submitted proposals
    def get_proposal_count(self):
        return len(json.loads(self.all_proposals_str))

    # SELECTING PROPOSAL PAGE ---------------------------------------------------------
    
    # ID of the selected proposer in the group
    selected_proposer_id = models.IntegerField(initial=0) 
    selected_proposal = models.LongStringField(initial="{}")
    # Stores all proposals submitted, grouped by subgroup ID
    subgroup_proposals_str = models.LongStringField(initial='{}')
    # Stores the selected proposal per subgroup
    selected_proposals_str = models.LongStringField(initial='{}')
    
    # Store the SELECTED share allocation proposal for each participant
    s1 = models.IntegerField(label="Participant 1")   # Share allocated to first player
    s2 = models.IntegerField(label="Participant 2")   # Share allocated to second player
    s3 = models.IntegerField(label="Participant 3")   # Share allocated to third player

    # Function to select a random proposal
    def select_random_proposal(self):
        proposals = json.loads(self.all_proposals_str)   

        if len(proposals) == 3:                                 # Ensure all players have submitted
            selected = random.choice(proposals)                 # Randomly select a proposal
            self.selected_proposer_id = selected["proposer"]    # Store proposer ID
            self.selected_proposal = json.dumps(selected)       # Store proposal as JSON

            # Extract the selected proposal's allocation
            allocation = selected["proposal"] 

            # Store the selected allocation in s1, s2, s3 fields
            self.s1 = allocation["s1"]
            self.s2 = allocation["s2"]
            self.s3 = allocation["s3"]

            # Print the randomly selected proposal in the terminal
            print(f"\n[DEBUG] Randomly selected proposal by Player {self.selected_proposer_id}: {allocation}\n")

        else:
            print(f"\n[DEBUG] Not enough proposals submitted yet. Current count: {len(proposals)}/3\n")  
    
    # DECISION PAGE ---------------------------------------------------------

    # Indicates whether the proposal was approved by the majority (>2 approved)
    approved = models.BooleanField(initial=False)

    # Count the votes and determine if the proposal is approved.
    def process_votes(self):
        total_votes = sum([p.vote for p in self.get_players()])
        self.approved = total_votes >= 2  # Approval if 2 or more votes are 'Yes'

    # Stores all votes for this period 
    all_votes_str = models.LongStringField(initial="[]")
    
    # Function to store each new vote instance (ie. proposer ID and vote)
    # def store_proposal(self, proposer_id, vote):
    #     proposals = json.loads(self.all_votes_str)                      # Convert JSON string to list
    #     proposals.append({"proposer": proposer_id, "vote": vote})   # Append new proposal
    #     self.all_proposals_str = json.dumps(proposals)                      # Convert back to JSON string

    #     # Print submitted proposals in the terminal
    #     print(f"\n[DEBUG] New proposal submitted by Player {proposer_id}: {proposal}")
    #     print(f"[DEBUG] All submitted proposals so far: {proposals}\n")
    
    # PAYMENT ---------------------------------------------------------

    # Total fund available for distribution among participants
    Fund = models.IntegerField()

    # Stores decisions made in a period as a serialized string
    decision_array_str = models.LongStringField()
    # Stores results of each period as a serialized string
    period_results_array_str = models.LongStringField()

    # Number of shares available, constrained between 1 and 1000
    number_shares = models.IntegerField(label="Number of Shares", min=1, max=1000, initial=0)

class CalculateRounds(Page):
    def is_displayed(self):
        # Display only if agreement
        if self.player.participant.next_period == False and player.participant.skip_this_oTree_round == False:
            return True
        else:
            return False

    def before_next_page(player, timeout_happened):
        group = self.player.group
        # increase round
        self.player.participant.rounds += 1
        group.current_round = player.participant.rounds

        participant = self.player.participant
        if timeout_happened:
            participant.is_dropout = True
            self.player.dropout = True

    @staticmethod
    def get_timeout_seconds(player):
        participant = self.player.participant
        if participant.is_dropout:
            return 1  # instant timeout, 1 second
        else:
            return C.TIMELIMIT * 3


# Page that computes which player is the Proposer
class CalculateWaitpage(WaitPage):
    body_text = "The round will start shortly."

    # @staticmethod
    def after_all_players_arrive(group: Group):
        for player in group.get_players():
            group = self.player.group
            group.current_period = self.player.participant.periods

            # this is just so the calculations don't repeat for all players
            if self.player.id_in_group == 1:
                # randomly choose the ID of the player who will be the Proposer with probability pi
                group.id_proposer = int(np.random.choice(list(range(1, C.PLAYERS_PER_GROUP + 1)), 1, p=C.pi_list))
                # Now, assign the randomly chosen ID the PROPOSER ROLE
                proposer_player = group.get_player_by_id(group.id_proposer)
                proposer_player.role_player = "Proposer"

    @property
    def is_displayed(self):
        if self.player.participant.skip_this_oTree_round == False:
            return True
        else:
            return False


class Player(BasePlayer):
    # Participant set-up
    # prolific_id = models.StringField(default=str(" "))
    prolific_id = models.LongStringField(
        # blank=False,
        # min_length=24,
        # max_length=24,
        # error_messages={"min_length": "Must be exactly 24 characters."},
        label="Please enter your prolific ID:",
        # Add photo of sample prolific ID and where to find it
    )
    
    is_priming = models.BooleanField()                  # Randomly assign each player to either receive priming or baseline treatment
    group_id_9 = models.IntegerField()
    subgroup_id = models.IntegerField()

    
    # Store the SELECTED share allocation proposal for each participant
    s1 = models.IntegerField(label="Participant 1")   # Share allocated to first player
    s2 = models.IntegerField(label="Participant 2")   # Share allocated to second player
    s3 = models.IntegerField(label="Participant 3")   # Share allocated to third player

    def treatment(self):
        return "priming" if self.is_priming else "baseline"

    # Game set-up
    period_no = models.IntegerField(initial=0)
    player_role = models.StringField()  
    proposal = models.IntegerField(min=0, max=30)       # Proposal for token allocation
    vote = models.BooleanField(
        choices=[[True, 'Approve'], [False, 'Reject']],
        label="Do you accept this proposal?",
        widget=widgets.RadioSelect,
        blank = True,                                     # Allows vote to be None initially         
        initial = False                                     # Set default value to false termi    
    )      

    # Payment    
    earnings = models.CurrencyField(initial=0)          # Earnings for the period
    all_earnings = models.LongStringField(default="[]")
    final_payment = models.FloatField()
    feedback = models.LongStringField(blank=True)       # Post-experiment survey response



    # New earnings storing function which uses participant.vars which stays the same for entire session
    def store_earnings(self, player_id, round, earnings):
        participant = self.participant

        # Initialize storage if not yet set
        if "all_earnings" not in participant.vars:
            participant.vars["all_earnings"] = []

        # Avoid duplicate storage
        existing_rounds = {entry["round"] for entry in participant.vars["all_earnings"]}
        if round in existing_rounds:
            print(f"[DEBUG] Earnings for round {round} already stored. Skipping duplicate entry.")
            return
        
        # Append new earnings
        participant.vars["all_earnings"].append({"round": round, "earnings": float(earnings)})

        # Store back to Player model (if needed for display)
        self.all_earnings = json.dumps(participant.vars["all_earnings"])

        print(f"[DEBUG] Stored earnings for round {round}: {earnings}")
        print(f"[DEBUG] All earnings so far: {self.all_earnings}")


    # STORE ROUND DATA -----------------------------------------------
    def store_round_data(self):
        participant = self.participant

        # Ensure storage exists
        if "round_data" not in participant.vars:
            participant.vars["round_data"] = []

        # Append the current round's data
        participant.vars["round_data"].append({
            "round": self.round_number,
            "earnings": self.earnings,
            "proposal": self.proposal,
            "vote": self.vote
        })

        print(f"[DEBUG] Stored data for round {self.round_number}: {participant.vars['round_data']}")



    #####################################################################################

 
    #------------------------------------------------------------------------------------------------------------------------------------
    
    # FINAL SURVEY QUESTIONS
    
    # Part 1a ----------------------
    cmt_propr = models.LongStringField(
        label="In the rounds where you were a proposer, what considerations did you take into account when proposing a distribution?",
    )
    cmt_vtr = models.LongStringField(
        label="In the rounds where you were a voter, what considerations did you take into account, when voting on a distribution?",
    )

    # Part 1b ----------------------

    retaliation = models.StringField(
        choices=[[1, "1 (Strongly Disagree)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
                 [7, "7 (Strongly Agree)"]],
        label="\"If I feel that someone has wronged me, I will retaliate if given the possibility to do so.\" To what "
              "extent do you agree with the previous statement, where 1 means strongly disagree and 7 strongly agree?",
        widget=widgets.RadioSelect,
    )
    retaliation_other = models.StringField(
        choices=[[1, "1 (Strongly Disagree)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
                 [7, "7 (Strongly Agree)"]],
        label="\"In general, people in this country retaliate when they feel someone has wronged them if given the "
              "possibility to do so.\" To what extent do you agree with the previous statement, where 1 means "
              "strongly disagree and 7 strongly agree? ",
        widget=widgets.RadioSelect,
    )
    mwc = models.StringField(
        choices=[[1, "1 (Completely Unacceptable)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
                 [7, "7 (Completely Acceptable)"]],
        label="Consider the following situation: \"A group of three people are negotiating how to split a sum of "
              "money. At least two of them must agree on the split.\" a.) In your view, how acceptable is it to split "
              "the money only between two people, with the third person getting nothing? Where 1 is completely "
              "unacceptable and 7 is completely acceptable.",
        widget=widgets.RadioSelect,
    )
    mwc_others = models.StringField(
        choices=[[1, "1 (Extremely unlikely)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
                 [7, "7 (Extremely likely)"]],
        label="If three people in this country were to find themselves in the situation described in the previous "
              "question, how likely is it that the money will be split only between two of them, with the third "
              "person getting nothing? Where 1 is extremely unlikely and 7 is extremely likely.",
        widget=widgets.RadioSelect,
    )

    # Part 1c ----------------------

    atq_1 = models.IntegerField(
        label="In a lake, there is a patch of lily pads. Every day, the patch doubles in size. If it takes 48 days for the patch to cover the entire lake, how long would it take for the patch to cover half of the lake? (only numbers, no words)?",
        max=10000000,
        min=-10000000,
    )
    atq_2 = models.IntegerField(
        label="If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets? (only numbers, no letters)",
        max=10000000,
        min=-10000000,
    )
    atq_3 = models.IntegerField(
        label="A bat and a ball cost 1 USD in total. The bat costs 0.8 USD more than the ball. How much does the ball cost? (only numbers, no letters)",
        max=10000000,
        min=-10000000,
    )

    # Part 1d ----------------------

    age = models.IntegerField(
        label="What is your age?", min=18, max=110
    )
    risk = models.StringField(
        choices=[[0, '0 (Extremely unlikely)'], [1, '1'], [2, '2'], [3, '3'], [4, '4'],
                 [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9'],
                 [10, '10 (Extremely likely)']],
        label='In general, how willing are you to take risks??',
        widget=widgets.RadioSelect,
    )

    # Part 1e ----------------------

    occ = models.StringField(
        label=' What is your occupation?'
    )
    volunt = models.StringField(
        choices=[[1, 'Yes'], [2, 'No']],
        label="Have you done any volunteer work in the last 6 months?",
        widget=widgets.RadioSelect,
    )
    # Contingent on selecting volunt == 1
    volunt_hrs = models.StringField(
        choices=[[1, "1 to 4 hours"], 
                [2, "5 to 9 hours"], 
                [3, "10 to 14 hours"], 
                [4, "15 or more hours"],
                [5, "Don't know"]],
        label = "Approximately how many hours a week do you spend doing volunteer work?",
        widget = widgets.RadioSelect,
        blank = True
    )

    # Part 2a ----------------------

    party_like = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label='Is there a political party that you feel closer to than other parties?',
        widget=widgets.RadioSelect,
    )
    # Only show party and party_prox if party_like == 1 
    party = models.StringField(
        label='Which political party do you feel closest to?',
        blank = True
    )
    party_prox = models.StringField(
        choices=[[1, 'Very close'], [2, 'Somewhat close'], [3, 'Not close'], [4, 'Not at all close'],
                 [5, "Don't know"]],
        label='How close do you feel to this party?',
        widget=widgets.RadioSelect,
        blank = True
    )

    # Part 2b ----------------------

    econ = models.IntegerField(
        label="How many economics and/or finance courses have you taken at the university level?",
        max=999,
        min=0,
    )

    plop_unempl = models.StringField(
        choices=[[1, "1 (People who are unemployed ought to take any offered job to keep welfare support)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (People who are unemployed ought to be able to refuse any job they do not want)"]],
        label='Mark where on the scale that you would place your own political opinions.',
        widget=widgets.RadioSelect,
    )
    plop_comp = models.StringField(
        choices=[[1, "1 (Competition is good)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (Competition is damaging)"]],
        label='Mark where on the scale that you would place your own political opinions.',
        widget=widgets.RadioSelect,
    )
    plop_incdist = models.StringField(
        choices=[[1, "1 (The income distribution ought to be more equal)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (There ought to be more economic incentive for the individual to work harder)"]],
        label='Mark where on the scale that you would place your own political opinions.',
        widget=widgets.RadioSelect,
    )
    plop_priv = models.StringField(
        choices=[[1, "1 (More public companies ought to be privatized)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (More companies ought to be state-owned)"]],
        label='Mark where on the scale that you would place your own political opinions.',
        widget=widgets.RadioSelect,
    )
    plop_luckeffort = models.StringField(
        choices=[[1, "1 (In the long run, hard work usually brings a better life.)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (Hard work doesn't generally bring success-it's more a matter of luck and connections)"]],
        label='Mark where on the scale that you would place your own political opinions.',
        widget=widgets.RadioSelect,
    )

    # Part 5 ----------------------

    # Religion questions
    rel = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Do you consider yourself as belonging to any particular religion or denomination?",
        widget=widgets.RadioSelect,
    )
    # Contingent on question above
    rel_spec = models.StringField(
        choices=[[1, "Christianity - Protestantism"], [2, "Christianity - Catholicism"],
                 [3, "Christianity - Other denomination"],
                 [4, "Islam - All denominations"], [5, "Buddhism"], [6, "Hinduism"], [7, "Other"], [8, "Don't know"]],
        label='Which religion/denomination do you consider yourself belonging to?',
        widget=widgets.RadioSelect,
        blank = True
    )
    # Conditional on selecting "other" on previous question
    rel_other = models.StringField(
        label="What other religion do you belong to?",
        blank = True
    )

    # Part 4 ----------------------

    # Parent-related questions

    # Mother country of birth
    mth_spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Was your mother born in the United States?",
        widget=widgets.RadioSelect,
    )
    # Conditional on question above
    mth_cntbrn = models.StringField(
        label="In which country was your mother born?",
        choices=COUNTRIES,
        blank=True
    )
    # Father country of birth
    fth_spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Was your father born in the United States?",
        widget=widgets.RadioSelect,
    )
    # Conditional on question above
    fth_cntbrn = models.StringField(
        label="In which country was your father born?",
        choices=COUNTRIES,
        blank=True
    )

    # Part 5 ----------------------

    mwc_bonus = models.StringField(
        choices=[[1, "1 (Completely Unacceptable)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
                 [7, "7 (Completely Acceptable)"]],
        label="Consider the following situation: \"A group of three members of a company's board are tasked with negotiating how to split a sum of \"bonus\" money. At least two of them must agree on the split.\". In your view, how acceptable is it to split the money only between two people, with the third person getting nothing? Where 1 is completely unacceptable and 7 is completely acceptable.",
        widget=widgets.RadioSelect,
    )
    mwc_bonus_others = models.StringField(
        choices=[[1, "1 (Extremely unlikely)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
                 [7, "7 (Extremely likely)"]],
        label="If three people in this country were to find themselves in the situation described in the previous question, how likely is it that the money will be split only between two of them, with the third person getting nothing? Where 1 is extremely unlikely and 7 is extremely likely.",
        widget=widgets.RadioSelect,
    )
    enjoy = models.StringField(
        choices=[[0, "0 (Not at all)"], [1, "1"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (Enjoyed a lot)"]],
        label='How much did you enjoy this experiment? 0 means "not at all" and 10 means "enjoyed a lot".',
        widget=widgets.RadioSelect,
    )

    # Part 6 -------------------------

    bonus = models.LongStringField(
        label="What do you think is the purpose of this experiment?",
    )

# ------------------------------------------------------------------------------------------------------------------------------------
    
# PROLIFIC MISC 

# For Prolific integration
class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education', "income"]

    @staticmethod
    def before_next_page(self, timeout_happened):
        self.prolific_id = self.participant.label
pass

