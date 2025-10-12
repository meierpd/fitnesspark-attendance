📊 Fitnesspark Visualizer

A lightweight Flask web application that displays live and historical gym attendance data collected by the fitnesspark-attendance project.

The app reads attendance logs from Google Cloud Storage, computes trends using pandas, and visualizes them through Chart.js in a responsive dashboard served by Google Cloud Run.

⸻

🧭 Overview

Architecture

Cloud Storage → Flask → Chart.js → Cloud Run (public URL)

Features
	•	Today vs Typical Chart — compares current day’s attendance to the average of the same weekday over the last 4 weeks.
	•	All-Time Chart — shows total attendance history over time.
	•	Live updates — the dashboard always shows the latest data when refreshed.
	•	Optional auto-refresh — can refresh automatically every 10 minutes for convenience.

Data Source

The app expects a file in Cloud Storage:

gs://fitnesspark-attendance-data/attendance/attendance_data.jsonl

Each line represents a record:

{"timestamp": "2025-10-12T20:28:51.661552", "count": 64, "status": "ok"}


⸻

⚙️ Local Development

1. Set up Python environment

cd visualizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

2. Run locally

Make sure you are authenticated with Google Cloud:

gcloud auth application-default login
python app.py

Then open http://localhost:8080 to view the dashboard.

⸻

🚀 Deployment to Google Cloud Run

1. Set environment variables

export PROJECT_ID=fitnesspark-attendance
export REGION=europe-west6
export IMAGE="europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/visualizer:latest"

2. Build and push the image

cd visualizer
gcloud builds submit --tag $IMAGE

3. Deploy to Cloud Run

gcloud run deploy fitnesspark-visualizer \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1

After deployment, you’ll see:

Service URL: https://fitnesspark-visualizer-xxxxxx-ew.a.run.app

That’s your live dashboard 🌍

Redeploying the same service keeps the same URL — only a new revision is created.

⸻

🧰 Maintenance & Troubleshooting

View logs

gcloud logs read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="fitnesspark-visualizer"' \
  --limit 50 --format="value(textPayload)"

Update after code changes

gcloud builds submit --tag $IMAGE
gcloud run deploy fitnesspark-visualizer --image $IMAGE --region $REGION

Delete old revisions

(Optional, to free resources)

gcloud run revisions list --region $REGION
gcloud run revisions delete REVISION_NAME --region $REGION


⸻

🔄 Data Refresh Behavior
	•	The dashboard always shows the newest data from Cloud Storage when reloaded.
	•	Since the scraper runs every 10 minutes, simply refreshing the page fetches new attendance data.
	•	(Optional) You can make it auto-refresh by adding this line to the <head> of index.html:

<meta http-equiv="refresh" content="600">

This reloads the page every 10 minutes automatically.

⸻

🔒 Optional: Make It Private

If you prefer to restrict access, remove --allow-unauthenticated from the deploy command and grant access only to specific Google accounts:

gcloud run services add-iam-policy-binding fitnesspark-visualizer \
  --member="user:youremail@gmail.com" \
  --role="roles/run.invoker" \
  --region $REGION


⸻

✅ Summary
	•	Main Chart: Today vs Typical (same weekday, 4-week average)
	•	Secondary Chart: All-Time Attendance
	•	Automatic Updates: Refresh manually or every 10 minutes
	•	Tech Stack: Flask + pandas + Chart.js + Cloud Run
	•	Data Source: Cloud Storage JSONL file

⸻

💡 Future idea: Add color-coded indicators like “Busier than usual” or “Quieter than usual” for instant visual context.