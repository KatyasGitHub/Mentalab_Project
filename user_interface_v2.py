import sys
from PyQt5.QtWidgets import (QMainWindow, QApplication, QMenu, QAction, QFileDialog, QHBoxLayout, 
                             QListWidget, QVBoxLayout, QCheckBox, QPushButton, QWidget,
                             QLabel, QLineEdit, QDialog, QFormLayout, QMessageBox, QListWidgetItem)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from mne import create_info
from mne.io import RawArray
from mne.viz import use_browser_backend
from mne.filter import notch_filter, filter_data

class EEGApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("EEG Data Analysis Tool")
        self.setGeometry(300, 200, 1300, 700)

        # Placeholder variables for loaded data
        self.data = None
        self.file_name = ""
        self.channel_names = []
        self.filtered_data = None  # To store filtered data
        self.channel_checkboxes = []
        
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('File')
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.load_file)
        file_menu.addAction(open_action)
        
        export_action = QAction('Export', self)
        export_action.triggered.connect(self.export_file)
        file_menu.addAction(export_action)
        
        # edit_menu = menubar.addMenu('Edit')
        # edit_action = QAction('Edit Channels', self)
        # edit_action.triggered.connect(self.edit_channels)
        # edit_menu.addAction(edit_action)

        # plot_menu = menubar.addMenu('Plot')
        # plot_action = QAction('Plot Selected Channels', self)
        # plot_action.triggered.connect(self.plot_selected_channels)
        # plot_menu.addAction(plot_action)
        
        filter_menu = menubar.addMenu('Filters')
        filter_action = QAction('Apply Filters', self)
        filter_action.triggered.connect(self.apply_filters)
        filter_menu.addAction(filter_action)
        
        # Left Panel - File and Channels
        self.file_list = QListWidget()
        self.channel_list = QListWidget()
        
        # Layouts
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("Loaded Files"))
        self.file_list = QListWidget()
        left_panel_layout.addWidget(self.file_list)
        self.file_list.itemClicked.connect(self.on_file_clicked)
        
        left_panel_layout.addWidget(QLabel("Channels"))
        self.channel_list.setSelectionMode(QListWidget.MultiSelection)
        for ch in self.channel_names:
            item = QListWidgetItem(ch)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.channel_list.addItem(item)
        
        left_panel_layout.addWidget(self.channel_list)

        # Add Save Button
        save_button = QPushButton("Plot")
        save_button.clicked.connect(self.update_plot_with_selected_channels)
        left_panel_layout.addWidget(save_button)
        
        left_panel = QWidget()
        left_panel.setLayout(left_panel_layout)
        
        # Right Panel - Free space for plotting
        self.plot_area = QVBoxLayout()
        right_panel = QWidget()
        right_panel.setLayout(self.plot_area)
        right_panel_layout = QVBoxLayout()
        right_panel.setLayout(right_panel_layout)
        
        # Main Layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_panel, 1)  # Left panel takes 1/3 of the space
        main_layout.addWidget(right_panel, 2)  # Right panel takes 2/3 of the space
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
    

    def load_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)", options=options)
        if file_name:
            self.file_name = file_name
            self.data = pd.read_csv(file_name)
            self.channel_names = list(self.data.columns[1:])  
            file_display_name = file_name.split('/')[-1]
            if not hasattr(self, 'file_channels'): # hasattr is used to check whether an object has a specific attribute
                self.file_channels = {}
            self.file_channels[file_display_name] = self.channel_names
            self.file_list.addItem(file_display_name)

    def on_file_clicked(self, item):
        file_display_name = item.text()
        if hasattr(self, 'file_channels') and file_display_name in self.file_channels:
            self.channel_names = self.file_channels[file_display_name]
            self.update_channel_list()

    def update_channel_list(self):
        self.channel_list.clear()
        for ch in self.channel_names:
            item = QListWidgetItem(ch)
            self.channel_list.addItem(item)
            item.setCheckState(Qt.Checked)
            checkbox = QCheckBox(ch)
            checkbox.setChecked(True)  
            self.channel_checkboxes.append(checkbox)

    def edit_channels(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Channels")
        
        layout = QVBoxLayout()
        
        for ch in self.channel_names:
            checkbox = QCheckBox(ch)
            checkbox.setChecked(True)
            layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(dialog.accept)
        layout.addWidget(save_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def get_selected_channels(self):
        return [cb.text() for cb in self.channel_checkboxes if cb.isChecked()]

    def update_plot_with_selected_channels (self):
        selected_channels = []
        for index in range(self.channel_list.count()):
            item = self.channel_list.item(index)
            if item.checkState() == Qt.Checked:
                selected_channels.append(item.text())

        if not selected_channels:
            QMessageBox.warning(self, "No Channels Selected", "Please select at least one channel to plot.")
            return

        selected_data = self.data[selected_channels].to_numpy().T
        timestamps = self.data.iloc[:, 0].to_numpy()  # Assuming first column is timestamps

        try:
            sfreq = 1 / np.mean(np.diff(timestamps))
        except ZeroDivisionError:
            QMessageBox.critical(self, "Error", "Timestamps are not properly spaced.")
            return

        info = create_info(ch_names=selected_channels, sfreq=sfreq, ch_types='eeg')
        raw = RawArray(selected_data, info)

        raw.set_annotations(None)
        while self.plot_area.count():
            widget = self.plot_area.takeAt(0).widget()
            if widget:
                widget.deleteLater()

        with use_browser_backend("qt"):
            browser = raw.plot(scalings="auto", overview_mode="hidden")
            self.plot_area.addWidget(browser)

    def apply_filters(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Apply Filters")
        
        layout = QFormLayout()
        low_cut = QLineEdit()
        high_cut = QLineEdit()
        notch = QLineEdit()
        layout.addRow("Low Cutoff Frequency (Hz):", low_cut)
        layout.addRow("High Cutoff Frequency (Hz):", high_cut)
        layout.addRow("Notch Filter Frequency (Hz):", notch)
        
        re_ref_checkbox = QCheckBox("Average Re-referencing")
        dc_offset_checkbox = QCheckBox("DC Offset Correction")
        layout.addWidget(re_ref_checkbox)
        layout.addWidget(dc_offset_checkbox)
        
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(lambda: self.filter_data(low_cut, high_cut, notch, re_ref_checkbox, dc_offset_checkbox))
        layout.addWidget(apply_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    

    def filter_data(self, low_cut, high_cut, notch, re_ref, dc_offset):
        selected_channels = self.get_selected_channels()
        data = self.data[selected_channels].to_numpy().T
        name = ''
        

        sfreq = 100  # Adjust as necessary
        if low_cut.text():
            data = filter_data(data, sfreq, l_freq=float(low_cut.text()), h_freq=None)
            name += ' LP'
        if high_cut.text():
            data = filter_data(data, sfreq, l_freq=None, h_freq=float(high_cut.text()))
            name += ' HP'
        if notch.text():
            data = notch_filter(data, sfreq, freqs=float(notch.text()))
            name += ' Notch'
        if re_ref.isChecked():
            data = data - data.mean(axis=0)
            name += ' ReRef'
        if dc_offset.isChecked():
            data = data - np.mean(data, axis=1, keepdims=True)
            name += ' DC'
        
        # Store filtered data for export
        self.filtered_data = pd.DataFrame(data.T, columns=selected_channels)
        self.filtered_data.insert(0, "Timestamps", self.data.iloc[:, 0])

        file_name = self.file_name + name
        self.filtered_data.to_csv(file_name, index=False)
        self.file_list.addItem(file_name.split('/')[-1])

        QMessageBox.information(self, "Filter Applied", "Filters applied successfully.")



    def export_file(self):
        if self.filtered_data is None:
            QMessageBox.warning(self, "No Filtered Data", "Please apply filters before exporting.")
            return
        
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, self.file_name, "", "CSV Files (*.csv)", options=options)
        if file_name:
            self.filtered_data.to_csv(file_name, index=False)
            QMessageBox.information(self, "Export Success", "Filtered data saved successfully.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = EEGApp()
    ex.show()
    sys.exit(app.exec_())