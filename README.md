## Offline ExG Data Analysis and Visualization Tool | Mentalab 

## Overview
This is a graphical tool for EEG data visualization and analysis. It supports importing EEG data from CSV and BDF files, applying filters, visualizing data in time and frequency domains, and exporting processed data.

## Key Features
- Load EEG data from CSV and BDF files
- Apply common EEG filters (high-pass, low-pass, notch, re-referencing, DC offset correction)
- Time-domain plotting 
- Fast Fourier Transform (FFT) Plot
- Bandpower visualization (time and bar plots)
- Power Spectral Density (PSD) calculation
- Spectrogram plotting (time-frequency visualization)
- Convert data between CSV and BDF formats
- Multi-file management within the session
- Export processed files (CSV or BDF) or plots

## Installation
### Prerequisites
- Python 3.8+
- Required libraries:
    ```bash
    pip install numpy pandas mne matplotlib scipy pyqt5
    ```
### Running the Application
```bash
python main_window.py
```

## Usage
1. Open the application.
2. Use the File menu to load EEG files (CSV/BDF).
3. Select desired channels.
4. Apply filters, plot data (time, frequency, power), or export files as needed.
