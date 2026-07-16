# Electrochemical Impedance Spectroscopy (EIS) Analyzer ⚡

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://eis-pv-analyzer.streamlit.app/)


<img width="1827" height="922" alt="image" src="https://github.com/user-attachments/assets/2e5822a9-0a12-4ecb-bf4c-653fd99d7332" />


## 📌 Overview
Electrochemical Impedance Spectroscopy (EIS) is a critical, yet data-intensive, technique for characterizing charge transfer and transport phenomena in photovoltaic devices. This Streamlit application provides a robust interface for processing raw EIS datasets, automatically generating standardized Nyquist and Bode plots, and estimating key equivalent circuit parameters without the need for manual, repetitive plotting.

## 🔬 Scientific Features
* **Rigorous Nyquist Plotting:** Automatically forces a strictly 1:1 aspect ratio on the Nyquist diagram ($-Z''$ vs. $Z'$). This mathematical constraint is essential for accurately diagnosing depressed semicircles and Constant Phase Elements (CPE) associated with electrode roughness and inhomogeneities.
* **Electrochemical Parameter Estimation:** Parses the impedance spectra to instantly estimate the Series Resistance ($R_s$), Total Resistance ($R_{total}$), and Charge Transfer Resistance ($R_{ct}$), alongside the characteristic frequency peak and maximum phase angle.
* **Dual-Axis Bode Diagrams:** Generates interactive Bode plots (Phase vs. log(Frequency)) for rapid frequency response analysis.
* **Advanced Data Export:** Compiles aggregated statistics and raw datasets into a single `.xlsx` report. Consistent with this tool suite, it injects natively editable Excel scatter charts (via `xlsxwriter`), ensuring that Nyquist plots retain their strict geometric proportions upon export.

## 🛠️ Tech Stack
* **Language:** Python 3.13
* **Framework:** Streamlit
* **Data Processing:** Pandas, NumPy
* **Visualization:** Plotly (Subplots & Interactive Web), XlsxWriter (Native Excel Charts)

## 🚀 Usage
Upload `.txt` or `.csv` EIS measurement files (semicolon `;` delimited). Ensure the data structure contains Frequency, $Z'$, $-Z''$, and Phase columns. Use the sidebar to toggle auto-scaling or manually define the Nyquist boundaries. The app will immediately render the interactive charts and provide the downloadable `.xlsx` report.
