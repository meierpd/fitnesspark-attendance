from flask import Flask, render_template, request, abort
from google.cloud import storage
import pandas as pd
from datetime import datetime, timedelta
from time import time
import io
import logging
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FitnessparkVisualizer")

# In-memory rate limiter
last_access = {}

# In-memory cache for processed data
cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

BUCKET_NAME = "fitnesspark-attendance-data"
BLOB_PATH = "attendance/attendance_data.jsonl"


@app.before_request
def limit_requests():
    """Simple IP-based rate limiter: allow 1 request every 2 seconds per IP."""
    ip = request.remote_addr
    now = time()
    if ip in last_access and now - last_access[ip] < 2:
        abort(429)  # Too Many Requests
    last_access[ip] = now


def load_data_from_gcs():
    """Load the attendance log file from Cloud Storage into a DataFrame."""
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(BLOB_PATH)

    data_bytes = blob.download_as_bytes()
    df = pd.read_json(io.BytesIO(data_bytes), lines=True)
    df.dropna(subset=["timestamp", "count"], inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize('UTC').dt.floor("10min")
    df.sort_values("timestamp", inplace=True)
    return df


def compute_today_vs_typical(df):
    now = pd.Timestamp.now('UTC')
    df["time"] = df["timestamp"].dt.strftime("%H:%M")
    df["weekday"] = df["timestamp"].dt.strftime("%A")

    today_weekday_name = now.strftime("%A")
    df_today = df[df["weekday"] == today_weekday_name]

    four_weeks_ago = (now - timedelta(weeks=4)).floor("10min")
    df_recent = df[df["timestamp"] >= four_weeks_ago]

    df_avg = df_recent.groupby(["weekday", "time"])["count"].mean().reset_index()

    # Filter for opening hours before converting to dict
    df_today = df_today[(df_today["time"] >= "06:30") & (df_today["time"] <= "22:00")]
    df_avg = df_avg[(df_avg["time"] >= "06:30") & (df_avg["time"] <= "22:00")]

    data_today = df_today[df_today["timestamp"].dt.date == now.date()]
    data_avg = df_avg[df_avg["weekday"] == today_weekday_name]
    
    # Ensure data is sorted by time for correct plotting
    data_today = data_today.sort_values('time')
    data_avg = data_avg.sort_values('time')

    return data_today, data_avg


def compute_weekly_summary(df):
    now = pd.Timestamp.now('UTC')
    four_weeks_ago = (now - timedelta(weeks=4)).floor("10min")
    df = df[df["timestamp"] >= four_weeks_ago].copy()

    df["weekday_name"] = df["timestamp"].dt.strftime("%A")

    # Define time buckets for the weekly summary table
    time_bins_minutes = [
        360, 420, 480, 540, 600, 660, 720, 780, 840, 900, 960, 1020, 1080,
        1140, 1200, 1260, 1320,
    ]  # 06:00 to 22:00
    labels = [
        "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00",
        "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00",
        "20:00", "21:00",
    ]

    time_in_minutes = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df["time_slot"] = pd.cut(
        time_in_minutes, bins=time_bins_minutes, labels=labels, right=False
    )
    df.dropna(subset=["time_slot"], inplace=True)

    pivot = df.groupby(["weekday_name", "time_slot"], observed=False)["count"].mean().reset_index()

    peaks = (
        df.groupby("weekday_name")
        .apply(lambda x: x.loc[x["count"].idxmax()][["timestamp", "count"]], include_groups=False)
        .reset_index()
    )
    peaks.rename(
        columns={"count": "peak_count", "timestamp": "peak_time"}, inplace=True
    )

    return pivot, peaks


def compute_weekly_profiles(df):
    df["weekday"] = df["timestamp"].dt.day_name()
    df["time"] = df["timestamp"].dt.strftime("%H:%M")

    df_weekly = df.groupby(["weekday", "time"])["count"].mean().reset_index()
    df_weekly.rename(columns={"count": "visitors"}, inplace=True)

    # Filter for opening hours
    df_weekly = df_weekly[(df_weekly["time"] >= "06:30") & (df_weekly["time"] <= "22:00")]

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    df_weekly["weekday"] = pd.Categorical(
        df_weekly["weekday"], categories=weekday_order, ordered=True
    )
    df_weekly = df_weekly.sort_values(["weekday", "time"])

    return df_weekly

def create_today_vs_typical_chart(today_data, avg_data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=today_data['time'], y=today_data['count'], mode='lines+markers', name='Today'))
    fig.add_trace(go.Scatter(x=avg_data['time'], y=avg_data['count'], mode='lines', name='Typical'))
    fig.update_layout(title_text="Today vs. Typical Attendance", template="plotly_white")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_weekly_pattern_chart(weekly_profiles):
    fig = px.line(weekly_profiles, x="time", y="visitors", color='weekday', title="Weekly Attendance Patterns")
    fig.update_layout(template="plotly_white")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_summary_table(summary, peaks):
    summary_pivot = summary.pivot(index='weekday_name', columns='time_slot', values='count').round(0).fillna(0).astype(int)
    summary_pivot = summary_pivot.reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    
    peaks['peak_time_str'] = peaks['peak_time'].dt.strftime('%H:%M')
    
    summary_pivot.reset_index(inplace=True)
    summary_pivot = summary_pivot.merge(peaks[['weekday_name', 'peak_count', 'peak_time_str']], on='weekday_name', how='left')
    summary_pivot.set_index('weekday_name', inplace=True)
    summary_pivot.rename(columns={'peak_count': 'Peak', 'peak_time_str': 'Peak Time'}, inplace=True)

    header_values = ['Day'] + list(summary_pivot.columns)
    cell_values = [summary_pivot.index] + [summary_pivot[col] for col in summary_pivot.columns]

    fig = go.Figure(data=[go.Table(
        header=dict(values=header_values, fill_color='paleturquoise', align='left'),
        cells=dict(values=cell_values, fill_color='lavender', align='left'))
    ])
    fig.update_layout(title_text="Weekly Summary and Peak Times")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_all_time_chart(df):
    fig = px.line(df, x='timestamp', y='count', title='All-Time Attendance')
    fig.update_layout(template="plotly_white")
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@app.route("/")
def index():
    try:
        now = time()
        # Check if cache is valid
        if "data" in cache and now - cache.get("timestamp", 0) < CACHE_TTL_SECONDS:
            logger.info("Serving from cache.")
            cached_data = cache["data"]
        else:
            logger.info("Cache miss or expired. Reloading data from GCS.")
            df = load_data_from_gcs()

            today_data, avg_data = compute_today_vs_typical(df.copy())
            summary, peaks = compute_weekly_summary(df.copy())
            weekly_profiles = compute_weekly_profiles(df.copy())

            chart1_json = create_today_vs_typical_chart(today_data, avg_data)
            chart2_json = create_weekly_pattern_chart(weekly_profiles)
            table_json = create_summary_table(summary, peaks)
            chart3_json = create_all_time_chart(df.copy())

            cached_data = {
                "chart1_json": chart1_json,
                "chart2_json": chart2_json,
                "table_json": table_json,
                "chart3_json": chart3_json,
            }
            # Update cache
            cache["data"] = cached_data
            cache["timestamp"] = now

    except Exception as e:
        logger.error(f"Failed to load data: {e}", exc_info=True)
        return "Error loading data", 500

    return render_template("index.html", **cached_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
