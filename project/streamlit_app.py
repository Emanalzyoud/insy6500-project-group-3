import streamlit as st
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


# ---------- Data loading and column fixing ----------

@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Load the processed greenhouse file and make sure it has the columns
    that the app expects, even if the pickle still uses the original names.
    """
    data_path = Path(__file__).parent.parent / "data" / "greenhouse_timeseries_processed.pkl"
    df = pd.read_pickle(data_path)

    # Make sure index is plain, so timestamp_utc is ONLY a column
    df = df.reset_index(drop=True)
    df.index.name = None

    # 1) timestamp_utc  -----------------------------------------
    if "timestamp_utc" not in df.columns:
        if "ts_utc_parsed" in df.columns:
            df["timestamp_utc"] = pd.to_datetime(df["ts_utc_parsed"])
        elif "ts_utc" in df.columns:
            df["timestamp_utc"] = pd.to_datetime(df["ts_utc"])
        else:
            # Fallback: simple numeric index as "time"
            df["timestamp_utc"] = pd.RangeIndex(len(df))
    else:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="ignore")

    # 2) metric_type  -------------------------------------------
    if "metric_type" not in df.columns and "dt" in df.columns:
        df["metric_type"] = df["dt"]

    # 3) device_id  ---------------------------------------------
    if "device_id" not in df.columns and "ref_d" in df.columns:
        df["device_id"] = df["ref_d"]

    # 4) scaled_value  ------------------------------------------
    if "scaled_value" not in df.columns:
        if "scaled_v" in df.columns:
            df["scaled_value"] = df["scaled_v"]
        elif "v" in df.columns:
            df["scaled_value"] = df["v"]

    # 5) outlier_type – if not present, assume none -------------
    if "outlier_type" not in df.columns:
        df["outlier_type"] = "none"

    return df


# Load once at the top level so the rest of the app can use it
df = load_data()


# =====================================================
# Sidebar filters (single clean version, with keys)
# =====================================================
st.sidebar.header("Filters")

# start from full dataframe
df_filtered = df.copy()

# --- Metric filter ---
metric_options = sorted(df_filtered["metric_type"].dropna().unique())
selected_metrics = st.sidebar.multiselect(
    "Metric type(s)",
    options=metric_options,
    default=metric_options,
    key="metric_filter",
)
df_filtered = df_filtered[df_filtered["metric_type"].isin(selected_metrics)]

# --- Device filter ---
device_options = sorted(df_filtered["device_id"].dropna().unique())
selected_devices = st.sidebar.multiselect(
    "Device(s)",
    options=device_options,
    default=device_options,
    key="device_filter",
)
df_filtered = df_filtered[df_filtered["device_id"].isin(selected_devices)]

# --- Time range slider based on row index ---
df_filtered = df_filtered.sort_values("timestamp_utc").reset_index(drop=True)
n_rows = len(df_filtered)

if n_rows <= 1:
    st.warning("No data available for the selected filters.")
    st.stop()

start_idx, end_idx = st.sidebar.slider(
    "Time range (row index)",
    min_value=0,
    max_value=n_rows - 1,
    value=(0, n_rows - 1),
    key="time_range_slider",
)

df_filtered = df_filtered.iloc[start_idx : end_idx + 1]


# =====================================================
# Overview header
# =====================================================

st.title("Greenhouse Sensor EDA Dashboard")

st.markdown(
    """
This dashboard explores a greenhouse monitoring dataset with four metrics:
**current**, **fault**, **sensor_battery_level**, and **sensor_signal_strength**.

Use the filters in the sidebar to focus on specific metrics, devices, or time windows.
"""
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Readings (filtered)", f"{len(df_filtered):,}")
with col2:
    st.metric("Devices", f"{df_filtered['device_id'].nunique()}")
with col3:
    outlier_rate = (df_filtered["outlier_type"] != "none").mean()
    st.metric("Outlier rate", f"{100 * outlier_rate:.2f} %")


# =====================================================
# Time-series plot
# =====================================================

st.subheader("Time series (scaled value)")

if df_filtered.empty:
    st.warning("No data for the current filters.")
else:
    metric_for_line = st.selectbox(
        "Metric for time series",
        options=sorted(df_filtered["metric_type"].unique()),
    )

    df_line = df_filtered[df_filtered["metric_type"] == metric_for_line].copy()
    df_line = df_line.sort_values("timestamp_utc")

    if not df_line.empty:
        if "timestamp_utc" in df_line.columns:
            df_line = df_line.set_index("timestamp_utc")
        st.line_chart(df_line["scaled_value"])
    else:
        st.info("No rows for the selected metric.")


# =====================================================
# Distribution / histogram
# =====================================================

st.subheader("Distribution of scaled values")

if not df_filtered.empty:
    fig, ax = plt.subplots()
    df_filtered["scaled_value"].plot(kind="hist", bins=30, ax=ax)
    ax.set_xlabel("Scaled value (0–100)")
    ax.set_ylabel("Count")
    st.pyplot(fig)
else:
    st.info("No data to show histogram.")


# =====================================================
# Outlier rate by metric
# =====================================================

st.subheader("Outlier rate by metric_type")

if not df_filtered.empty:
    outlier_mask = df_filtered["outlier_type"] != "none"
    metric_summary = (
        df_filtered.assign(is_outlier=outlier_mask)
        .groupby("metric_type", observed=False)
        .agg(
            n_readings=("is_outlier", "size"),
            n_outliers=("is_outlier", "sum"),
        )
    )
    metric_summary["outlier_rate"] = (
        metric_summary["n_outliers"] / metric_summary["n_readings"]
    )

    st.dataframe(metric_summary)
    st.bar_chart(metric_summary["outlier_rate"])
else:
    st.info("No data to summarize outliers.")
