from flask import Flask, render_template_string
from google.cloud import storage
import pandas as pd
import io

app = Flask(__name__)

BUCKET_NAME = "fitnesspark-attendance-data"
BLOB_PATH = "attendance/attendance_data.jsonl"

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Fitnesspark Attendance</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body style="font-family: sans-serif; max-width: 800px; margin: auto;">
  <h1>🏋️‍♂️ Fitnesspark Attendance</h1>
  <p>Last updated: {{ last_timestamp }}</p>
  <canvas id="chart" width="800" height="400"></canvas>
  <script>
    const ctx = document.getElementById('chart').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: {{ timestamps | safe }},
        datasets: [{
          label: 'Visitor count',
          data: {{ counts | safe }},
          borderColor: 'blue',
          fill: false
        }]
      },
      options: { scales: { x: { title: { display: true, text: 'Time' } },
                           y: { title: { display: true, text: 'Visitors' } } } }
    });
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(BLOB_PATH)
        data = blob.download_as_text()
        df = pd.read_json(io.StringIO(data), lines=True)
        df = df.sort_values("timestamp")
        timestamps = df["timestamp"].astype(str).tolist()
        counts = df["count"].tolist()
        last_timestamp = df["timestamp"].iloc[-1]
        return render_template_string(TEMPLATE,
                                      timestamps=timestamps,
                                      counts=counts,
                                      last_timestamp=last_timestamp)
    except Exception as e:
        return f"<h1>Error loading data:</h1><pre>{e}</pre>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)