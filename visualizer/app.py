from flask import Flask, render_template, request, abort
from google.cloud import storage
import pandas as pd
from datetime import datetime, timedelta
from time import time
import io
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FitnessparkVisualizer")

# In-memory rate limiter
last_access = {}

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
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)
    return df


def compute_today_vs_typical(df):
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["time"] = df["timestamp"].dt.floor("10T").dt.strftime("%H:%M")
    df["weekday"] = df["timestamp"].dt.strftime("%A")

    today = datetime.now().strftime("%A")
    df_today = df[df["weekday"] == today]

    four_weeks_ago = datetime.now() - timedelta(weeks=4)
    df_recent = df[df["timestamp"] >= four_weeks_ago]

    df_avg = df_recent.groupby(["weekday", "time"])["count"].mean().reset_index()

    data_today = df_today[df_today["timestamp"].dt.date == datetime.now().date()][
        ["time", "count"]
    ].to_dict(orient="records")
    data_avg = df_avg[df_avg["weekday"] == today][["time", "count"]].to_dict(
        orient="records"
    )
    return data_today, data_avg


def compute_weekly_summary(df):
    now = datetime.now()
    four_weeks_ago = now - timedelta(weeks=4)
    df = df[df["timestamp"] >= four_weeks_ago].copy()

    df["time_slot"] = df["timestamp"].dt.floor("30T").dt.strftime("%H:%M")
    df["weekday_name"] = df["timestamp"].dt.strftime("%A")

    pivot = df.groupby(["weekday_name", "time_slot"])["count"].mean().reset_index()

    peaks = (
        df.groupby("weekday_name")
        .apply(lambda x: x.loc[x["count"].idxmax()][["timestamp", "count"]])
        .reset_index()
    )
    peaks.rename(
        columns={"count": "peak_count", "timestamp": "peak_time"}, inplace=True
    )

    return pivot, peaks


def compute_weekly_profiles(df):
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["weekday"] = df["timestamp"].dt.day_name()
    df["time"] = df["timestamp"].dt.floor("10T").dt.strftime("%H:%M")

    df_weekly = df.groupby(["weekday", "time"])["count"].mean().reset_index()

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


@app.route("/")
def index():
    try:
        df = load_data_from_gcs()
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return "Error loading data", 500

    data_today, data_avg = compute_today_vs_typical(df)
    df_summary, df_peaks = compute_weekly_summary(df)
    df_profiles = compute_weekly_profiles(df)

    return render_template(
        "index.html",
        today=data_today,
        average=data_avg,
        history=df.to_dict(orient="records"),
        summary=df_summary.to_dict(orient="records"),
        peaks=df_peaks.to_dict(orient="records"),
        weekly_profiles=df_profiles.to_dict(orient="records"),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
