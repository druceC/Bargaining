from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'Survey'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    cmt_propr = models.LongStringField(
        label="In the rounds where you were a proposer, what considerations did you take into account when proposing a distribution?",
    )
    cmt_vtr= models.LongStringField(
        label="In the rounds where you were a voter, what considerations did you take into account, when voting on a distribution?",
    )

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
        label="A bat and a ball cost 110 Euros in total. The bat costs 100 Euros more than the ball. How much does the ball cost? (only numbers, no letters)",
        max=10000000,
        min=-10000000,
    )
    age = models.IntegerField(
        label="What is your age?", min=18,max=110)

    gen = models.StringField(
        choices=[[1, 'Female'], [2, 'Male'],
                 [3, 'Other']],
        label='What gender describes you?',
        widget=widgets.RadioSelect,
    )

    gen_cgi = models.StringField(
        choices=[[0, '0 (Very masculine)'], [1, '1'], [2, '2'], [3, '3'], [4, '4'],
                 [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9'],
                 [10, '10 (Very feminine)']],
        label='In general, how do you see yourself? Where would you put yourself on this scale (0-10) from "Very masculine" to "Very feminine"?',
        widget=widgets.RadioSelect,
    )
    risk = models.StringField(
        choices=[[0, '0 (Extremely unlikely)'], [1, '1'], [2, '2'], [3, '3'], [4, '4'],
                 [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9'],
                 [10, '10 (Extremely likely)']],
        label='In general, how willing are you to take risks??',
        widget=widgets.RadioSelect,
    )
    party_like = models.StringField(
        choices=[[1,'Yes'], [2,'No'],[3,"Don't know"]],
        label='Is there a political party that you feel closer to than other parties?',
        widget=widgets.RadioSelect,
    )
    econ = models.IntegerField(
        label="How many economics and/or finance courses have you taken at the university level?",
        max=999,
        min=0,
    )
    party = models.StringField(
        label='Which party?'
    )
    party_prox = models.StringField(
        choices=[[1, 'Very close'], [2, 'Somewhat close'], [3, 'Not close'], [4, 'Not at all close'], [5, "Don't know"]],
        label='How close do you feel to this party?',
        widget=widgets.RadioSelect,
    )
    gender_other = models.StringField(
        label='What is your gender?'
    )
    inc = models.IntegerField(
        label="What is your personal monthly income before taxes?",
        max=999999999,
        min=0,
    )
    inc_hh = models.IntegerField(
        label="What is the monthly income before taxes of the household in which you were raised?",
        max=999999999,
        min=0,
    )
    inc_hh = models.IntegerField(
        label="What is the monthly income before taxes of the household in which you were raised?",
        max=999999999,
        min=0,
    )
    stud = models.StringField(
        choices=[[1, 'Yes'], [2, 'No']],
        label="Are you a currently a student at the University of Nairobi or another higher education institution?",
        widget=widgets.RadioSelect,
    )
    stud_degree = models.StringField(
        choices=[[1, 'Bachelor'], [2, 'Master'],[3,'PhD']],
        label="Are you a bachelor's, master's or PhD student?",
        widget=widgets.RadioSelect,
    )
    stud_job = models.StringField(
        choices=[[1, 'Yes'], [2, 'No']],
        label="Do you currently have a student job?",
        widget=widgets.RadioSelect,
        initial=-9
    )
    finc_supp = models.StringField(
        choices=[[1, "I don't receive any financial support from my parents"], [2, 'Less than 500 Euros'],
                 [3,"500 - 999 Euros"], [4,"1,000 - 1,499 Euros"],[5,"1,500 - 1,999 Euros"],[6,"2,000 - 2,499 Euros"], [7,"2,500 - 2,999 Euros"],[8,"3,000 - 3,499 Euros"],
                 [9,"3,500 - 3,999 Euros"], [10,"4.000-4,499 Euros"], [11,"4,500 - 4,999 Euros"], [12,"More than 5,000 Euros"], [13,"I would prefer not to say"]],
        label='How much monthly financial support do you currently receive from your parents?',
        widget=widgets.RadioSelect,
    )

    occ = models.StringField(
        label=' What is your occupation?'
    )

    degree = models.StringField(
        choices=[[1, "None"],[2, "Pre-school"],[3, "Standard 1"],[4, "Standard 2"],
                [5, "Standard 3"],[6, "Standard 4"],[7, "Standard 5"],[8, "Standard 6"],
                [9, "Standard 7"],[10, "Standard 8"],[11, "Form 1"],[12, "Form 2"],
                [13, "Form 3"],[14, "Form 4"],[15, "Form 5"],[16, "Form 6"],
                [17, "College Year 1"],[18, "College Year 2"],[19, "College Year 3"],
                [20, "College Year 4"],[21, "University Year 1"], [22, "University Year 2"],
                [23, "University Year 3"], [24, "University Year 4"], [25, "Polytechnic"],
                [26, "Postgraduate"],],
        label='What is your highest education attained?',
    )

    volunt = models.StringField(
        choices=[[1, 'Yes'], [2, 'No']],
        label="Have you done any volunteer work in the last 6 months?",
        widget=widgets.RadioSelect,
    )
    stud_job_hrs = models.StringField(
        choices=[[1,"1 to 4 hours"], [2,"5 to 9 hours"],[3,"10 to 14 hours"],[4,"15 or more hours"],[5,"Don't know"]],
        label='Approximately how many hours a week do you spend working at your student job?',
        widget=widgets.RadioSelect,
    )
    volunt_hrs = models.StringField(
        choices=[[1,"1 to 4 hours"],[2,"5 to 9 hours"],[3,"10 to 14 hours"],[4,"15 or more hours"],[5,"Don't know"]],
        label='Approximately how many hours a week do you spend doing volunteer work?',
        widget=widgets.RadioSelect,
    )
    plop_unempl = models.StringField(
        choices=[[1,"1 (People who are unemployed ought to take any offered job to keep welfare support)"],
                 [2,"2"],[3,"3"],[4,"4"],[5,"5"],[6,"6"],[7,"7"],[8,"8"],[9,"9"],[10,"10 (People who are unemployed ought to be able to refuse any job they do not want)"]],
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
    rel = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'],[3,"Don't know"]],
        label="Do you consider yourself as belonging to any particular religion or denomination?",
        widget=widgets.RadioSelect,
    )
    spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Were you born in Kenya?",
        widget=widgets.RadioSelect,
    )
    spcit = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Are you an Kenyan citizen?",
        widget=widgets.RadioSelect,
    )
    cntbrn = models.StringField(
        label='In which country were you born?'
    )
    rel_spec = models.StringField(
        choices=[[1,"Christianity - Protestantism"],[2,"Christianity - Catholicism"], [3,"Christianity - Other denomination"],
        [4,"Islam - All denominations"],[5,"Buddhism"],[6,"Hinduism"],[7,"Other"],[8,"Don't know"]],
        label='Which religion/denomination do you consider yourself belonging to?',
        widget=widgets.RadioSelect,
        initial=-9
    )
    mth_spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Was your mother born in Kenya?",
        widget=widgets.RadioSelect,
    )
    fth_spbrn = models.StringField(
        choices=[[1, 'Yes'], [2, 'No'], [3, "Don't know"]],
        label="Was your father born in Kenya?",
        widget=widgets.RadioSelect,
    )
    rel_other= models.StringField(
        label="What other religion do you belong to?",
    )
    mth_cntbrn = models.StringField(
        label="In which country was your mother born?",
    )
    fth_cntbrn = models.StringField(
        label="In which country was your father born?",
    )
    mth_spcit = models.StringField(
        label="Is your mother an Kenyan citizen?",
    )
    fth_spcit = models.StringField(
        label="Is your father an Kenyan citizen?",
    )
    mth_cit = models.StringField(
        label="What citizenship does your mother hold?",
    )
    fth_cit = models.StringField(
        label="What citizenship does your father hold?",
    )
    primlang = models.StringField(
        label="What was the primary language spoken in the household in which you were raised?",
    )
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
        choices=[[0,"0 (Not at all)"],[1, "1"],
                 [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "7"], [8, "8"], [9, "9"],
                 [10, "10 (Enjoyed a lot)"]],
        label='How much did you enjoy this experiment? 0 means "not at all" and 10 means "enjoyed a lot".',
        widget=widgets.RadioSelect,
    )
    cmt = models.LongStringField(
        label='Do you have any comments regarding the experiment?'
    )


# FUNCTIONS


# PAGES

class Part1a(Page):
    form_model = 'player'
    form_fields = ['cmt_propr','cmt_vtr']
    

class Part1b(Page):
    form_model = 'player'
    form_fields = ['retaliation','retaliation_other','mwc','mwc_others']


class Part1c(Page):
    form_model = 'player'
    form_fields = ['atq_1','atq_2','atq_3']


class Part1d(Page):
    form_model = 'player'
    form_fields = ['age','gen','gen_cgi','risk','party_like','econ']


class Part2a(Page):
    form_model = 'player'
    @staticmethod
    def get_form_fields(player):
        if int(player.gen) == 3 and int(player.party_like) == 1:
            return ['party', 'party_prox','gender_other']
        elif int(player.gen) == 3:
            return ['gender_other']
        elif int(player.party_like) == 1:
            return['party', 'party_prox']

    @staticmethod
    def is_displayed(player):
        return int(player.gen) == 3 or int(player.party_like) == 1


    

class Part2b(Page):
    form_model = 'player'
    form_fields = ['inc','inc_hh','stud']

class Part3a(Page):
    form_model = 'player'
    form_fields = ['stud_degree',#'stud_job',
                   'finc_supp','volunt']

    @staticmethod
    def is_displayed(player):
        return int(player.stud) == 1
    

class Part3b(Page):
    form_model = 'player'
    form_fields = ['occ','degree','volunt']

    @staticmethod
    def is_displayed(player):
        return int(player.stud) == 2
    

class Part4a(Page):
    form_model = 'player'
    form_fields = [#'stud_job_hrs',
                   'volunt_hrs']

    @staticmethod
    def get_form_fields(player):
        #if int(player.volunt) == 1 and int(player.stud_job) == 1:
        #    return ['stud_job_hrs','volunt_hrs']
        #elif int(player.stud_job) == 1:
        #    return ['stud_job_hrs']
        #elif int(player.volunt) == 1:
        if int(player.volunt) == 1:
            return ['volunt_hrs']

    @staticmethod
    def is_displayed(player):
        return int(player.volunt) == 1 #or int(player.stud_job) == 1


class Part4b(Page):
    form_model = 'player'
    form_fields = ['plop_unempl','plop_comp','plop_incdist']

class Part4c(Page):
    form_model = 'player'
    form_fields = ['plop_priv','plop_luckeffort']

class Part5(Page):
    form_model = 'player'
    form_fields = ['rel', 'spbrn','spcit']
    
class Part6(Page):
    form_model = 'player'
    form_fields = ['cntbrn','rel_spec','mth_spbrn','fth_spbrn']
    @staticmethod
    def get_form_fields(player):
        if int(player.spbrn) == 2 and int(player.rel) == 1:
            return ['cntbrn','rel_spec','mth_spbrn','fth_spbrn']
        elif int(player.spbrn) == 2:
            return ['cntbrn','mth_spbrn','fth_spbrn']
        elif int(player.rel) == 1:
            return ['rel_spec','mth_spbrn','fth_spbrn']
        else:
            return ['mth_spbrn','fth_spbrn']

class Part7(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if int(player.rel_spec) == 7 and int(player.mth_spbrn)==2 and int(player.fth_spbrn)==2:
            return ['rel_other','mth_cntbrn', 'mth_spcit','fth_cntbrn','fth_spcit']
        elif int(player.mth_spbrn)==2 and int(player.fth_spbrn)==2:
            return ['mth_cntbrn', 'mth_spcit','fth_cntbrn','fth_spcit']
        elif int(player.rel_spec) == 7 and int(player.mth_spbrn)==2 :
            return ['rel_other','mth_cntbrn', 'mth_spcit']
        elif int(player.rel_spec) == 7 and int(player.fth_spbrn)==2 :
            return ['rel_other', 'fth_cntbrn', 'fth_spcit']
        elif int(player.rel_spec) == 7 :
            return ['rel_other']
        elif int(player.mth_spbrn)==2 :
            return ['mth_cntbrn', 'mth_spcit']
        elif int(player.fth_spbrn)==2 :
            return ['fth_cntbrn','fth_spcit']

    @staticmethod
    def is_displayed(player):
        return int(player.rel_spec) == 7 or int(player.mth_spbrn)==2 or int(player.fth_spbrn)==2
    

class Part8(Page):
    form_model = 'player'
    form_fields = ['mth_cit','fth_cit','primlang']
    def get_form_fields(player):
        if int(player.mth_spbrn)==2 and int(player.fth_spbrn)==2:
            return ['mth_cit','fth_cit','primlang']
        elif int(player.mth_spbrn)==2:
            return ['mth_cit','primlang']
        elif int(player.fth_spbrn)==2:
            return ['fth_cit','primlang']

    @staticmethod
    def is_displayed(player):
        return int(player.mth_spbrn)==2 or int(player.fth_spbrn)==2

class Part9(Page):
    form_model = 'player'
    form_fields = ['mwc_bonus','mwc_bonus_others','enjoy','cmt']

class Fin(Page):
    form_model = 'player'



page_sequence = [Part1a,Part1b,Part1c,Part1d,Part2a,Part2b,Part3a,Part3b,
                 Part4a,Part4b,Part4c,Part5,Part6,Part7,Part8,Part9,Fin]



