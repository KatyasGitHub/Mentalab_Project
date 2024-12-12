import sys
from PyQt5.QtWidgets import QApplication
from application import EEGApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = EEGApp()
    ex.show()
    sys.exit(app.exec_())