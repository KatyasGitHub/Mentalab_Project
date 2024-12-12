import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

class EEGApp_CoverSlide(QWidget):
    """Cover Slide displayed at the start."""
    def __init__(self, switch_to_main):
        super().__init__()
        self.switch_to_main = switch_to_main  
        self.setFixedSize(1100, 620)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Add logo
        logo_label = QLabel(self)
        script_dir = os.path.dirname(os.path.abspath(__file__)) 
        project_dir = os.path.dirname(script_dir)
        image_path = os.path.join(project_dir, "resources", "logo_transparent.png")
        logo_pixmap = QPixmap(image_path)
        logo_label.setPixmap(logo_pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        
        # Add title
        title_label = QLabel("Mentalab EEG Data Analysis Tool")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; margin-bottom: 20px;")

        # Add load button
        load_button = QPushButton("Let's get started!")
        load_button.setStyleSheet("padding: 10px; font-size: 20px;")
        load_button.clicked.connect(self.switch_to_main)

        # Add elements to layout
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(title_label, alignment=Qt.AlignCenter)
        layout.addWidget(load_button, alignment=Qt.AlignCenter)
        self.setLayout(layout)
