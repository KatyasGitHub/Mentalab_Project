import os
import pandas as pd
import numpy as np
import mne
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QHBoxLayout, 
    QListWidget, QVBoxLayout, QCheckBox, QPushButton, QWidget,
    QLabel, QLineEdit, QDialog, QFormLayout, QMessageBox, QListWidgetItem,
    QMenu, QSlider
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import Slider
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from mne.io import RawArray
from mne.viz import use_browser_backend
from mne.filter import notch_filter, filter_data
from mne import export
from gui.fft_canvas import FFTCanvas
from scipy.signal import welch, spectrogram

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
        self.file_format_store = {}
        self.file_channels = {}
        self.sampling_frequency = None
        

        self.data = None
        self.file_name = ""
        self.channel_names = []
        self.channel_checkboxes = []
        self.current_plot_widget = None  # To keep track of the current plot widget

        menubar = self.menuBar()
        self.all_buttons = []
        
        # Menu Bar
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

        # Left Panel - File, Channels and Plotting Buttons
        left_panel_layout = QVBoxLayout()

        load_files_layout = QHBoxLayout()
        loaded_files = QLabel("Loaded Files")
        loaded_files.setStyleSheet("font-size: 18px; font-weight: bold;")
        load_files_layout.addWidget(loaded_files)
        delete_files_button = QPushButton("Delete File")
        delete_files_button.setFixedSize(100, 35)  # Make the button very small
        delete_files_button.setToolTip("Delete Selected File")
        delete_files_button.clicked.connect(self.delete_files)
        load_files_layout.addWidget(delete_files_button)
        left_panel_layout.addLayout(load_files_layout)

        self.file_list = QListWidget()
        left_panel_layout.addWidget(self.file_list)
        self.file_list.itemClicked.connect(self.on_file_clicked)

        # convert_button = QPushButton("Convert CSV <-> BDF")
        # convert_button.clicked.connect(self.convert_selected_file)
        # left_panel_layout.addWidget(convert_button)
        # self.all_buttons.append(convert_button)

        channels_layout = QHBoxLayout()
        channels_label = QLabel("Channels")
        channels_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        channels_layout.addWidget(channels_label)
        clear_channels_button = QPushButton("Clear All")
        self.all_buttons.append(clear_channels_button)
        clear_channels_button.setFixedSize(100, 35)  # Make the button very small
        clear_channels_button.setToolTip("Clear all selected channels")
        clear_channels_button.clicked.connect(self.clear_all_channels)
        channels_layout.addWidget(clear_channels_button)
        left_panel_layout.addLayout(channels_layout)

        self.channel_list = QListWidget()
        self.channel_list.setSelectionMode(QListWidget.MultiSelection)
        left_panel_layout.addWidget(self.channel_list)
        
        plot_time_button = QPushButton("Plot Time Domain")
        plot_time_button.clicked.connect(self.update_time_plot)
        left_panel_layout.addWidget(plot_time_button)
        self.all_buttons.append(plot_time_button)
        
        plot_fft_button = QPushButton("FFT Plot")
        plot_fft_button.clicked.connect(self.update_fft_plot)
        left_panel_layout.addWidget(plot_fft_button)
        self.all_buttons.append(plot_fft_button)

        plot_power_density_button = QPushButton("Bandpower Visualization")
        menu = QMenu()
        time_action = menu.addAction("Time Domain")
        bars_action = menu.addAction("Bars ")
        plot_power_density_button.setMenu(menu)
        time_action.triggered.connect(self.update_bandpower_visualization)
        bars_action.triggered.connect(self.update_bandpower_bars_visualization)
        left_panel_layout.addWidget(plot_power_density_button)
        self.all_buttons.append(plot_power_density_button)

        plot_power_density_button = QPushButton("Power Spectrum Density")
        plot_power_density_button.clicked.connect(self.update_psd_visualization)
        left_panel_layout.addWidget(plot_power_density_button)
        self.all_buttons.append(plot_power_density_button)

        plot_power_density_button = QPushButton("Spectogram")
        plot_power_density_button.clicked.connect(self.update_spectogram_visualization)
        left_panel_layout.addWidget(plot_power_density_button)
        self.all_buttons.append(plot_power_density_button)

        self.update_buttons_state()
        
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


    def update_buttons_state(self):
        """Enable or disable buttons based on whether the file is selected and the selected file has a valid sampling frequency."""
        current_item = self.file_list.currentItem()
        
        if not current_item:
            has_valid_sampling_freq = False
        else:
            file_display_name = current_item.text()
            has_valid_sampling_freq = self.file_frequency_store.get(file_display_name) is not None

        for button in self.all_buttons:
            button.setEnabled(has_valid_sampling_freq)


    def load_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV or BDF File", "", options=options)
        if not file_name:
            return
        self.file_name = file_name
        file_display_name = file_name.split('/')[-1]
        channel_names = []
        if os.path.basename(file_name).split('.')[1] == "csv":
            self.file_name = file_name
            self.data = pd.read_csv(file_name)
            channel_names = list(self.data.columns[1:])

            self.file_data_store[file_display_name] = self.data.div(1e6)   # store raw dataset in the data store
            self.file_list.addItem(file_display_name) # add the name of the file to the list widget

            self.file_channels[file_display_name] = channel_names
            self.file_format_store[file_display_name] = 'csv'

            # If the is a _Meta.csv file -> get sampling frequency from it 
            folder = os.path.dirname(file_name)
            base_name = os.path.basename(file_name).split('.')[0]
            modified_base_name = base_name.replace("ExG", "")
            meta_file_path = os.path.join(folder, f"{modified_base_name}Meta.csv")
            
            sampling_frequency = None  
            
            if os.path.exists(meta_file_path):
                print(f"Metadata file found")
                try:
                    sampling_frequency = pd.read_csv(meta_file_path, delimiter=',')['sr'][0]
                    print(f"Sampling frequency extracted from metadata: {sampling_frequency} Hz")
                except Exception as e:
                    print(f"Error reading metadata file: {e}")
            else:
                print(f"No metadata file found for {file_name}.")
            
            # If no sampling frequency found, compute it from timestamps
            if sampling_frequency is None:
                if 'TimeStamp' in self.data.columns[0]:
                    timestamps = self.data.iloc[:, 0].values 
                    sampling_frequency = 1 / np.mean(np.diff(timestamps))
                    print(f"Computed sampling frequency: {sampling_frequency:.2f} Hz")
                else:
                    print("Timestamps not found in the data, unable to compute sampling frequency.")
            
            if sampling_frequency:
                self.file_frequency_store[file_display_name] = sampling_frequency
            else:
                self.file_frequency_store[file_display_name] = None
                QMessageBox.warning(self, "Warning", 
                    "The file has no related metadata file as well as no timestamps included. Filtering and Plotting will not work for this file.",
                    QMessageBox.Ok)

        elif os.path.basename(file_name).split('.')[1] == "bdf":
            try:
                raw_data = mne.io.read_raw_bdf(file_name, preload=True)
                sampling_frequency = raw_data.info['sfreq']  # Extract sampling frequency
                channel_names = raw_data.ch_names[1:]  # Extract channel names

                # Store raw dataset (in MNE Raw format)
                self.file_data_store[file_display_name] = raw_data
                self.file_list.addItem(file_display_name)

                self.file_channels[file_display_name] = channel_names

                self.file_frequency_store[file_display_name] = sampling_frequency
                self.file_format_store[file_display_name] = 'bdf'
                print(f"Loaded BDF file: {file_name} with {sampling_frequency} Hz sampling rate.")
            
            except Exception as e:
                print(f"Error loading BDF file: {e}")
                self.file_frequency_store[file_display_name] = None
        else:
            print(f"The format is not supported. Please choose a .csv of .bdf file.")
        self.update_buttons_state()
    

    def convert_selected_file(self):
        """Converts the currently selected file from CSV to BDF or BDF to CSV."""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file from the list.")
            return

        file_display_name = current_item.text()
        if file_display_name not in self.file_data_store:
            QMessageBox.warning(self, "Data Not Found", f"No data found for {file_display_name}.")
            return

        data_obj = self.file_data_store[file_display_name]

        # -- Distinguish CSV (DataFrame) from BDF (Raw) --
        if isinstance(data_obj, pd.DataFrame):
            # CSV --> BDF
            df = data_obj

            # Extract sampling frequency as stored
            sfreq = self.file_frequency_store.get(file_display_name)

            # If 'TimeStamp' column not present, either compute or skip
            if 'TimeStamp' in df.columns:
                timestamps = df['TimeStamp'].values
            else:
                # e.g. estimate from data
                timestamps = np.arange(len(df)) / sfreq

            channel_names = df.columns[1:]  # first column is 'TimeStamp'
            data_array = df[channel_names].to_numpy().T

            info = mne.create_info(ch_names=list(channel_names), sfreq=sfreq, ch_types='eeg')
            raw = RawArray(data_array, info)

            # # Ask user where to save
            # save_path, _ = QFileDialog.getSaveFileName(self, "Save BDF", "", "BDF Files (*.bdf)")
            # if not save_path:
            #     return
            # raw.save(save_path, overwrite=True)

            # Add new BDF to file list and data structures
            # new_display = os.path.basename(save_path)
            new_file_display_name = file_display_name.replace(".csv", ".bdf")
            self.file_data_store[new_file_display_name] = raw
            self.file_channels[new_file_display_name] = raw.ch_names
            self.file_frequency_store[new_file_display_name] = sfreq
            self.file_list.addItem(new_file_display_name)

        elif isinstance(data_obj, mne.io.BaseRaw):
            # BDF --> CSV
            raw_data = data_obj
            sfreq = raw_data.info['sfreq']
            data_array = raw_data.get_data()
            timestamps = np.arange(data_array.shape[1]) / sfreq

            # Build a DataFrame (first col is 'TimeStamp')
            channel_names = raw_data.ch_names
            df = pd.DataFrame(data_array.T, columns=channel_names)
            # Avoid "already exists" error:
            if 'TimeStamp' not in df.columns:
                df.insert(0, 'TimeStamp', timestamps)
            else:
                # overwrite existing column if you want
                df['TimeStamp'] = timestamps  

            # Add new CSV to file list and data structures
            new_file_display_name = file_display_name.replace(".bdf", ".csv")
            self.file_data_store[new_file_display_name] = df
            self.file_channels[new_file_display_name] = list(df.columns[1:])  # skip 'TimeStamp'
            self.file_frequency_store[new_file_display_name] = sfreq
            self.file_list.addItem(new_file_display_name)

        else:
            QMessageBox.warning(self, "Unsupported Format", "Selected file is neither CSV nor BDF.")
        

    def delete_files(self):
        """Removes the selected file from the list and internal storage."""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file from the list to delete.")
            return

        file_display_name = current_item.text()
        
        # confirm before deleting
        reply = QMessageBox.question(self, "Delete File", 
                                    f"Are you sure you want to remove '{file_display_name}' from the list?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # remove from internal storage
            self.file_list.takeItem(self.file_list.row(current_item))
            if file_display_name in self.file_data_store:
                del self.file_data_store[file_display_name]
            if file_display_name in self.file_channels:
                del self.file_channels[file_display_name]
            if file_display_name in self.file_frequency_store:
                del self.file_frequency_store[file_display_name]
            if file_display_name in self.file_format_store:
                del self.file_format_store[file_display_name]

            # clear channel and plotting areas
            self.channel_list.clear()
            self.clear_plot_area()
            QMessageBox.information(self, "File Deleted", f"'{file_display_name}' has been removed.")


    def on_file_clicked(self, item):
        """Getting data from the selected file from the file list."""
        file_display_name = item.text()
        if file_display_name in self.file_data_store:
            self.data = self.file_data_store[file_display_name]
            self.channel_names = self.file_channels[file_display_name]
            self.update_channel_list()
            self.sampling_frequency = self.file_frequency_store.get(file_display_name, None)
        else:
            QMessageBox.warning(self, "File Not Found", f"The file {file_display_name} is not available.")
        self.update_buttons_state()


    def update_channel_list(self):
        """Updates channel list based on the selected file from the file list."""
        self.channel_list.clear()
        self.channel_checkboxes = []  # Reset checkboxes
        for ch in self.channel_names:
            item = QListWidgetItem(ch)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.channel_list.addItem(item)
            self.channel_checkboxes.append(item)


    def get_selected_data(self, file_display_name, selected_channels):
        """Extracts selected EEG data from either a CSV (Pandas DataFrame) or a BDF (MNE Raw Object)."""
        
        if file_display_name not in self.file_data_store:
            QMessageBox.warning(self, "Data Not Found", f"No data found for {file_display_name}.")
            return None, None, None  # Return empty values if file not found

        current_data = self.file_data_store[file_display_name]
        sfreq = self.file_frequency_store.get(file_display_name, None)

        if sfreq is None:
            QMessageBox.warning(self, "No Sampling Frequency", "Sampling frequency not found.")
            return None, None, None

        # CSV Data (Pandas DataFrame)
        if isinstance(current_data, pd.DataFrame):
            if selected_channels and all(ch in current_data.columns for ch in selected_channels):
                selected_data = current_data[selected_channels].to_numpy().T
                timestamps = current_data.iloc[:, 0].to_numpy()
                n = len(timestamps)
            else:
                QMessageBox.warning(self, "Invalid Channels", "Selected channels not found in CSV file.")
                return None, None, None

        # BDF Data (MNE Raw Object)
        elif isinstance(current_data, mne.io.BaseRaw):
            ch_indices = [current_data.ch_names.index(ch) for ch in selected_channels if ch in current_data.ch_names]
            if not ch_indices:
                QMessageBox.warning(self, "Invalid Channels", "Selected channels not found in BDF file.")
                return None, None, None
            selected_data = current_data.get_data(picks=ch_indices)  
            n = selected_data.shape[1]
            timestamps = np.arange(n) / sfreq  # generate timestamps if they are not present

        else:
            QMessageBox.warning(self, "Unsupported File Format", "The selected file format is not supported.")
            return None, None, None

        return selected_data, timestamps, sfreq, n


    def get_selected_channels(self):
        """Returnes the channels selected in the channel list."""
        return [item.text() for item in self.channel_checkboxes if item.checkState() == Qt.Checked] # output in the form ["Ch1", "Ch5"]
    

    def clear_all_channels(self):
        """Clear all selected channels in the channel list."""
        for index in range(self.channel_list.count()):
            item = self.channel_list.item(index)
            item.setCheckState(Qt.Unchecked)


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
        """Plots ExG signals for selected channels vs Time in seconds."""

        current_item = self.file_list.currentItem()
        selected_channels = self.get_selected_channels()
        if len(selected_channels) == 0:
            QMessageBox.warning(self, "No Channels Selected", "Please select one channel for visualization.")
            return
        file_display_name = current_item.text()
        selected_data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        # Create MNE Raw object
        info = mne.create_info(ch_names=selected_channels, sfreq=sfreq, ch_types='eeg')
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
        """Updated Fast-Fourier-Transformation plot for selected channels."""
        selected_channels = self.get_selected_channels()
        if not selected_channels:
            QMessageBox.warning(self, "No Channels Selected", "Please select at least one channel to plot.")
            return
        current_item = self.file_list.currentItem()
        file_display_name = current_item.text()
        selected_data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        self.clear_plot_area()
        freqs = np.fft.rfftfreq(n, d=1/sfreq)

        # FFT canvas
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
        toolbar = NavigationToolbar(fft_canvas, self)
        self.plot_area.addWidget(toolbar)
        self.current_toolbar = toolbar
        self.plot_area.addWidget(fft_canvas)
        self.current_plot_widget = fft_canvas


    def update_bandpower_visualization(self):
        """Updated the plot for Bandpower Visualization for selected channels."""
        selected_channels = self.get_selected_channels()
        current_item = self.file_list.currentItem()
        file_display_name = current_item.text()     
        current_data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        bands = {
            "Delta (0.5-4 Hz)": (0.5, 4),
            "Theta (4-8 Hz)": (4, 8),
            "Alpha (8-13 Hz)": (8, 13),
            "Beta (13-30 Hz)": (13, 30),
            "Gamma (30-50 Hz)": (30, 50),
        }
        self.clear_plot_area()

        # Create container for toolbar, canvas, and slider
        container = QWidget()
        layout = QVBoxLayout(container)

        num_bands = len(bands)
        fig, axes = plt.subplots(num_bands, 1, figsize=(12, num_bands * 3),
                                sharex=True, dpi=100)
        if num_bands == 1:
            axes = [axes]
        fig.subplots_adjust(hspace=0.5)
        time = np.arange(n) / sfreq

        # Trim 0.5 sec from each edge (if possible) to reduce filter transients
        edge_trim = int(0.5 * sfreq)
        if n > 2 * edge_trim:
            time = time[edge_trim:-edge_trim]

        band_signals = []
        for idx, (band_name, (low, high)) in enumerate(bands.items()):
            filtered_channels = []
            for ch in range(len(selected_channels)):
                sig = filter_data(current_data[ch], sfreq=sfreq, l_freq=low, h_freq=high)
                if n > 2 * edge_trim:
                    sig = sig[edge_trim:-edge_trim]
                filtered_channels.append(sig)
            avg_sig = np.mean(filtered_channels, axis=0)
            band_signals.append(avg_sig)
            axes[idx].plot(time, avg_sig, label=band_name,
                        color=plt.cm.viridis(idx / num_bands), alpha=0.8)
            axes[idx].legend(loc='upper right')
            axes[idx].grid(True, linestyle='--', alpha=0.7)
            # axes[idx].set_ylabel("µV")
        axes[-1].set_xlabel("Time (seconds)")
        fig.suptitle("Frequency Bands vs Time", fontsize=16)

        canvas = FigureCanvas(fig)
        canvas.draw()
        toolbar = NavigationToolbar(canvas, self)

        # Create a slider to scroll through time
        window_width = 10  # seconds visible at a time
        total_time = time[-1] - time[0]
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(int(total_time - window_width))
        slider.setValue(0)

        # Store variables as instance attributes for the slider callback method.
        self._axes = axes
        self._time = time
        self._band_signals = band_signals
        self._canvas = canvas
        self._window_width = window_width

        slider.valueChanged.connect(self.update_xlim)

        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        layout.addWidget(slider)
        self.plot_area.addWidget(container)
        self.current_plot_widget = container

        # Initialize x-limits and y-limits based on slider's starting value.
        self.update_xlim(slider.value())

    # Function to make Bandpower VS Time Plot scrollable
    def update_xlim(self, value):
        """Update x-limits and dynamically adjust y-limits based on the visible time window."""
        x_min = value
        x_max = x_min + self._window_width
        for i, ax in enumerate(self._axes):
            ax.set_xlim(x_min, x_max)
            # Find indices in the time array that fall within the visible window.
            indices = (self._time >= x_min) & (self._time <= x_max)
            if np.any(indices):
                y_visible = self._band_signals[i][indices]
                y_min = np.min(y_visible)
                y_max = np.max(y_visible)
                # If the y-range is nearly zero, set a default margin.
                if np.isclose(y_max, y_min):
                    margin = 1 if y_max == 0 else 0.1 * abs(y_max)
                else:
                    margin = 0.1 * (y_max - y_min)
                ax.set_ylim(y_min - margin, y_max + margin)
        self._canvas.draw_idle()

    def update_bandpower_bars_visualization(self):
        """Updated the plot for bandpower visualization in bars for selected channels."""
        current_item = self.file_list.currentItem()
        selected_channels = self.get_selected_channels()
        if len(selected_channels) == 0:
            QMessageBox.warning(self, "No Channels Selected", "Please select one channel for visualization.")
            return
        file_display_name = current_item.text()
        current_data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)
    
        bands = {
            "Delta (0.5-4 Hz)": (0.5, 4),
            "Theta (4-8 Hz)": (4, 8),
            "Alpha (8-13 Hz)": (8, 13),
            "Beta (13-30 Hz)": (13, 30),
            "Gamma (30-50 Hz)": (30, 50),
        }
        bandpower_values = {}
        for band_name, (low, high) in bands.items():
            filtered_data = np.zeros(n)  # an array for averaging
            # sum filtered data across selected channels
            for i, channel in enumerate(selected_channels):
                filtered_signal = filter_data(current_data[i], sfreq=sfreq, l_freq=low, h_freq=high)
                filtered_data += filtered_signal
            # average over selected channels
            filtered_data /= len(selected_channels)
            # compute the band power (RMS of filtered signal)
            bandpower = np.sqrt(np.mean(filtered_data**2))
            bandpower_values[band_name] = bandpower

        self.clear_plot_area()

        fig, ax_abs = plt.subplots(figsize=(10, 5))
        bands_list = list(bandpower_values.keys())
        abs_values = list(bandpower_values.values())
        bars = ax_abs.bar(bands_list, abs_values, alpha=0.7)
        ax_abs.set_ylabel("Absolute Band Power")

        # second y-axis for relative power
        ax_rel = ax_abs.twinx()

        # ?? ensure both y-axes cover the same numeric range
        ax_rel.set_ylim(ax_abs.get_ylim())

        # convert absolute scale to relative by dividing by total_power in the tick labels
        total_power = sum(abs_values)
        def absolute_to_relative_formatter(value, _):
            relative = value / total_power if total_power != 0 else 0
            return f"{relative:.2f}"  

        ax_rel.yaxis.set_major_formatter(FuncFormatter(absolute_to_relative_formatter))
        ax_rel.set_ylabel("Relative Band Power")
        ax_abs.set_title("Band Power Plot: Absolute & Relative")
        ax_abs.set_xticklabels(bands_list, rotation=15)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)

        self.plot_area.addWidget(toolbar)
        self.current_toolbar = toolbar
        self.plot_area.addWidget(canvas)
        self.current_plot_widget = canvas



    def update_psd_visualization(self):
        """Compute and plot the Power Spectral Density (PSD) of selected EEG channels."""
        selected_channels = self.get_selected_channels()
        if len(selected_channels) == 0:
            QMessageBox.warning(self, "No Channels Selected", "Please select one channel for visualization.")
            return

        current_item = self.file_list.currentItem()
        file_display_name = current_item.text()
        selected_data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        psd_values = []
        freqs = None  # to store frequency bins

        # compute PSD for selected channels using Welch's method
        for i, channel in enumerate(selected_channels):
            signal = selected_data[i]  
            f, Pxx = welch(signal, fs=sfreq, nperseg=min(1024, len(signal)))  # Welch's PSD estimation
            psd_values.append(Pxx)

            if freqs is None:
                freqs = f  # Store frequency bins
        # average PSD across selected channels
        avg_psd = np.mean(psd_values, axis=0)

        self.clear_plot_area()
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(freqs, avg_psd, color="blue", lw=1.5)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Power Spectral Density (V²/Hz)")
        ax.set_title("Power Spectral Density (PSD)")
        ax.set_xscale('log')  # Log scale for better visualization
        ax.grid(True)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        self.plot_area.addWidget(toolbar)
        self.current_toolbar = toolbar
        self.plot_area.addWidget(canvas)
        self.current_plot_widget = canvas


    def update_spectogram_visualization(self):
        """Compute and plot a time-frequency representation (spectrogram) of selected EEG channels."""
        selected_channels = self.get_selected_channels()
        if len(selected_channels) == 0:
            QMessageBox.warning(self, "No Channels Selected", "Please select one channel for visualization.")
            return

        current_item = self.file_list.currentItem()
        file_display_name = current_item.text()
        data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        # Compute spectrogram for selected channels and average
        spectrogram_list = []
        for i, channel in enumerate(selected_channels):
            signal = data[i] 
            freqs, times, Sxx = spectrogram(signal, fs=sfreq, nperseg=1024)
            spectrogram_list.append(Sxx)

        avg_spectrogram = np.mean(spectrogram_list, axis=0)

        self.clear_plot_area()
        fig, ax = plt.subplots(figsize=(6, 4))
        pcm = ax.pcolormesh(times, freqs, 10 * np.log10(avg_spectrogram), shading='auto')
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_title("Time-Frequency Spectrogram")
        fig.colorbar(pcm, ax=ax, label="Power/Frequency (dB/Hz)")
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        self.plot_area.addWidget(toolbar)
        self.current_toolbar = toolbar
        self.plot_area.addWidget(canvas)
        self.current_plot_widget = canvas


    def apply_filters(self):
        """Layout for the menu bar button Filter. Calls filter_data function.""" 
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
        """
        Applies MNE filters to the data. 
        Stores the new data to the internal memory and displays
        it in the file list with the name includes the applied filters.
        """
        current_item = self.file_list.currentItem()
        file_display_name = current_item.text()
        selected_channels = self.get_selected_channels()
        data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        name_suffix = "" # addition to the name to show which filters were applied
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

        if isinstance(data, pd.DataFrame):
            filtered_data = pd.DataFrame(data.T, columns=selected_channels)
            filtered_data.insert(0, "Timestamps", data.iloc[:, 0])
        else:
            info = mne.create_info(ch_names=selected_channels, sfreq=sfreq, ch_types='eeg')
            filtered_data = RawArray(data, info)
        
        original_format = self.file_format_store[file_display_name]
        if original_format == 'bdf':
            filtered_file_name = file_display_name.replace('.bdf', f'{name_suffix}.bdf')
        else:
            filtered_file_name = file_display_name.replace('.csv', f'{name_suffix}.csv')

        self.file_data_store[filtered_file_name] = filtered_data
        self.file_format_store[filtered_file_name] = original_format
        self.file_frequency_store[filtered_file_name] = sfreq
        self.file_channels[filtered_file_name] = selected_channels #????????????????????????????????????????????????????
        self.file_list.addItem(filtered_file_name)

        QMessageBox.information(self, "Filter Applied", "Filters applied successfully.")
        dialog.accept()


    def export_file(self):
        """Exports (saves to the computer) files in the specified format."""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No File Selected", "Please select a file to export.")
            return
        selected_channels = self.get_selected_channels()
        if not selected_channels:
            QMessageBox.warning(self, "No Channels Selected", "Please select at least one channel to plot.")
            return
        file_display_name = current_item.text()
        selected_data, timestamps, sfreq, n = self.get_selected_data(file_display_name, selected_channels)

        # Open file dialog to select export location
        options = QFileDialog.Options()
        base_name = os.path.splitext(file_display_name)[0]  
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Filtered Data", 
            base_name,  # Use the cleaned filename without extension
            # "CSV Files (*.csv);;EDF Files (*.edf)",  # File type options
            "CSV Files (*.csv);;BDF Files (*.bdf)",  # File type options
            options=options
        )
        
        if file_name:
            try:
                # For CSV export
                if file_name.endswith('.csv'):
                    # Build a DataFrame from the selected data so the first column is timestamps
                    export_df = pd.DataFrame(selected_data.T, columns=selected_channels)
                    if export_df.columns[0] != 'TimeStamp':
                        export_df.insert(0, 'TimeStamp', timestamps)
                    export_df.to_csv(file_name, index=False)

                elif file_name.endswith('.bdf'):
                    # Build an MNE Raw from the selected data and save as BDF
                    info = mne.create_info(ch_names=selected_channels, sfreq=sfreq, ch_types='eeg')
                    raw_to_save = RawArray(selected_data, info)
                    # file_name = file_name.replace('.bdf', '.edf')
                    print(f"Selected file name: {file_name}")
                    print(f"Type of file_name: {type(file_name)}")
                    # export.export_raw(raw_to_save, file_name, fmt='edf')
                    export.export_raw(file_name, raw_to_save,
                      fmt='eeglab',
                      overwrite=True, physical_range=[-400000, 400000])

                    # raw_to_save.save(file_name, overwrite=True)

                QMessageBox.information(self, "Export Success", f"File '{file_display_name}' has been successfully exported to '{file_name}'.")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"An error occurred while exporting: {e}")
