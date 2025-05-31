import os
import random
import string
import re
import json
import sys
from kivymd.app import MDApp
import kivymd.icon_definitions
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.button import MDButton, MDButtonText
from kivy.uix.button import Button
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogIcon,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogButtonContainer,
)
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.card import MDCard
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.audio import SoundLoader
from kivy.loader import Loader
import hints
from case_files import CaseFilesScreen, CardItem

LabelBase.register(name='Chiller', 
                   fn_regular=os.path.join(os.getcwd(), 'fonts/CHILLER.TTF'))


background_music = SoundLoader.load("audio/bg_music.wav")
lose_sound = SoundLoader.load("audio/lose_sound.wav")
win_sound = SoundLoader.load("audio/win_sound1.ogg")

def get_app_dir():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running in a normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(get_app_dir(), 'stats.json'), 'r') as f:
    stats = json.load(f)

class StartScreen(MDScreen):
    def __init__(self, **kwargs):
        super(StartScreen, self).__init__(**kwargs)
        self.play_music()

    def play_music(self):
        if background_music:
            print(f"Sound loaded successfully from {background_music.source}")
            background_music.loop = True
            background_music.play()
        else:
            print("Error loading sound")
    
    def choose_category(self, value):
        app = MDApp.get_running_app()
        if value == 'any':
            app.WORD_LIST = list(hints.facts_n_hints.keys())
        else:
            app.WORD_LIST = [k for k, v in hints.facts_n_hints.items() if value in v.get("Category", [])]
    
    def on_category_selected(self, value):
        # This method is called when a category is selected from the dropdown menu.
        # It sets the selected category and updates the WORD_LIST accordingly.
        self.choose_category(value)
        app = MDApp.get_running_app()
        game = app.root.get_screen(name='game')
        game.WORD_LIST = app.WORD_LIST

    def show_info(self):
        self.info_dialog = MDDialog(
            # -----------------------Headline text-------------------------
            MDDialogHeadlineText(
                text="About the game"
            ),
            # -----------------------Supporting text-----------------------
            MDDialogSupportingText(
                text=''' Classic hangman with a True Crime twist.\n\nChoose from a variety of categories.\n[i]Note that some cases may appear in multiple categories[/i]
                \n Check your rank by clicking the police badge icon.\n[i]Zen mode will not affect your rank.[i]
                ''',
                markup=True,
                halign='center'
            ),

            # ---------------------Button container------------------------
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(text = "OK!"),
                    on_release = lambda x: self.info_dialog.dismiss()
                ),
                Widget(),
                spacing = '5dp',
            ))

        self.info_dialog.open()

    def show_rank(self):
        game_screen = HangmanApp.get_running_app().root.get_screen(name='game')
        rank_dialog = MDDialog(
            MDDialogHeadlineText(
                text='Your Stats'
            ),
            MDDialogSupportingText(text=f'Score: {game_screen.SCORE}\n\nBest time: {game_screen.best_time}\n\nCurrent rank: [b]{game_screen.current_rank.upper()}[/b]',
                                   markup=True, font_style='Title', role='medium'),
            MDDialogButtonContainer(
                Widget(), 
                MDButton(
                    MDButtonText(text = "OK!"),
                    on_release = lambda x: rank_dialog.dismiss()
                )
            )
        )
        rank_dialog.open()

    def case_files(self):
        # Open the CaseFilesScreen
        app = HangmanApp.get_running_app()
        app.root.current = 'case_files'
        case_files_screen = app.root.get_screen(name='case_files')
        case_files_screen.on_start()


class SettingsScreen(MDScreen):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)

    def music_on_off(self):
        if background_music.state == 'play':
            background_music.stop()
        else:
            background_music.loop = True
            background_music.play()

    def zen_mode(self):
        game_screen = HangmanApp.get_running_app().root.get_screen(name='game')
        if game_screen.ids.time_label.disabled == False:
            game_screen.ids.time_label.text = "Zen Mode"
            game_screen.ids.time_label.disabled = True
            game_screen.timer_event.cancel()

    def choose_difficulty(self, value):
        game_screen = HangmanApp.get_running_app().root.get_screen(name='game')
        if value == 'easy':
            game_screen.show_letters = ['a', 'e', 'i', 'o', 'u']
            print(self.ids.difficulty.text)
        elif value == 'medium':
            game_screen.show_letters = [i for i in random.choices(string.ascii_lowercase, k=8) if i not in ['a', 'e', 'i', 'o', 'u']]
            print(self.ids.difficulty.text)
        elif value == 'hard':
            game_screen.show_letters = []


class GameScreen(MDScreen):
    def __init__(self, **kwargs):
        super(GameScreen, self).__init__(**kwargs)
        self.win_dialog = None
        self.lose_dialog = None
        self.WORD_LABEL = []
        self.WORD = StringProperty()
        self.GUESSES = []
        self.ERRORS = []
        self.SCORE = stats['score']
        self.n_hints = 0
        self.timer = 0
        self.timer_event = None
        self.show_letters = []
        self.current_rank = stats['rank']
        self.best_time = stats['best_time']
        self.menu = None

    def on_pre_enter(self, *args):
        """Called before the screen is displayed."""
        self.timer = 0
        self.ids.time_label.text = "Time Elapsed: 0s"
        self.start_game()

    def start_game(self, *args):
        app = HangmanApp.get_running_app()
        self.ids.hint.text = ''
        self.WORD_LABEL.clear()
        self.GUESSES.clear()
        self.ERRORS.clear()
        self.n_hints = 0
        self.timer = 0
        # Cancel any existing timer event
        if self.timer_event:
            self.timer_event.cancel()

        # Start the timer
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)

        if app.WORD_LIST:
            self.WORD = random.choice(app.WORD_LIST)
            print(self.WORD)
        else:
            self.WORD = random.choice(list(hints.facts_n_hints.keys()))

        for letter in self.WORD:
            if letter.isalpha():
                if self.show_letters and letter in self.show_letters:
                    self.WORD_LABEL.append(letter.upper())
                else:
                    self.WORD_LABEL.append('_')
            elif letter.isspace():
                self.WORD_LABEL.append('  ')
        self.ids.word.text = ' '.join(self.WORD_LABEL)
        self.ids.error.source = f'images/img0.png'
        return ' '.join(self.WORD_LABEL)
        
    def update_timer(self, dt):
        settings_screen = HangmanApp.get_running_app().root.get_screen(name='settings')
        if not settings_screen.ids.zen_mode.active:
            self.timer += 1
            self.ids.time_label.disabled = False
            self.ids.time_label.text = f"Time Elapsed: {self.timer}s"
            self.ids.score.text = f'Score:\n{self.SCORE}'
            self.ids.score.disabled = False
        elif settings_screen.ids.zen_mode.active:
            self.timer = 0
            self.ids.time_label.text = "Zen Mode"
            self.ids.time_label.disabled = True
            self.SCORE = 0
            self.ids.score.text = f''
            self.ids.score.disabled = True
    
    def menu_open(self):
        if self.n_hints == 3:
            self.ids.hint.text = "You're out of hints"
        else:
            items = ["Location", "Crime Detail", "Person Detail"]
            menu_items = [
                {
                    "text": f"{i}",
                    "on_release": lambda x=i: self.show_hint(x),
                } for i in items
            ]
            self.menu=MDDropdownMenu(
                caller=self.ids.button, items=menu_items
            )
            self.menu.open()

    def show_hint(self, text_item):
        if text_item == "Location":
            hint = f"Active in: {hints.facts_n_hints[self.WORD]['Location']}" 
            self.ids.hint.text = hint
            self.n_hints += 1
            self.menu.dismiss()
        elif text_item == "Crime Detail":
            hint = f"{hints.facts_n_hints[self.WORD]['MO']}" 
            self.ids.hint.text = hint
            self.n_hints += 1
            self.menu.dismiss()
        elif text_item == "Person Detail":
            hint = f"{hints.facts_n_hints[self.WORD]['Detail']}" 
            self.ids.hint.text = hint
            self.n_hints += 1
            self.menu.dismiss()

    def go_to_main_from_dialog(self, instance):
        if self.win_dialog is not None:
            self.win_dialog.dismiss()
            self.switch_screen()
        elif self.lose_dialog is not None:
            self.lose_dialog.dismiss()
            self.switch_screen()

    def switch_screen(self, *args):
        HangmanApp.get_running_app().root.current ='start'

    def show_win_dialog(self):
        if self.timer_event:
            self.timer_event.cancel()

        play_again = MDButton(
            MDButtonText(text="Play Again"),
            style="text")
        play_again.bind(on_release =lambda x: self.win_dialog.dismiss())

        back_to_menu = MDButton(
            MDButtonText(text="Main Menu"),
            style="text")
        back_to_menu.bind(on_release=self.go_to_main_from_dialog)
        
        self.win_dialog = MDDialog(
            MDDialogIcon(
                icon="handcuffs"
            ),
            # -----------------------Headline text-------------------------
            MDDialogHeadlineText(
                text="New case file unlocked!"
            ),
            # -----------------------Supporting text-----------------------
            MDDialogSupportingText(
                text=hints.facts_n_hints[self.WORD]['Facts'],
            ),

            # ---------------------Button container------------------------
            MDDialogButtonContainer(
                Widget(),
                back_to_menu,
                play_again,
                Widget(),
                spacing = '5dp',
            ))

        self.win_dialog.open()
        self.win_dialog.bind(on_dismiss=self.start_game)

    def show_lose_dialog(self):
        if self.timer_event:
            self.timer_event.cancel()
        play_again = MDButton(
            MDButtonText(text="Play Again"),
            style="text")
        play_again.bind(on_release=lambda x: self.lose_dialog.dismiss())

        back_to_menu = MDButton(
            MDButtonText(text="Main Menu"),
            style="text")
        back_to_menu.bind(on_release=self.go_to_main_from_dialog)
        
        self.lose_dialog = MDDialog(
            MDDialogIcon(
                icon="skull-crossbones"
            ),
            # -----------------------Headline text-------------------------
            MDDialogHeadlineText(
                text=f"You Lost, the answer was {self.WORD.upper()}",
            ),
            # -----------------------Supporting text-----------------------
            MDDialogSupportingText(
                text=hints.facts_n_hints[self.WORD]['Facts'],
            ),

            # ---------------------Button container------------------------
            MDDialogButtonContainer(
                Widget(),
                back_to_menu,
                play_again,
                Widget(),
                spacing = '5dp'
            ))

        self.lose_dialog.open()
        self.lose_dialog.bind(on_dismiss=self.start_game)

    def update_rank(self):
        ranks =['Cadet', 'Officer', 'Detective', 'Corporal', 'Sergeant', 'Lieutenant', 'Captain', 'Deputy Chief', 'Chief of Police', 'Commisioner']
        rank_index = min(self.SCORE // 10, len(ranks) - 1)  # Ensure index doesn't exceed the list
        new_rank = ranks[rank_index]
        if new_rank != self.current_rank:
            change_rank_dialog = MDDialog(
                MDDialogIcon(icon="party-popper"),
                MDDialogSupportingText(text=f"Congratulations!\n\nYou're rank is now {new_rank}"),
                MDDialogButtonContainer(
                    MDButton(MDButtonText(text="Yay!"), on_release=lambda x: change_rank_dialog.dismiss())
                )
            )
            change_rank_dialog.open()
        self.current_rank = ranks[rank_index]

    def get_best_time(self):
        if not self.best_time:
            self.best_time = self.timer
        else:
            if self.timer < self.best_time:
                self.best_time = self.timer
            elif self.timer > self.best_time:
                pass
    
    def on_quit_pressed(self, *args):
        # Enable all letter buttons
        if hasattr(self.ids, 'buttons_layout'):
            for button in self.ids.buttons_layout.buttons.values():
                button.disabled = False
        # Optionally, switch to main menu or perform other quit actions
        HangmanApp.get_running_app().root.current = 'start'



class ButtonsLayout(GridLayout):
    def __init__(self, **kwargs):
        super(ButtonsLayout, self).__init__(**kwargs)
        # Configuring the layout.
        self.rows = 2
        self.cols = 13
        self.pos_hint = {'center_x': .5, 'center_y': .9}
        self.size_hint = (1, .2)

        # Creating a dictionary for buttons.
        self.buttons = {}
        
        # Creating the buttons.
        self.create_buttons()

        self.configure_buttons()


    def create_buttons(self):
        # Creating buttons for all the alphabets.
        for alphabet in string.ascii_uppercase:
            # Creating button.
            button = Button(
                text=alphabet,
                size_hint=(.1, .1),
                background_color=(1, 1, 1, .6),
                font_name='Chiller',
                font_size='30dp'
            )
            # Adding button to the layout.
            self.add_widget(button)
            # Adding button to the dictionary.
            self.buttons[alphabet] = button

    def btn_press(self, button, **kwargs):
        game_screen = HangmanApp.get_running_app().root.get_screen(name='game')
        button.disabled = True
        game_screen.GUESSES.append(button.text)
        game_screen.ids.word.text = self.word_display()

    def configure_buttons(self):
        # Bind all the buttons.
        for button in self.buttons.values():
            button.on_press = lambda btn=button: self.btn_press(btn)

    def word_display(self):
        game_screen = HangmanApp.get_running_app().root.get_screen(name='game')
        settings_screen = HangmanApp.get_running_app().root.get_screen(name='settings')
        err_count = 0
        for letter in game_screen.GUESSES:
            for idx, item in enumerate(game_screen.WORD):
                if item.upper() == letter:
                    game_screen.WORD_LABEL[idx] = letter
                    game_screen.ids.word.text = ' '.join(game_screen.WORD_LABEL)
        if game_screen.GUESSES[-1] not in game_screen.WORD.upper():
            game_screen.ERRORS.append(letter)
            err_count = len(game_screen.ERRORS)
            game_screen.ids.error.source = f'images/img{err_count}.png'
        
        if len(re.findall(r"[a-zA-Z]", game_screen.WORD)) == len(re.findall(r"[a-zA-Z]", game_screen.ids.word.text)):
            if not settings_screen.ids.zen_mode.active:
                if len(game_screen.ERRORS) == 0:
                    game_screen.SCORE += 2
                else:
                    game_screen.SCORE += 1
                game_screen.ids.score.text = f'Score:\n{game_screen.SCORE}'
                game_screen.update_rank()
                game_screen.get_best_time()
            win_sound.play()
            game_screen.show_win_dialog()
            hints.facts_n_hints[game_screen.WORD]['status'] = 'solved'
            for button in self.buttons.values():
                button.disabled = False
        elif len(game_screen.ERRORS) == 8:
            lose_sound.play()
            game_screen.show_lose_dialog()
            for button in self.buttons.values():
                button.disabled = False
        game_screen.ids.word.text
        return game_screen.ids.word.text


screen_helper = '''
MDScreenManager: 
    StartScreen: 
        name: "start"
    GameScreen: 
        name: "game"
    SettingsScreen: 
        name: "settings"
    CaseFilesScreen:
        name: "case_files"
'''

def save_stats(*args, **kwargs):
    game_screen = HangmanApp.get_running_app().root.get_screen(name='game')
    stats = {
        "score": game_screen.SCORE,
        "best_time": game_screen.best_time,
        "rank": game_screen.current_rank

    }
    with open(os.path.join(get_app_dir(), 'stats.json'), "w") as f:
        json.dump(stats, f)

    with open(os.path.join(get_app_dir(), 'hints.py'), 'w') as f:
        facts_n_hints = hints.facts_n_hints
        f.write(f"facts_n_hints = {json.dumps(facts_n_hints, indent=4)}\n")

class HangmanApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.WORD_LIST = []

    def build(self):
        self.title = "Hangman - Noose of Justice"
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.theme_style = "Dark"
        self.root = Builder.load_string(screen_helper)
        return self.root
    
    def on_stop(self):
        save_stats()
    


if __name__ == '__main__':
    HangmanApp().run()