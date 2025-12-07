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


# ---------- Sidebar filters ----------

st.sidebar.header("Filters")

# Metric filter
metric_options = sorted(df["metric_type"].unique())
default_metric = [m for m in metric_options if m != "fault"] or metric_options

selected_metrics = st.sidebar.multiselect(
    "Metric type(s)",
    options=metric_options,
    default=default_metric,
)

# Device filter
device_options = sorted(df["device_id"].unique())
selected_devices = st.sidebar.multiselect(
    "Device(s)",
    options=device_options,
    default=device_options,
)

# Time range filter (works for datetime or integer)
min_ts = df["timestamp_utc"].min()
max_ts = df["timestamp_utc"].max()
start_ts, end_ts = st.sidebar.slider(
    "Time range",
    min_value=min_ts,
    max_value=max_ts,
    value=(min_ts, max_ts),
)

# Apply filters
mask = (
    df["metric_type"].isin(selected_metrics)
    & df["device_id"].isin(selected_devices)
    & (df["timestamp_utc"] >= start_ts)
    & (df["timestamp_utc"] <= end_ts)
)
df_filtered = df[mask].copy()


# ---------- Overview header ----------

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


# ---------- Time-series plot ----------

st.subheader("Time series (scaled value)")

if df_filtered.empty:
    st.warning("No data for the current filters.")
else:
    metric_for_line = st.selectbox(
        "Metric for time series",
        options=sorted(df_filtered["metric_type"].unique()),
    )

    df_line = df_filtered[df_filtered["metric_type"] == metric_for_line].sort_values(
        "timestamp_utc"
    )

    if not df_line.empty:
        # Only set index if it's not already using timestamp_utc
        if df_line.index.name != "timestamp_utc" and "timestamp_utc" in df_line.columns:
            df_line = df_line.set_index("timestamp_utc")

        st.line_chart(df_line["scaled_value"])
    else:
        st.info("No rows for the selected metric.")


# ---------- Distribution / histogram ----------

st.subheader("Distribution of scaled values")

if not df_filtered.empty:
    fig, ax = plt.subplots()
    df_filtered["scaled_value"].plot(kind="hist", bins=30, ax=ax)
    ax.set_xlabel("Scaled value (0–100)")
    ax.set_ylabel("Count")
    st.pyplot(fig)
else:
    st.info("No data to show histogram.")


# ---------- Outlier rate by metric ----------

st.subheader("Outlier rate by metric_type")

outlier_mask = df["outlier_type"] != "none"
metric_summary = (
    df.assign(is_outlier=outlier_mask)
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
