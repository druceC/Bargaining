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
INTRO_QUESTIONS = 3
SURVEY_PAGES = 11

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
            "survey_step": 1,
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
            "survey_step": 2,
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
            "survey_step": 3,
            "total_steps": INTRO_QUESTIONS  # Adjust based on survey length
        }
    
    def before_next_page(self):
        # Record response
        store_survey_response(self.player, "Income", self.form_fields)


# ---------------------------------------------------------------------------------------------------  

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


    # Completion Link for Prolific

    # def js_vars(player):
    #     return dict(
    #         # completionlink=player.subsession.session.config['completionlink']
    # )
    # pass

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
    # # IntroQuestions, 
    # Nationality,    
    # Education,      
    # Gender,       
    # Income,         

    # # Game Instructions
    # ExperimentInstructions,
    # SampleInstructions,
    QuizPage,
    FailedPage,
]
