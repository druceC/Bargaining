from otree.api import *
import numpy
import time



doc = """
Filter App (instructions, quiz)
"""


class Constants(BaseConstants):
    name_in_url = 'filter_app'
    players_per_group = None
    num_rounds = 1
    no_periods_payment = 2
    total_time = 3*60

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    total_num_failed_attempts = models.IntegerField(initial=0)
    q1_num_failed_attempts = models.IntegerField(initial=0)
    q2_num_failed_attempts = models.IntegerField(initial=0)
    q3_num_failed_attempts = models.IntegerField(initial=0)
    q4_num_failed_attempts = models.IntegerField(initial=0)
    q1_quiz = models.IntegerField(
        label="If a proposal is rejected then:",
        choices=[
            [1, 'A group with new members is formed and one member is randomly chosen to propose.'],
            [2, 'The group members remain the same and one member is randomly chosen to propose'],
        ],
        widget=widgets.RadioSelect,
    )
    q2_quiz = models.IntegerField(
        label="For a proposal to be approved:",
        choices=[
            [1, 'At least two members must vote in favor.'],
            [2, 'All members must vote in favor.'],
        ],
        widget=widgets.RadioSelect,
    )
    adios_reason = models.StringField()


# PAGES
class Welcome(Page):
    pass

class Introduction_1(Page):
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.payoffs_array = []
        player.participant.payoffs_array = []
        player.participant.calculator_invest = []
        player.participant.calculator_proposer = []
        player.participant.calculator_voter = []
        player.participant.skip_this_oTree_round = False
        #sum, max or min
        player.participant.FUND_TYPE="fixed"

class Introduction_2(Page):
    pass


class Quiz(Page):
    form_model = 'player'
    form_fields = ['q1_quiz','q2_quiz']
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1



    @staticmethod
    def error_message(player: Player, values):
        solutions = dict(q1_quiz=2, q2_quiz=1)
        # error_message can return a dict whose keys are field names and whose
        # values are error messages
        errors = {f: 'Wrong' for f in solutions if values[f] != solutions[f]}
        count = 1
        for f in solutions:
            print(values[f])
            if count == 1 and values[f] != 2:
                player.q1_num_failed_attempts += 1
            elif count == 2 and values[f] != 2:
                player.q2_num_failed_attempts += 1
            elif count == 3 and values[f] != 2:
                player.q3_num_failed_attempts += 1
            elif count == 4 and values[f] != 2:
                player.q4_num_failed_attempts += 1
            count += 1

        # errors = 'You have failed the quiz once. You have one more chance! If you fail again you will not be able to continue the activity!'
        # print('errors is', errors)
        if errors:
            player.total_num_failed_attempts += 1
            return errors



page_sequence = [Welcome,
                 Introduction_1, Introduction_2, Quiz
                 ]
