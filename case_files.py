from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivy.properties import StringProperty
from kivymd.uix.card import MDCard
from kivymd.uix.divider import MDDivider
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogIcon,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogContentContainer,
    MDDialogButtonContainer,
)
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.list import MDListItem, MDListItemLeadingIcon, MDListItemSupportingText
from kivymd.uix.label import MDLabel
import hints

class CardItem(MDCard):
    '''Implements a material card.'''
    title = StringProperty("title")
    src = StringProperty("src")
    cases = hints.facts_n_hints 
    case_info = None
    
    def show_case_info(self):
        if self.title != '????':
            self.case_info = MDDialog(
                # -----------------------Headline text-------------------------
                MDDialogHeadlineText(
                    text=self.title,
                ),
                MDDialogSupportingText(
                    text = self.cases[self.title]['Facts'],
                ),
                # -----------------------Custom content------------------------
                MDDialogContentContainer(
                    MDDivider(),
                    MDListItem(
                        MDListItemLeadingIcon(
                            icon="map-marker-account",
                        ),
                        MDListItemSupportingText(
                            text=self.cases[self.title]['Location'],
                        ),
                        theme_bg_color="Custom",
                        md_bg_color=self.theme_cls.transparentColor,
                    ),
                    MDListItem(
                        MDListItemLeadingIcon(
                            icon="knife",
                        ),
                        MDListItemSupportingText(
                            text=self.cases[self.title]['MO'],
                        ),
                        theme_bg_color="Custom",
                        md_bg_color=self.theme_cls.transparentColor,
                    ),
                    MDListItem(
                        MDListItemLeadingIcon(
                            icon="account-details",
                        ),
                        MDListItemSupportingText(
                            text=f"{self.cases[self.title]['Detail']}",
                        ),
                        theme_bg_color="Custom",
                        md_bg_color=self.theme_cls.transparentColor,
                    ),
                    MDDivider(),
                    orientation="vertical",
                    
                ),
                # ---------------------Button container------------------------
                MDDialogButtonContainer(
                    MDButton(
                        MDButtonText(text="Dismiss"),
                        style="text", on_release=lambda x: self.case_info.dismiss(),
                    ),
                    spacing="8dp",
                ),
            )
            self.case_info.open()
        else:
            self.case_info = None
        


class CaseFilesScreen(MDScreen):
    """
    A screen for displaying locked and unlocked cases.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize any additional properties or methods here
        self.cases = list(hints.facts_n_hints.keys())  # List to hold case file data
        self.case_info = list(hints.facts_n_hints.values())
        
    def on_start(self):
        
        for i in range(len(self.cases)):
            if self.case_info[i]['status']=='solved':
                self.ids.grid.add_widget(
                    CardItem(title=self.cases[i], 
                            src="images/unlockedF.png" if 'femme fatales' in self.case_info[i]['Category'] 
                            else "images/unlockedM.png")
                )
            elif self.case_info[i]['status'] != 'solved':
                self.ids.grid.add_widget(
                    CardItem(title="????", 
                            src="images/lockedF.png" if 'femme fatales' in self.case_info[i]['Category'] 
                            else "images/lockedM.png")
                )
        
    

    