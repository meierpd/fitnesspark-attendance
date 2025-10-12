from flask import Flask, render_template, jsonify
from google.cloud import storage
import pandas as pd
import io
from datetime import datetime, timedelta

app = Flask(__name__)

BUCKET_NAME = "fitnesspark-attendance-data"
FILE_PATH = "attendance/attendance_data.jsonl"


def load_data():
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(FILE_PATH)
    data = blob.download_as_text()

    df = pd.read_json(io.StringIO(data), lines=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["weekday"] = df["timestamp"].dt.weekday
    df["time"] = df["timestamp"].dt.strftime("%H:%M")
    return df


def compute_today_vs_average(df):
    now = datetime.now()
    today_date = now.date()
    today_weekday = now.weekday()

    # Filter for same weekday in the last 4 weeks
    four_weeks_ago = now - timedelta(weeks=4)
    df_period = df[
        (df["timestamp"] >= four_weeks_ago) & (df["weekday"] == today_weekday)
    ]

    # Compute average per time slot
    df_avg = df_period.groupby("time")["count"].mean().reset_index()

    # Get today's data
    df_today = df[df["timestamp"].dt.date == today_date].copy()
    df_today = df_today[["time", "count"]]

    return df_today, df_avg


def compute_weekly_summary(df):
    now = datetime.now()
    four_weeks_ago = now - timedelta(weeks=4)
    df = df[df["timestamp"] >= four_weeks_ago].copy()

    # Round timestamps to nearest 30 min
    df["time_slot"] = df["timestamp"].dt.floor("30min").dt.strftime("%H:%M")
    df["weekday_name"] = df["timestamp"].dt.strftime("%A")

    # Compute average per weekday & time slot
    pivot = df.groupby(["weekday_name", "time_slot"])["count"].mean().reset_index()

    # Compute peak per weekday
    peaks = (
        df.groupby("weekday_name")
        .apply(lambda x: x.loc[x["count"].idxmax()][["timestamp", "count"]])
        .reset_index()
    )
    peaks.rename(
        columns={"count": "peak_count", "timestamp": "peak_time"}, inplace=True
    )

    return pivot, peaks


@app.route("/")
def index():
    df = load_data()
    df_today, df_avg = compute_today_vs_average(df)

    data_today = df_today.to_dict(orient="records")
    data_avg = df_avg.to_dict(orient="records")
    data_history = df[["timestamp", "count"]].to_dict(orient="records")

    df_summary, df_peaks = compute_weekly_summary(df)
    summary = df_summary.to_dict(orient="records")
    peaks = df_peaks.to_dict(orient="records")

    return render_template(
        "index.html",
        today=data_today,
        average=data_avg,
        history=data_history,
        summary=summary,
        peaks=peaks,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
