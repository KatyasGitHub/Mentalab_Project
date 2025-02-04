import sys
from PyQt5.QtWidgets import QApplication
from application import EEGApp
import os
os.environ["MNE_DISABLE_LAZY"] = "1" # needed for the icon on the Desktop


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = EEGApp()
    ex.show()
    sys.exit(app.exec_())