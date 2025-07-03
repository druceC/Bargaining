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

def load_language_choices():
    filepath = os.path.join(os.path.dirname(__file__), 'iso_639_3_new.csv')
    choices = []

    with open(filepath, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Language'].strip()
            code = row['Code'].strip()
            if code and name:
                choices.append((code, name))

    length = len(choices)
    # Add "other" option to the beginning of list
    # choices.insert(length, (000, "Other (please specify)"))

    return choices

# -----------------------

class Constants(BaseConstants):
    name_in_url = 'filter_app'
    players_per_group = None                 # Commented out for dynamic group formation 
    # players_per_group = 3
    num_rounds = 5                          # Overall round loop
    no_periods = 5                          # Custom counter
    total_tokens = 30
    token_value = 0.4                       # 4 tokens = 1 USD

def creating_session(subsession):
    session = subsession.session
    
    session.list_players_waiting = '[]'

    # Ensure every participant has a period count
    for player in subsession.get_players():     
        # Shorter reference
        participant = player.participant 

        # Assign prolific_id safely
        player.prolific_id = participant.label or participant.vars.get('prolific_id', 'NA')

class Subsession(BaseSubsession):
    creating_session = creating_session

    pass

# Group-level data
class Group(BaseGroup):
    
    # STATE TRACKING ---------------------------------------------------------
    
    # Group Period
    current_period = models.IntegerField(initial=0)

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

class Player(BasePlayer):

    # PROLIFIC SET-UP
    
    # prolific_id = models.LongStringField(
    #     # blank=False,
    #     # min_length=24,
    #     # max_length=24,
    #     # error_messages={"min_length": "Must be exactly 24 characters."},
    #     label="Please enter your prolific ID:",
    #     # Add photo of sample prolific ID and where to find it
    # )

    prolific_id = models.StringField(blank=True)
    study_id = models.StringField(blank=True)
    player_session_id = models.StringField(blank=True)
    experiment_start_time = models.FloatField()
    experiment_end_time = models.FloatField()
    game_start_time = models.FloatField()
    game_end_time = models.FloatField()

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

    #------------------------------------------------------------------------------------------------------------------------------------
    
    # DEMOGRAPHICS QUESTIONS
    
    combined_payoff = models.FloatField()
    random_payoff = models.FloatField()
    
    # Gender -------------------

    gen = models.StringField(
        choices=[
            [1, 'Man'], 
            [2, 'Woman'], 
            # [3, 'Non-binary or Genderqueer'], 
            [3, 'Other (please specify)'],
            # [5, 'I prefer not to answer']
        ],
        label='How do you describe your gender?',
        widget=widgets.RadioSelect,  
    )
    # New field for custom input
    other_gender = models.StringField(blank=True)

    # Income ----------------------

    inc = models.IntegerField(
        label="What is your personal monthly income before taxes? (Please enter full amount in dollars.)",
        choices=[
            (1, "Less than $10,000"),
            (2, "$10,000 - $19,000"),
            (3, "$20,000 - $29,999"),
            (4, "$30,000 - $39,999"),
            (5, "$40,000 - $49,999"),
            (6, "$50,000 - $59,999"),
            (7, "$60,000 - $69,999"),
            (8, "$70,000 - $79,999"),
            (9, "$80,000 - $99,999"),
            (10, "$100,000 - $119,999"),
            (11, "$120,000 - $149,999"),
            (12, "$150,000 - $199,999"),
            (13, "$200,000 - $249,999"),
            (14, "$250,000 - $349,999"),
            (15, "$350,000 - $499,000"),
            (16, "$500,000 or more"),
            (17, "Prefer not to say"),
        ]
    )
    inc_hh = models.IntegerField(
        label="What was your household’s total monthly income before taxes during your childhood?",
        choices=[
            (1, "Less than $10,000"),
            (2, "$10,000 - $19,000"),
            (3, "$20,000 - $29,999"),
            (4, "$30,000 - $39,999"),
            (5, "$40,000 - $49,999"),
            (6, "$50,000 - $59,999"),
            (7, "$60,000 - $69,999"),
            (8, "$70,000 - $79,999"),
            (9, "$80,000 - $99,999"),
            (10, "$100,000 - $119,999"),
            (11, "$120,000 - $149,999"),
            (12, "$150,000 - $199,999"),
            (13, "$200,000 - $249,999"),
            (14, "$250,000 - $349,999"),
            (15, "$350,000 - $499,000"),
            (16, "$500,000 or more"),
            (17, "Prefer not to say"),
        ]
    )

     # Education ----------------------

    degree = models.StringField(
        choices=[
            (1, "Did not graduate from high school"),
            (2, "High school graduate"),
            (3, "Some college, but no degree (yet)"),
            (4, "2-year college degree"),
            (5, "4-year college degree"),
            (6, "Postgraduate degree (MA, MBA, MD, JD, PhD, etc.)"),
        ],
        label='What is your highest level of education attained?',
    )

    # Nationality ----------------------

    # Country of birth
    spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Were you born in the United States?",
        widget=widgets.RadioSelect,
    )
    # Conditional on the question above (if not born in the US)
    cntbrn = models.StringField(
        label='Which country were you born in?',
        choices=COUNTRIES,
        blank=True      # Allows skipping
    )
    # Citizenship
    spcit = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Are you an American citizen?",
        widget=widgets.RadioSelect,
    )
    # Conditional on the question above (if not american citizen)
    other_cit = models.StringField(
        label="What citizenship do you hold?",
        choices=COUNTRIES,
        blank=True      # Allows skipping
    )
    primlang = models.StringField(
        label="What was the primary language spoken in the household in which you were raised?",
        choices=load_language_choices(),
    )
 
 
    #------------------------------------------------------------------------------------------------------------------------------------
    
    # FINAL SURVEY QUESTIONS
    
    # Part 1a ----------------------
    # cmt_propr = models.LongStringField(
    #     label="In the rounds where you were a proposer, what considerations did you take into account when proposing a distribution?",
    # )
    # cmt_vtr = models.LongStringField(
    #     label="In the rounds where you were a voter, what considerations did you take into account, when voting on a distribution?",
    # )

    # Part 1b ----------------------

    # retaliation = models.StringField(
    #     choices=[[1, "1 (Strongly Disagree)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
    #              [7, "7 (Strongly Agree)"]],
    #     label="\"If I feel that someone has wronged me, I will retaliate if given the possibility to do so.\" To what "
    #           "extent do you agree with the previous statement, where 1 means strongly disagree and 7 strongly agree?",
    #     widget=widgets.RadioSelect,
    # )
    # retaliation_other = models.StringField(
    #     choices=[[1, "1 (Strongly Disagree)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
    #              [7, "7 (Strongly Agree)"]],
    #     label="\"In general, people in this country retaliate when they feel someone has wronged them if given the "
    #           "possibility to do so.\" To what extent do you agree with the previous statement, where 1 means "
    #           "strongly disagree and 7 strongly agree? ",
    #     widget=widgets.RadioSelect,
    # )
    # mwc = models.StringField(
    #     choices=[[1, "1 (Completely Unacceptable)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
    #              [7, "7 (Completely Acceptable)"]],
    #     label="Consider the following situation: \"A group of three people are negotiating how to split a sum of "
    #           "money. At least two of them must agree on the split.\" a.) In your view, how acceptable is it to split "
    #           "the money only between two people, with the third person getting nothing? Where 1 is completely "
    #           "unacceptable and 7 is completely acceptable.",
    #     widget=widgets.RadioSelect,
    # )
    # mwc_others = models.StringField(
    #     choices=[[1, "1 (Extremely unlikely)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
    #              [7, "7 (Extremely likely)"]],
    #     label="If three people in this country were to find themselves in the situation described in the previous "
    #           "question, how likely is it that the money will be split only between two of them, with the third "
    #           "person getting nothing? Where 1 is extremely unlikely and 7 is extremely likely.",
    #     widget=widgets.RadioSelect,
    # )

    # Part 1c ----------------------

    # atq_1 = models.IntegerField(
    #     label="In a lake, there is a patch of lily pads. Every day, the patch doubles in size. If it takes 48 days for the patch to cover the entire lake, how long would it take for the patch to cover half of the lake? (only numbers, no words)?",
    #     max=10000000,
    #     min=-10000000,
    # )
    # atq_2 = models.IntegerField(
    #     label="If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets? (only numbers, no letters)",
    #     max=10000000,
    #     min=-10000000,
    # )
    # atq_3 = models.IntegerField(
    #     label="A bat and a ball cost 1 USD in total. The bat costs 0.8 USD more than the ball. How much does the ball cost? (only numbers, no letters)",
    #     max=10000000,
    #     min=-10000000,
    # )

    # Part 1d ----------------------

    # age = models.IntegerField(
    #     label="What is your age?", min=18, max=110
    # )
    # risk = models.StringField(
    #     choices=[[0, '0 (Extremely unlikely)'], [1, '1'], [2, '2'], [3, '3'], [4, '4'],
    #              [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9'],
    #              [10, '10 (Extremely likely)']],
    #     label='In general, how willing are you to take risks?',
    #     widget=widgets.RadioSelect,
    # )

    # Part 1e ----------------------

    # occ = models.StringField(
    #     label=' What is your occupation?'
    # )
    # volunt = models.StringField(
    #     choices=[[1, 'Yes'], [2, 'No']],
    #     label="Have you done any volunteer work in the last 6 months?",
    #     widget=widgets.RadioSelect,
    # )
    # # Contingent on selecting volunt == 1
    # volunt_hrs = models.StringField(
    #     choices=[[1, "1 to 4 hours"], 
    #             [2, "5 to 9 hours"], 
    #             [3, "10 to 14 hours"], 
    #             [4, "15 or more hours"],
    #             [5, "Don't know"]],
    #     label = "Approximately how many hours a week do you spend doing volunteer work?",
    #     widget = widgets.RadioSelect,
    #     blank = True
    # )

    # Part 2a ----------------------

    # party_like = models.StringField(
    #     choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
    #     label='Is there a political party that you feel closer to than other parties?',
    #     widget=widgets.RadioSelect,
    # )
    # # Only show party and party_prox if party_like == 1 
    # party = models.StringField(
    #     choices=[[1, 'Republican Party'], [2, 'Democratic Party'], [3, 'Libertarian Party'], ['Other (please specify)']],
    #     label='Which political party do you feel closest to?',
    #     widget=widgets.RadioSelect,
    #     blank = True
    # )

    # # New field for custom input
    # other_party = models.StringField(blank=True)

    # party_prox = models.StringField(
    #     choices=[[1, 'Very close'], [2, 'Somewhat close'], [3, 'Not close'], [4, 'Not at all close'],
    #              [5, "Don't know"]],
    #     label='How close do you feel to this party?',
    #     widget=widgets.RadioSelect,
    #     blank = True
    # )

    # Part 2b ----------------------

    # econ = models.IntegerField(
    #     label="How many economics and/or finance courses have you taken at the university level?",
    #     max=999,
    #     min=0,
    # )

    # plop_unempl = models.StringField(
    #     choices=[[1, "1 (People who are unemployed ought to take any offered job to keep welfare support)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
    #              [10, "10 (People who are unemployed ought to be able to refuse any job they do not want)"]],
    #     label='Mark where on the scale that you would place your own political opinions.',
    #     widget=widgets.RadioSelect,
    # )
    # plop_comp = models.StringField(
    #     choices=[[1, "1 (Competition is good)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
    #              [10, "10 (Competition is damaging)"]],
    #     label='Mark where on the scale that you would place your own political opinions.',
    #     widget=widgets.RadioSelect,
    # )
    # plop_incdist = models.StringField(
    #     choices=[[1, "1 (The income distribution ought to be more equal)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
    #              [10, "10 (There ought to be more economic incentive for the individual to work harder)"]],
    #     label='Mark where on the scale that you would place your own political opinions.',
    #     widget=widgets.RadioSelect,
    # )
    # plop_priv = models.StringField(
    #     choices=[[1, "1 (More public companies ought to be privatized)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
    #              [10, "10 (More companies ought to be state-owned)"]],
    #     label='Mark where on the scale that you would place your own political opinions.',
    #     widget=widgets.RadioSelect,
    # )
    # plop_luckeffort = models.StringField(
    #     choices=[[1, "1 (In the long run, hard work usually brings a better life.)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
    #              [10, "10 (Hard work doesn't generally bring success-it's more a matter of luck and connections)"]],
    #     label='Mark where on the scale that you would place your own political opinions.',
    #     widget=widgets.RadioSelect,
    # )

    # Part 5 ----------------------

    # Religion questions
    # rel = models.StringField(
    #     choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
    #     label="Do you consider yourself as belonging to any particular religion or denomination?",
    #     widget=widgets.RadioSelect,
    # )
    # # Contingent on question above
    # rel_spec = models.StringField(
    #     choices=[[1, "Christianity - Protestantism"], [2, "Christianity - Catholicism"],
    #              [3, "Christianity - Other denomination"],
    #              [4, "Islam - All denominations"], [5, "Buddhism"], [6, "Hinduism"], [7, "Other"], [8, "Don't know"]],
    #     label='Which religion/denomination do you consider yourself belonging to?',
    #     widget=widgets.RadioSelect,
    #     blank = True
    # )
    # # Conditional on selecting "other" on previous question
    # rel_other = models.StringField(
    #     label="What other religion do you belong to?",
    #     blank = True
    # )

    # Party Questions --------------------------
    # party_like = models.StringField(
    #     choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
    #     label='Is there a political party that you feel closer to than other parties?',
    #     widget=widgets.RadioSelect,
    # )
    # Only show party and party_prox if party_like == 1 
    party = models.StringField(
        choices=[[1, 'Republican'], [2, 'Democrat'], [3, 'Independent'], [4, 'Something Else']],
        # label='Generally speaking, do you usually think of yourself as a Democrat, a Republican, an independent, or something else?',
        label='In general, do you usually think of yourself as a Democrat, a Republican, an independent, or something else?',
        widget=widgets.RadioSelect,
    )

    party_closer = models.StringField(
        choices=[[1, 'Closer to the Republican Party'], [2, 'Closer to the Democratic Party'], [3, 'Neither'], ],
        # label='Do you think of yourself as closer to the Republican or Democratic Party?',
        label='Do you think of yourself as closer to the Republican or Democratic Party?',
        widget=widgets.RadioSelect,
        blank = True        # optional depending on answer to party
    )

    party_strong_republican = models.StringField(
        choices=[[1, 'Strong Republican'], [2, 'Not Very Strong Republican'], ],
        # choices=[[1, 'Strong Republican / Strong Democrat'], [2, 'Not Very Strong Republican / Not Very Strong Democrat'], ],
        # label='Would you call yourself a strong ${Republican / Democrat} or a not very strong ${Rep / Dem}?',
        label='Would you call yourself a strong Republican or not a very strong Republican?',
        widget=widgets.RadioSelect,
        blank = True        # optional depending on answer to party_closer
    )

    party_strong_democrat = models.StringField(
        choices=[[1, 'Strong Democrat'], [2, 'Not Very Strong Democrat'], ],
        # choices=[[1, 'Strong Republican / Strong Democrat'], [2, 'Not Very Strong Republican / Not Very Strong Democrat'], ],
        # label='Would you call yourself a strong ${Republican / Democrat} or a not very strong ${Rep / Dem}?',
        label='Would you call yourself a strong Democrat or not a very strong Democrat?',
        widget=widgets.RadioSelect,
        blank = True         # optional depending on answer to party_closer
    )

    # # New field for custom input
    # other_party = models.StringField(blank=True)

    # party_prox = models.StringField(
    #     choices=[[1, 'Very close'], [2, 'Somewhat close'], [3, 'Not close'], [4, 'Not at all close'],
    #              [5, "Don't know"]],
    #     label='How close do you feel to this party?',
    #     widget=widgets.RadioSelect,
    #     blank = True
    # )

    

    # Part 4 ----------------------

    # Parent-related questions

    # Mother country of birth
    # mth_spbrn = models.StringField(
    #     choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
    #     label="Was your mother born in the United States?",
    #     widget=widgets.RadioSelect,
    # )
    # # Conditional on question above
    # mth_cntbrn = models.StringField(
    #     label="In which country was your mother born?",
    #     choices=COUNTRIES,
    #     blank=True
    # )
    # # Father country of birth
    # fth_spbrn = models.StringField(
    #     choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
    #     label="Was your father born in the United States?",
    #     widget=widgets.RadioSelect,
    # )
    # # Conditional on question above
    # fth_cntbrn = models.StringField(
    #     label="In which country was your father born?",
    #     choices=COUNTRIES,
    #     blank=True
    # )

    # Part 5 ----------------------

    # mwc_bonus = models.StringField(
    #     choices=[[1, "1 (Completely Unacceptable)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
    #              [7, "7 (Completely Acceptable)"]],
    #     label="Consider the following situation: \"A group of three members of a company's board are tasked with negotiating how to split a sum of \"bonus\" money. At least two of them must agree on the split.\". In your view, how acceptable is it to split the money only between two people, with the third person getting nothing? Where 1 is completely unacceptable and 7 is completely acceptable.",
    #     widget=widgets.RadioSelect,
    # )
    # mwc_bonus_others = models.StringField(
    #     choices=[[1, "1 (Extremely unlikely)"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"],
    #              [7, "7 (Extremely likely)"]],
    #     label="If three people in this country were to find themselves in the situation described in the previous question, how likely is it that the money will be split only between two of them, with the third person getting nothing? Where 1 is extremely unlikely and 7 is extremely likely.",
    #     widget=widgets.RadioSelect,
    # )
    # enjoy = models.StringField(
    #     choices=[[0, "0 (Not at all)"], [1, "1"],
    #              [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
    #              [10, "10 (Enjoyed a lot)"]],
    #     label='How much did you enjoy this experiment? 0 means "not at all" and 10 means "enjoyed a lot".',
    #     widget=widgets.RadioSelect,
    # )

    # Part 6 -------------------------

    # bonus = models.LongStringField(
    #     label="What do you think is the purpose of this experiment?",
    # )

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

