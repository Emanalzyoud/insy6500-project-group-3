# INSY 6500 Final Project – AU Greenhouse Sensor Data EDA Project

This repo contains the final project for INSY-6500 course for Group 3

The goal is to apply the full EDA workflow to a real-world dataset
and build a Streamlit app to explore it interactively.

---

## Dataset
- **Source:** Urban.io dashboard export for the AU Greenhouse  

The data comes from a greenhouse monitoring system. Each row is one sensor reading
at a point in time. The sensors report:

- **current** – electrical current drawn by the device  
- **fault** – 0/1 flag for whether the device is in a fault state  
- **sensor_battery_level** – battery charge level (%)  
- **sensor_signal_strength** – radio signal strength (%)

There are 5,960 rows and ~20 columns after cleaning, so it is non-trivial but still
manageable for EDA.

---

## Questions

I focused on a few main questions:

1. **How healthy is the greenhouse system overall?**  
   - Are current, battery level, and signal strength generally in safe ranges?

2. **How do these metrics behave over time?**  
   - Are there long periods of low battery or poor signal?  
   - Are readings regular, or are there gaps?

3. **Where do anomalies (outliers) occur?**  
   - Which metric produces the most unusual values?  
   - Are anomalies concentrated at specific times?

4. **Can we engineer simple features that make the behavior easier to explain?**  
   - For example: battery health categories, signal quality bins, change-size bins.

These questions guided the whole EDA process and the design of the dashboard.

---

## EDA Workflow 

The notebook `project/insy6500_final_greenhouse.ipynb` follows the six EDA phases.

### 1. Load & Initial Reconnaissance

- Loaded `data/greenhouse_merged_top_fields.csv` with pandas.  
- Inspected shape (`5960 × 20`), column types, and a few sample rows.  
- Identified the four `metric_type` values: `current`, `fault`, `sensor_battery_level`,
  and `sensor_signal_strength`.

### 2. Data Quality Assessment

- Checked missing values: no serious NA problems; `ref_unit` has a few missing values.  
- Looked for duplicates: none found.  
- Validated numeric ranges on the raw columns:
  - `v` and `scaled_v` are always between 0 and 100.  
  - `fault` is always 0 or 1.  
  - Battery and signal values are within [0, 100]%.  
  - Current is non-negative and not extreme.  
- Examined change variables (`dv`, `dv_per_s`) and time spacing (`dts`) to see that
  most steps have zero change, with occasional large jumps and 5–20 minute intervals.

Overall, the raw data was already quite clean; we did not need heavy “repair” work.

### 3. Cleaning Decisions

- Worked on a copy of the data (`df = df_raw.copy()`).
- Renamed columns to be more descriptive, e.g.:
  - `ts_utc` → `timestamp_utc`,  
  - `dt` → `metric_type`,  
  - `v` → `value`,  
  - `scaled_v` → `scaled_value`,  
  - `dv` → `delta_value`,  
  - `dts` → `delta_ts_ms`,  
  - `ref_d` → `device_id`, etc.
- Converted `timestamp_utc` to a proper datetime and cast several columns to `category`.
- Standardized units into a single `unit` column (battery and signal as `%`).
- After these changes, the dataset was easier to read and ready for analysis.

### 4. Statistical EDA

Univariate and bivariate exploration included:

- **Sensor levels over time**:  
  - Current is stable and low.  
  - Fault is always 0 (no recorded faults).  
  - Battery level is mostly high or full.  
  - Signal strength is usually strong but more variable than battery.
- **Distributions** of the scaled metrics show that most readings are near the top
  of the 0–100 scale.
- **Change variables** (`delta_value`, `delta_per_second`) show that most steps
  have no change, with a few large jumps up or down.
- **Per-device counts** confirm that each device logs a similar number of readings.

This phase builds intuition that the system is normally healthy and stable.

### 5. Transformation & Feature Engineering

Several new features were created to make the behavior easier to interpret:

- **Time features**  
  - `elapsed_hours`: hours since the start of the run.  
  - `time_bin_2h`: 2-hour bins (0–2, 2–4, …, 12–14 hours).

- **Level categories**  
  - `battery_bin` for battery readings (`low`, `medium`, `high`, `full`).  
  - `signal_bin` for signal strength (`weak`, `medium`, `strong`) based on quantiles.  
  - `change_bin` for change size in `delta_value` (`small`, `medium`, `large`).

- **Outlier flags**  
  - `delta_value_outlier` for the largest 1% of absolute changes.  
  - `delta_per_second_outlier` for large rates of change on “stationary” metrics.  
  - `outlier_type` combines these into `none`, `delta_value`, `delta_per_second`,
    or `both`.

Key findings:

- Only about **0.9%** of all rows are flagged as any kind of outlier.  
- All outliers come from the **`sensor_signal_strength`** metric  
  (~3.7% of its readings).  
- `current`, `fault`, and `sensor_battery_level` have essentially zero flagged
  outliers.  
- Outliers are spread through the 14-hour window rather than confined to one
  short interval.

### 6. Save & Document

- The final cleaned and enriched dataframe (`df_ts`) is saved to  
  `data/greenhouse_timeseries_processed.pkl`.
- This file is used by the Streamlit app so that the dashboard always works with
  the same processed data.
- The notebook mixes narrative text, code, and plots to document each step and
  the reasoning behind it.

---

## Streamlit Dashboard

Alongside the notebook analysis, we built an interactive dashboard using Streamlit
(`streamlit_app.py`). The dashboard lets us explore the cleaned greenhouse sensor
data by metric, device, and time range, and visualize time series, distributions,
and outlier rates.  

To run the app locally

```bash
cd ~/insy6500/project-group3
conda activate insy6500
cd project
streamlit run streamlit_app.py
