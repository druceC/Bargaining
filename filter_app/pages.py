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
import time
import json
import csv
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fund_vanishes.settings")
from django.core.files.storage import default_storage

# Variables for Progress Bar 
INTRO_QUESTIONS = 4

# Timeout
PROPOSAL_TIMEOUT = 60                  # Proposer Page 
VOTE_TIMEOUT = 60                      # Voter Page
PROPOSAL_TIMEOUT_2 = 30                # 2nd Chance Proposer Page
VOTE_TIMEOUT_2 = 30                    # 2nd Chance Voter Page
RESULTS_TIMEOUT = 30                   # Results Page timeout

NUMBER_OF_ROUNDS = 3

# ---------------------------------------------------------------------------------------------------

# INTRO QUESTIONS

# Dropout detection for normal pages (all game pages inherit from this)
class BasePage(Page):
    def is_displayed(self):
        # Don't show page if dropout is detected
        return not self.group.drop_out_detected

# Dropout detection for WaitPages
class BaseWaitPage(WaitPage):
    def is_displayed(self):
        # Don't show page if dropout is detected
        return not self.group.drop_out_detected


class WelcomePage(Page):
    def is_displayed(self):
        self.player.experiment_start_time = time.time()
        return self.round_number == 1

    def before_next_page(self):
        self.player.prolific_id = self.participant.label
        self.player.study_id = self.session.config.get('study_id')
        self.player.player_session_id = self.session.config.get('session_id')


class ExperimentInstructions(Page):
    def is_displayed(self):
        return self.round_number == 1
    
    def vars_for_template(self):
        return {
            'proposal_timeout': PROPOSAL_TIMEOUT,
            'vote_timeout': VOTE_TIMEOUT,
            'num_rounds': NUMBER_OF_ROUNDS
        }

class SampleInstructions(Page):
    def is_displayed(self):
        return self.round_number == 1
    
    def vars_for_template(self):
        return {
            'num_rounds': NUMBER_OF_ROUNDS
        }

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
class FailedPage(Page):
    # Displays failure message if the player fails the quiz after 3 attempts
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
    form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit']
    # form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit', 'gen', 'other_gender','degree']

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
        

class Nationality_old(Page):
    form_model = 'player'
    # form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit', 'primlang']
    form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit']

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
            "survey_step": 1,
            "total_steps": INTRO_QUESTIONS  
        }

    def before_next_page(self):
        # Store responses
        store_survey_response(self.player, "Education", self.form_fields)

class Gender(Page):
    form_model = 'player'
    # form_fields = ['sex', 'gen', 'other_gender', 'gen_cgi',]
    form_fields = ['gen', 'other_gender']

    # Gender choices mapping
    GENDER_CHOICES = {
        "1": "man or male",
        "2": "woman or female",
        "3": "Other (please specify)",
        # "4": "I use a different term",
        # "5": "I prefer not to answer"
    }

    def is_displayed(self):
        return self.round_number == 1
    
    def vars_for_template(self):
        return {
            "survey_step": 2,
            "total_steps": INTRO_QUESTIONS 
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Gender", self.form_fields)
        
        # If user didn't select "I use a different term"
        if self.player.gen != '3':
            self.player.other_gender = ''
        
        # Assign the provided gender label into "selected_gender" variable or a custom one if 'gen' == '4'
        if str(self.player.gen).strip() == "3":
            self.participant.vars["selected_gender"] = self.player.other_gender  # Custom term
        else:
            self.participant.vars["selected_gender"] = self.GENDER_CHOICES.get(str(self.player.gen), "Not specified")

        # Save gender_cgi for templating in priming/baselin
        # self.participant.vars["gender_expression"] = self.player.gen_cgi

class Party(Page):
    form_model = 'player'
    # form_fields = ['sex', 'gen', 'other_gender', 'gen_cgi',]
    # form_fields = ['party', 'party_closer', 'party_strong_republican', 'party_strong_democrat']
    form_fields = ['spbrn', 'cntbrn', 'spcit', 'other_cit', 'gen', 'other_gender','degree','party', 'party_closer', 'party_strong_republican', 'party_strong_democrat','inc','inc_hh']

    # Gender choices mapping
    GENDER_CHOICES = {
        "1": "man or male",
        "2": "woman or female",
        "3": "Other (please specify)",
    }

    def is_displayed(self):
        return self.round_number == 1
    
    def vars_for_template(self):
        return {
            "survey_step": 3,
            "total_steps": INTRO_QUESTIONS 
        }

    def before_next_page(self):

        # Nationality =================================================================

        if self.player.spbrn != '2':        # If not 'No'
            self.player.cntbrn = ''         # Clear the field
        
        if self.player.spcit != '2':        # If not 'No'
            self.player.other_cit = ''      # Clear the field


        # Gender =================================================================

        if self.player.gen != '3':
            self.player.other_gender = ''
        
        # Assign the provided gender label into "selected_gender" variable or a custom one if 'gen' == '4'
        if str(self.player.gen).strip() == "3":
            self.participant.vars["selected_gender"] = self.player.other_gender  # Custom term
        else:
            self.participant.vars["selected_gender"] = self.GENDER_CHOICES.get(str(self.player.gen), "Not specified")

        # Party =================================================================

        # If user selected "Independent" or "Something Else"
        if self.player.party != '1' and self.player.party != '2':
            self.player.party_strong_republican = ''
            self.player.party_strong_democrat = ''

        # If user selected "Republican" for first question
        if self.player.party == '1':
            # Make strong democrat question unrequired
            self.player.party_strong_democrat = ''
            # Make second question unrequired
            self.player.party_closer = ''

        # If user selected "Democrat" for second question
        if self.player.party == '2':
            # Make strong republican question unrequired
            self.player.party_strong_republican = ''
            # Make second question unrequired
            self.player.party_closer = ''


        # Record response
        store_survey_response(self.player, "Intro_Questions", self.form_fields)



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
    # Completion Link for Prolific

    # def js_vars(player):
    #     return dict(
    #         # completionlink=player.subsession.session.config['completionlink']
    # )
    # pass

# ---------------------------------------------------------------------------------------------------

# PAGE SEQUENCE

page_sequence = [

    WelcomePage,

    # Preliminary Questions
    # IntroQuestions,                       # Inquire Prolific ID
    # Nationality,    
    # Education,      
    # Gender, 
    Party,       
    # Income,        

    # Game Instruction Pages
    ExperimentInstructions,
    SampleInstructions,
    QuizPage,
    FailedPage,
]
