# Defines players, groups, session logic, and game state
import json
import random
from otree.api import *

class Constants(BaseConstants):
    name_in_url = 'fund_vanishes'
    players_per_group = 3
    num_rounds = 5
    no_periods = 5
    total_tokens = 30
    token_value = 0.1  # 10 tokens = 1 USD

def creating_session(subsession):
    session = subsession.session

    # Regroup players after every round 
    subsession.group_randomly(fixed_id_in_group=True)

    session.list_players_waiting = '[]'
    #subsession.group_randomly()

    # Ensure every participant has a period count
    for player in subsession.get_players():     
        # Shorter reference
        participant = player.participant 

        # Randomly assign player for either priming or baseline treatment
        if "is_priming" not in participant.vars:            
            participant.vars["is_priming"] = random.choice([True, False])
        
        # Ensure this carries over to the player's instance for this round
        player.is_priming = participant.vars["is_priming"]

        print(f"Player {player.id_in_group} in group {player.group.id_in_subsession} → {'Priming' if player.is_priming else 'Baseline'}")

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
    pass

# Group-level data
class Group(BaseGroup):
    
    # STATE TRACKING ---------------------------------------------------------
    # Group Period
    current_period = models.IntegerField(initial=0)

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

    # @staticmethod
    def is_displayed(self):
        if self.player.participant.skip_this_oTree_round == False:
            return True
        else:
            return False


class Player(BasePlayer):
    # Assign prolific ID
    prolific_id = models.StringField(default=str(" "))
    
    is_priming = models.BooleanField()                  # Randomly assign each player to either receive priming or baseline treatment
    period_no = models.IntegerField(initial=0)
    player_role = models.StringField()  
    proposal = models.IntegerField(min=0, max=30)       # Proposal for token allocation
    vote = models.BooleanField(
        choices=[[True, 'Approve'], [False, 'Reject']],
        label="Do you accept this proposal?",
        widget=widgets.RadioSelect,
        blank = True                                    # Allows vote to be None initially                 
    )                 
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



    # # Function to store earnings of a player instance (ie. proposer ID and allocation proposed)
    # def store_earnings(self, player_id, round, earnings):
    #     # payoff = json.loads(self.group.all_proposals_str)                         # Convert JSON string to list
    
    #     # Store earnings in participant.vars which stays the same for entire session

    #     try:
    #         # Ensure existing all_earnings is a valid list
    #         all_earnings_list = json.loads(self.all_earnings) if self.all_earnings else []
    #     except json.JSONDecodeError:
    #         all_earnings_list = []
    #         print("new list started")

    #     # Ensure it's a list before appending
    #     # if not isinstance(all_earnings_list, list):
    #     #     all_earnings_list = []
    #     #     print("new list started")
        
    #     # ✅ Prevent duplicate storage for the same round
    #     existing_rounds = {entry["round"] for entry in all_earnings_list}
    #     if round in existing_rounds:
    #         print(f"[DEBUG] Earnings for round {round} already stored. Skipping duplicate entry.")
    #         return  # Exit early to prevent duplicates
        
    #     # Append new earnings for the current round
    #     all_earnings_list.append({"round": round, "earnings": float(earnings)})            # Append new payoff

    #     # Convert back to JSON string and save
    #     self.all_earnings = json.dumps(all_earnings_list)

    #     # Print submitted proposals in the terminal
    #     print(f"Player: {player_id}")
    #     print(f"\n[DEBUG] New earnings earned in round {round}: {earnings}")
    #     print(f"[DEBUG] All earnings so far: {self.all_earnings}\n")
    
     # Function to determine the final earnings based on a randomly selected round
    # def final_earnings(self):
    #     # Select random round
    #     try:
    #         all_earnings_list = json.loads(self.all_earnings)  # Load earnings history
    #     except json.JSONDecodeError:
    #         all_earnings_list = []

    #     if not all_earnings_list:
    #         return {"payment_period": None, "final_payment": 0}  # No earnings recorded

    #     # Select a random round from stored rounds
    #     payment_period = random.randint(0, len(all_earnings_list) - 1)
    #     print(f"payment period {payment_period}")
    #     final_payment = all_earnings_list[payment_period]["earnings"]

    #     # Debugging output
    #     print(f"\n[DEBUG] Selected random payment round: {all_earnings_list[payment_period]['round']}")
    #     print(f"[DEBUG] Final payment: {final_payment}")

    #     return {"payment_period": payment_period, "final_payment": final_payment}
    #     # return {"payment_period": all_earnings_list[payment_period]["round"], "final_payment": final_payment}

    # MODIFIED FINAL EARNINGS FUNCTION
    def final_earnings(self):
        participant = self.participant

        # Load earnings from participant.vars instead of self.all_earnings
        all_earnings_list = participant.vars.get("all_earnings", [])

        if len(all_earnings_list) == 0:
            return {"selected_periods": [], "final_payment": 0}  # No earnings recorded
        
        # If only one round is available, pick that. Otherwise, select two unique rounds.
        if len(all_earnings_list) == 1:
            selected_entries = [all_earnings_list[0]]
        else:
            # Select two unique random periods from all_earnings_list, or fewer if there aren't enough roundes
            selected_entries = random.sample(all_earnings_list, min(2, len(all_earnings_list)))

        # Extract period numbers and earnings
        selected_periods = [{"period": entry["round"], "tokens": entry["earnings"]} for entry in selected_entries]

        # Compute total final payment (includes $2 fixed participation fee) | 10 tokens = 1 USD
        final_payment = (sum(entry["earnings"] for entry in selected_entries)/4) + 2 + 1

        # Compute individual USD equivalent entry of each entry using (4 tokens = 1 USD Conversion)
        total_bonus = (sum(entry["earnings"] for entry in selected_entries)/4)

        for entry in selected_periods:
            entry["usd_equivalent"] = round(entry["tokens"] / 4, 2)

        # Debugging output
        print(f"\n[DEBUG] Selected payment rounds: {selected_periods}")
        print(f"[DEBUG] Total final payment: {final_payment}")

        # return {"selected_periods": selected_periods, "final_payment": final_payment, ""}
        return {"selected_periods": selected_periods, 
                "final_payment": final_payment,
                # "period_earnings": period_earnings,
                "total_bonus": total_bonus
            }

    #####################################################################################
    
    #  QUIZ SECTION

    # Tracks total failed quiz attempts across all questions
    total_num_failed_attempts = models.IntegerField(initial=0)

    # Tracks failed attempts for each individual quiz question
    q1_num_failed_attempts = models.IntegerField(initial=0)
    q2_num_failed_attempts = models.IntegerField(initial=0)
    q3_num_failed_attempts = models.IntegerField(initial=0)

    # Q1: What happens when a proposal is rejected?
    q1_quiz = models.IntegerField(
        choices=[
            [1, "The group members remain the same and one member is randomly chosen to propose."],
            [2, "The fund vanishes, each member gets 0 tokens."]
        ],
        label="If a proposal is rejected, what happens next?",
        widget=widgets.RadioSelect
    )
    # Q2: What is required for proposal approval?
    q2_quiz = models.IntegerField(
        choices=[
            [1, "At least two members must vote in favor."],
            [2, "All members must vote in favor."]
        ],
        label="For a proposal to be approved, how many votes are required?",
        widget=widgets.RadioSelect
    )
    # Q3: Group members for each period
    q3_quiz = models.IntegerField(
        choices=[
            [1, "You will face the exact same group members."],
            [2, "Your group members will be randomly selected."]
        ],
        label="Each time that you are placed in a group to divide the 30 tokens:",
        widget=widgets.RadioSelect
    )

    # Stores the reason for a participant leaving the experiment (if applicable)
    adios_reason = models.StringField()

    # Dropout identifier
    dropout = models.BooleanField(initial=False)
    # Players decision
    decision = models.BooleanField(initial=False)
    random_period = models.StringField()
    # Share of the funded proposed
    share = models.CurrencyField(initial=0)
    # Role, default is Voter
    role_player = models.StringField(initial="Voter")
    # Was the offer accepted by each individual voter?
    player_offer_accepted = models.BooleanField()
    # Investment
    investment = models.BooleanField(label="Would you like to contribute?", choices=[[True, "Yes"], [False, "No"]],
                                     widget=widgets.RadioSelect, )
    # Payoff this period
    payoff_this_period = models.FloatField()
    # individual share for each participant
    s = models.IntegerField()
    # individual per of the share for each participant
    s_per = models.FloatField()

    points_to_currency = models.CurrencyField()
    points_to_currency_s = models.CurrencyField()
    
    #------------------------------------------------------------------------------------------------------------------------------------s

    # PRIMING/BASELINE QUESTIONS

    qp1 = models.StringField(
        choices=[[1, "1 (Not Important at all)"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5 (Extremely Important))"],],
        label="Earlier you described your gender as _____. Please answer the following question, How important is it for you that others know your gender?",
        widget=widgets.RadioSelect,
    )

    qp2 = models.StringField(
        choices=[
            [1, "1 (Feminine)"],
            [2, "2"],
            [3, "3"],
            [4, "4"],
            [5, "5"],
            [6, "6"],
            [7, "7"],
            [8, "8"],
            [9, "9"],
            [10, "10 (Masculine)"]
        ],
        label="On a scale of 1-10, where 1 is feminine and 10 is masculine, how would you rate the expression of your gender identity?",
        widget=widgets.RadioSelect,
    )

    qp3 = models.StringField(
        choices=[
            [1, "1 (Not Important at all)"],
            [2, "2"],
            [3, "3"],
            [4, "4"],
            [5, "5 (Extremely Important)"]
        ],
        label="You have stated that you rate your expression of your gender identity as ____. How important is it for you to express your gender identity to others?",
        widget=widgets.RadioSelect,
    )
    #------------------------------------------------------------------------------------------------------------------------------------
    
    # SURVEY QUESTIONS 
    
    combined_payoff = models.FloatField()
    random_payoff = models.FloatField()

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
    
    # Gender -------------------

    sex = models.StringField(
        choices=[[1, 'Male'], [2, 'Female'], [3, 'Intersex'], 
                 [4, 'I prefer not to answer']],
        label='What sex were you assigned at birth, or your original birth certificate?',
        widget=widgets.RadioSelect,
    )

    gen = models.StringField(
        choices=[
            [1, 'Man or Male'], 
            [2, 'Woman or Female'], 
            [3, 'Non-binary or Genderqueer'], 
            [4, 'I use a different term (please specify)'],
            [5, 'I prefer not to answer']
        ],
        label='How do you describe your gender?',
        widget=widgets.RadioSelect,  
    )
    # New field for custom input
    other_gender = models.StringField(blank=True)

    gen_cgi = models.StringField(
        choices=[[0, '0 (Very masculine)'], [1, '1'], [2, '2'], [3, '3'], [4, '4'],
                 [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9'],
                 [10, '10 (Very feminine)']],
        label='In general, how do you see yourself? Where would you put yourself on this scale (0-10) from "Very masculine" to "Very feminine"?',
        widget=widgets.RadioSelect,
    )

    # Income ----------------------

    inc = models.IntegerField(
        label="What is your personal monthly income before taxes? <br>(Please enter full amount in dollars.)",
        max=999999999,
        min=0,
    )
    inc_hh = models.IntegerField(
        label="What was your household’s total monthly income before taxes during your childhood? (Provide the full amount in dollars, considering the combined income of all those living in your primary childhood home.)",
        max=999999999,
        min=0,
    )

    # Part 3a ----------------------

    # stud_degree = models.StringField(
    #     choices=[[1, 'Bachelor'], [2, 'Master'],[3,'PhD']],
    #     label="Are you a bachelor's, master's or PhD student?",
    #     widget=widgets.RadioSelect,
    # )
    stud_job = models.StringField(
        choices=[[1, 'Yes'], [2, 'No']],
        label="Do you currently have a student job?",
        widget=widgets.RadioSelect,
        initial=-9
    )
    # finc_supp = models.StringField(
    #     choices=[[1, "I don't receive any financial support from my parents"],
    #              [2, "Less than 20.000 KSH"], [3, "20.000-29.999 KSH"], [4, "30.000-49.999 KSH"],
    #              [5, "50.000-59.999 KSH"], [6, "60.000-69.999 KSH"], [7, "70.000-79.999 KSH"],
    #              [8, "80.000-99.999 KSH"], [9, "100.000-119.999 KSH"], [10, "120.000-149.999 KSH"],
    #              [11, "More than 150.000 KSH"], [12, "I would prefer not to say"]],
    #     label='How much monthly financial support do you currently receive from your parents?',
    #     widget=widgets.RadioSelect,
    # )

    # Education ----------------------

    degree = models.StringField(
        choices=[[1, "None"], [2, "Pre-school"], [3, "Standard 1"], [4, "Standard 2"],
                 [5, "Standard 3"], [6, "Standard 4"], [7, "Standard 5"], [8, "Standard 6"],
                 [9, "Standard 7"], [10, "Standard 8"], [11, "Form 1"], [12, "Form 2"],
                 [13, "Form 3"], [14, "Form 4"], [15, "Form 5"], [16, "Form 6"],
                 [17, "College Year 1"], [18, "College Year 2"], [19, "College Year 3"],
                 [20, "College Year 4"], [21, "University Year 1"], [22, "University Year 2"],
                 [23, "University Year 3"], [24, "University Year 4"], [25, "Polytechnic"],
                 [26, "Postgraduate"], ],
        label='What is your highest education attained?',
    )

    # Part 3b ----------------------

    occ = models.StringField(
        label=' What is your occupation?'
    )
    degree = models.StringField(
        choices=[[1, "None"], [2, "Pre-school"], [3, "Standard 1"], [4, "Standard 2"],
                 [5, "Standard 3"], [6, "Standard 4"], [7, "Standard 5"], [8, "Standard 6"],
                 [9, "Standard 7"], [10, "Standard 8"], [11, "Form 1"], [12, "Form 2"],
                 [13, "Form 3"], [14, "Form 4"], [15, "Form 5"], [16, "Form 6"],
                 [17, "College Year 1"], [18, "College Year 2"], [19, "College Year 3"],
                 [20, "College Year 4"], [21, "University Year 1"], [22, "University Year 2"],
                 [23, "University Year 3"], [24, "University Year 4"], [25, "Polytechnic"],
                 [26, "Postgraduate"], ],
        label='What is your highest education attained?',
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


    # Part 4a ----------------------

    # stud_job_hrs = models.StringField(
    #     choices=[[1, "1 to 4 hours"], [2, "5 to 9 hours"], [3, "10 to 14 hours"], [4, "15 or more hours"],
    #              [5, "Don't know"]],
    #     label='Approximately how many hours a week do you spend working at your student job?',
    #     widget=widgets.RadioSelect,
    # )

    # Part 2a ----------------------

    # Political Questions

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

    # Part 4b ----------------------

     # Economics Questions

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

    # rel_spec = models.StringField(blank=True)

    # Part a ----------------------

    # Conditional on selecting "other" on previous question
    rel_other = models.StringField(
        label="What other religion do you belong to?",
        blank = True
    )

    # Part 6 ----------------------
    # Part 6 ----------------------

    # Personal birth and citizenships

    spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Were you born in the United States?",
        widget=widgets.RadioSelect,
    )
    # Conditional on the question above (if not born in the US)
    cntbrn = models.StringField(
        label='Which country were you born in?',
        blank=True
    )

    spcit = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Are you an American citizen?",
        widget=widgets.RadioSelect,
    )
    # Conditional on the question above (if not american citizen)
    other_cit = models.StringField(
        label="What citizenship do you hold?",
        blank=True
        # widget=widgets.RadioSelect,
    )

    primlang = models.StringField(
        label="What was the primary language spoken in the household in which you were raised?",
    )

    # Part 7 ----------------------

    # Parent-related questions

    mth_spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Was your mother born in the United States?",
        widget=widgets.RadioSelect,
    )
    # Conditional on question above
    mth_cntbrn = models.StringField(
        label="In which country was your mother born?",
        blank=True
    )

    fth_spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Was your father born in the United States?",
        widget=widgets.RadioSelect,
    )
    # Conditional on question above
    fth_cntbrn = models.StringField(
        label="In which country was your father born?",
        blank=True
    )

    # Part 8 ----------------------

    # mth_cit = models.StringField(
    #     label="What citizenship does your mother hold?",
    # )
    # fth_cit = models.StringField(
    #     label="What citizenship does your father hold?",
    # )
    

    # Part 9 ----------------------

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

    # Part 10 -------------------------

    bonus = models.LongStringField(
        label="What do you think is the purpose of this experiment?",
    )


# For Prolific integration
class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education', "income"]

    @staticmethod
    def before_next_page(self, timeout_happened):
        self.prolific_id = self.participant.label
pass

