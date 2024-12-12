from PyQt5.QtWidgets import QStackedWidget
from gui.cover_slide import EEGApp_CoverSlide
from gui.main_window import EEGApp_Main

class EEGApp(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Show Initial Window
        cover_slide = EEGApp_CoverSlide(self.switch_to_main)
        self.main_ui = EEGApp_Main()

        self.addWidget(cover_slide)
        self.addWidget(self.main_ui)

        self.setCurrentIndex(0)

    # Switches to the Main Window when the button "Let's get started!" is pressed 
    def switch_to_main(self):
        self.setCurrentIndex(1)
