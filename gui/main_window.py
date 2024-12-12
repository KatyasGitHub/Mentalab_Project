import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QStackedWidget, QAction, QFileDialog, QHBoxLayout, 
    QListWidget, QVBoxLayout, QCheckBox, QPushButton, QWidget,
    QLabel, QLineEdit, QDialog, QFormLayout, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mne import create_info
from mne.io import RawArray
from mne.viz import use_browser_backend
from mne.filter import notch_filter, filter_data
from gui.fft_canvas import FFTCanvas

class EEGApp_Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("EEG Data Analysis Tool")
        self.setGeometry(300, 200, 1100, 620)
        self.current_toolbar = None
        self.file_data_store = {}
        self.file_frequency_store = {}
        self.sampling_frequency = None

        self.data = None
        self.file_name = ""
        self.channel_names = []
        self.channel_checkboxes = []
        self.current_plot_widget = None  # To keep track of the current plot widget

        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('File')
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.load_file)
        file_menu.addAction(open_action)
        
        export_action = QAction('Export', self)
        export_action.triggered.connect(self.export_file)
        file_menu.addAction(export_action)
        
        filter_menu = menubar.addMenu('Filters')
        filter_action = QAction('Apply Filters', self)
        filter_action.triggered.connect(self.apply_filters)
        filter_menu.addAction(filter_action)
        
        # Left Panel - File and Channels
        left_panel_layout = QVBoxLayout()
        loaded_files = QLabel("Loaded Files")
        loaded_files.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_panel_layout.addWidget(loaded_files)
        self.file_list = QListWidget()
        left_panel_layout.addWidget(self.file_list)
        self.file_list.itemClicked.connect(self.on_file_clicked)
        
        channels = QLabel("Channels")
        channels.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_panel_layout.addWidget(channels)
        self.channel_list = QListWidget()
        self.channel_list.setSelectionMode(QListWidget.MultiSelection)
        left_panel_layout.addWidget(self.channel_list)
        
        # Add Plot Buttons
        plot_time_button = QPushButton("Plot Time Domain")
        plot_time_button.clicked.connect(self.update_time_plot)
        left_panel_layout.addWidget(plot_time_button)
        
        plot_fft_button = QPushButton("FFT Plot")
        plot_fft_button.clicked.connect(self.update_fft_plot)
        left_panel_layout.addWidget(plot_fft_button)
        
        left_panel_layout.addStretch()
        
        left_panel = QWidget()
        left_panel.setLayout(left_panel_layout)
        
        # Right Panel - Plotting Area
        self.plot_area = QVBoxLayout()
        right_panel = QWidget()
        right_panel.setLayout(self.plot_area)

        logo_label = QLabel()
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
        image_path = os.path.join(script_dir, "logo_transparent.png")
        logo_pixmap = QPixmap(image_path)
        logo_label.setPixmap(logo_pixmap.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Main Layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_panel, 1)  # Left panel takes 1/3 of the space
        main_layout.addWidget(right_panel, 2)  # Right panel takes 2/3 of the space

        logo_layout = QVBoxLayout()
        logo_layout.addWidget(logo_label, alignment=Qt.AlignRight | Qt.AlignTop)
        main_layout.addLayout(logo_layout) 

        
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

            # Store the original dataset in the data store
            self.file_data_store[file_display_name] = self.data
            self.file_list.addItem(file_display_name)

            if not hasattr(self, 'file_channels'):
                self.file_channels = {}
            self.file_channels[file_display_name] = self.channel_names

        # META FILE IMPLEMENTATION
        folder = os.path.dirname(file_name)
        base_name = os.path.basename(file_name).split('.')[0]
        meta_file_path = os.path.join(folder, f"{base_name}_Meta.csv")
        
        sampling_frequency = None  
        
        if os.path.exists(meta_file_path):
            print(f"Metadata file found: {meta_file_path}")
            try:
                # Read metadata file
                meta_data = pd.read_csv(meta_file_path, header=None)
                if len(meta_data) > 1 and len(meta_data.columns) > 2:
                    # Extract sampling frequency (sr) from second row, third column
                    sampling_frequency = float(meta_data.iloc[1, 2])
                    print(f"Sampling frequency extracted from metadata: {sampling_frequency} Hz")
                else:
                    print("Error: Metadata file is improperly formatted.")
            except Exception as e:
                print(f"Error reading metadata file: {e}")
        else:
            print(f"No metadata file found for {file_name}.")
        
        # If no sampling frequency found, compute it from timestamps
        if sampling_frequency is None:
            print("Attempting to compute sampling frequency from timestamps...")
            if 'TimeStamp' in self.data.columns[0]:
                timestamps = self.data.iloc[:, 0].values  # Assume first column contains timestamps
                sampling_frequency = 1 / np.mean(np.diff(timestamps))
                print(f"Computed sampling frequency: {sampling_frequency:.2f} Hz")
            else:
                print("Timestamps not found in the data, unable to compute sampling frequency.")
        
        if sampling_frequency:
            self.file_frequency_store[file_display_name] = sampling_frequency
            print(f"Final Sampling Frequency for {file_display_name}: {sampling_frequency} Hz")
        else:
            self.file_frequency_store[file_display_name] = None
            print(f"Sampling frequency for {file_display_name} could not be determined.")
    
    def on_file_clicked(self, item):
        file_display_name = item.text()
        if file_display_name in self.file_data_store:
            self.data = self.file_data_store[file_display_name]
            self.channel_names = list(self.data.columns[1:])
            self.update_channel_list()
            self.sampling_frequency = self.file_frequency_store.get(file_display_name, None)
        else:
            QMessageBox.warning(self, "File Not Found", f"The file {file_display_name} is not available.")

    def update_channel_list(self):
        self.channel_list.clear()
        self.channel_checkboxes = []  # Reset checkboxes
        for ch in self.channel_names:
            item = QListWidgetItem(ch)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.channel_list.addItem(item)
            self.channel_checkboxes.append(item)

    def get_selected_channels(self):
        return [item.text() for item in self.channel_checkboxes if item.checkState() == Qt.Checked]

    def clear_plot_area(self):
        """Clears the current plot widget and toolbar from the plot area."""
        if self.current_plot_widget is not None:
            self.plot_area.removeWidget(self.current_plot_widget)
            self.current_plot_widget.deleteLater()
            self.current_plot_widget = None
        
        if self.current_toolbar is not None:
            self.plot_area.removeWidget(self.current_toolbar)
            self.current_toolbar.deleteLater()
            self.current_toolbar = None

    def update_time_plot(self):
        selected_channels = self.get_selected_channels()
        if not selected_channels:
            QMessageBox.warning(self, "No Channels Selected", "Please select at least one channel to plot.")
            return
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file from the list.")
            return

        file_display_name = current_item.text()
        if file_display_name in self.file_data_store:
            current_data = self.file_data_store[file_display_name]
        else:
            QMessageBox.warning(self, "Data Not Found", f"No data found for {file_display_name}.")
            return

        # selected_data = self.filtered_data[selected_channels].to_numpy().T if self.filtered_data is not None else self.data[selected_channels].to_numpy().T
        # timestamps = self.data.iloc[:, 0].to_numpy()  # Assuming first column is timestamps
        # sfreq = 1 / np.mean(np.diff(timestamps))
        sfreq = self.file_frequency_store.get(file_display_name, None)
        selected_data = current_data[selected_channels].to_numpy().T
        # timestamps = current_data.iloc[:, 0].to_numpy()  # Assume the first column is timestamps
        # sfreq = self.file_frequency_store.get(file_display_name, 1.0)

        # Create MNE Raw object
        info = create_info(ch_names=selected_channels, sfreq=sfreq, ch_types='eeg')
        raw = RawArray(selected_data, info)
        raw.set_annotations(None)

        # Clear existing plot
        self.clear_plot_area()

        # Embed MNE plot into the plot area
        with use_browser_backend("qt"):
            browser = raw.plot(scalings="auto", overview_mode="hidden")
            self.plot_area.addWidget(browser)
            self.current_plot_widget = browser

    def update_fft_plot(self):
        selected_channels = self.get_selected_channels()
        if not selected_channels:
            QMessageBox.warning(self, "No Channels Selected", "Please select at least one channel to plot.")
            return

        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file from the list.")
            return

        file_display_name = current_item.text()
        if file_display_name in self.file_data_store:
            current_data = self.file_data_store[file_display_name]
        else:
            QMessageBox.warning(self, "Data Not Found", f"No data found for {file_display_name}.")
            return

        # selected_data = self.filtered_data[selected_channels].to_numpy().T if self.filtered_data is not None else self.data[selected_channels].to_numpy().T
        # timestamps = self.data.iloc[:, 0].to_numpy()  # Assuming first column is timestamps
        # sfreq = 1 / np.mean(np.diff(timestamps))
        sfreq = self.file_frequency_store.get(file_display_name, None)
        selected_data = current_data[selected_channels].to_numpy().T
        timestamps = self.data.iloc[:, 0].to_numpy()  # Assuming first column is timestamps
        # sfreq = 1 / np.mean(np.diff(timestamps))

        n = len(timestamps)
        freqs = np.fft.rfftfreq(n, d=1/sfreq)

        # Clear existing plot and toolbar
        self.clear_plot_area()

        # Create FFT canvas
        fft_canvas = FFTCanvas(self, width=5, height=4, dpi=100)
        for idx, ch in enumerate(selected_channels):
            yf = np.fft.rfft(selected_data[idx])
            yf_magnitude = np.abs(yf) / n
            fft_canvas.axes_fft.plot(freqs, yf_magnitude, label=ch)
        fft_canvas.axes_fft.set_title("Frequency Domain (FFT) Signals")
        fft_canvas.axes_fft.set_xlabel("Frequency (Hz)")
        fft_canvas.axes_fft.set_ylabel("Magnitude")
        fft_canvas.axes_fft.legend(loc='upper right', fontsize='small')
        fft_canvas.axes_fft.set_xlim(0, sfreq / 2)  # Ensures x-axis matches Nyquist
        fft_canvas.fig.tight_layout()
        fft_canvas.draw()

        # Create and add the Navigation Toolbar
        toolbar = NavigationToolbar(fft_canvas, self)
        self.plot_area.addWidget(toolbar)
        self.current_toolbar = toolbar

        # Add FFT plot to the plot area
        self.plot_area.addWidget(fft_canvas)
        self.current_plot_widget = fft_canvas

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
        apply_button.clicked.connect(lambda: self.filter_data(low_cut, high_cut, notch, re_ref_checkbox, dc_offset_checkbox, dialog))
        layout.addWidget(apply_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def filter_data(self, low_cut, high_cut, notch, re_ref, dc_offset, dialog):
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file to filter.")
            return

        file_display_name = current_item.text()
        selected_channels = self.get_selected_channels()
        # Retrieve the selected dataset from the dictionary
        if file_display_name not in self.file_data_store:
            QMessageBox.warning(self, "Data Not Found", f"No data found for {file_display_name}.")
            return

        data = self.file_data_store[file_display_name]
        data = data[selected_channels].to_numpy().T 
        sfreq = self.file_frequency_store.get(file_display_name, None)
        name_suffix = ""
        if sfreq is None:
            QMessageBox.warning(self, "Sampling Frequency Not Found", "No sampling frequency found for the selected file.")
            return

        if low_cut.text():
            try:
                data = filter_data(data, sfreq, l_freq=float(low_cut.text()), h_freq=None)
                name_suffix += f'_HP{low_cut.text()}Hz'
            except ValueError:
                QMessageBox.warning(self, "Invalid Low Cutoff", "Please enter a valid low cutoff frequency.")
                return
        if high_cut.text():
            try:
                data = filter_data(data, sfreq, l_freq=None, h_freq=float(high_cut.text()))
                name_suffix += f'_LP{high_cut.text()}Hz'
            except ValueError:
                QMessageBox.warning(self, "Invalid High Cutoff", "Please enter a valid high cutoff frequency.")
                return
        if notch.text():
            try:
                data = notch_filter(data, sfreq, freqs=float(notch.text()))
                name_suffix += f'_Notch{notch.text()}Hz'
            except ValueError:
                QMessageBox.warning(self, "Invalid Notch Frequency", "Please enter a valid notch filter frequency.")
                return
        if re_ref.isChecked():
            data = data - data.mean(axis=0)
            name_suffix += '_ReRef'
        if dc_offset.isChecked():
            data = data - np.mean(data, axis=1, keepdims=True)
            name_suffix += '_DC'

        # Store filtered data for export
        filtered_data = pd.DataFrame(data.T, columns=selected_channels)
        filtered_data.insert(0, "Timestamps", self.data.iloc[:, 0])

        # Generate a new filename for the filtered data
        filtered_file_name = file_display_name.replace('.csv', f'{name_suffix}.csv')

        self.file_data_store[filtered_file_name] = filtered_data
        self.file_frequency_store[filtered_file_name] = sfreq
        self.file_list.addItem(filtered_file_name)

        QMessageBox.information(self, "Filter Applied", "Filters applied successfully.")
        dialog.accept()

    def export_file(self): 
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file to export.")
            return

        file_display_name = current_item.text()

        # Retrieve the selected dataset from the dictionary
        if file_display_name not in self.file_data_store:
            QMessageBox.warning(self, "Data Not Found", f"No data found for {file_display_name}.")
            return

        current_data = self.file_data_store[file_display_name]

        # Open file dialog to select export location
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Filtered Data", f"{file_display_name}", "CSV Files (*.csv)", options=options)
        
        if file_name:
            try:
                # Export the data to the selected file
                current_data.to_csv(file_name, index=False)
                QMessageBox.information(self, "Export Success", f"File '{file_display_name}' has been successfully exported to '{file_name}'.")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"An error occurred while exporting: {e}")
