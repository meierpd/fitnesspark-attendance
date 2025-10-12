# 📊 Fitnesspark Visualizer

A lightweight Flask web application that displays live and historical gym attendance data collected by the **fitnesspark-attendance** project.

The app reads attendance logs from **Google Cloud Storage**, plots them as a simple time series chart using **Chart.js**, and serves the dashboard through **Google Cloud Run**.

---

## 🧭 Overview

### Architecture

```
Cloud Storage → Flask app → Cloud Run (public URL)
```

### Data Source

The app expects a file in Cloud Storage:

```
gs://fitnesspark-attendance-data/attendance/attendance_data.jsonl
```

Each line represents a record:

```json
{"timestamp": "2025-10-12T20:28:51.661552", "count": 64, "status": "ok"}
```

---

## ⚙️ Local Development

### 1. Set up Python environment

```bash
cd visualizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run locally

Make sure you are authenticated with Google Cloud:

```bash
gcloud auth application-default login
python app.py
```

Then open [http://localhost:8080](http://localhost:8080).

---

## 🚀 Deployment to Google Cloud Run

### 1. Set environment variables

```bash
export PROJECT_ID=fitnesspark-attendance
export REGION=europe-west6
export IMAGE="europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/visualizer:latest"
```

### 2. Build and push the image

```bash
cd visualizer
gcloud builds submit --tag $IMAGE
```

### 3. Deploy to Cloud Run

```bash
gcloud run deploy fitnesspark-visualizer \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1
```

When deployment completes, you’ll see:

```
Service URL: https://fitnesspark-visualizer-xxxxxx-ew.a.run.app
```

That’s your live public dashboard 🌍

---

## 🧰 Maintenance & Troubleshooting

### Check logs

```bash
gcloud logs read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="fitnesspark-visualizer"' \
  --limit 50 --format="value(textPayload)"
```

### Update after code changes

```bash
gcloud builds submit --tag $IMAGE
gcloud run deploy fitnesspark-visualizer --image $IMAGE --region $REGION
```

### Delete old revisions

(Optional, to clean up resources)

```bash
gcloud run revisions list --region $REGION
gcloud run revisions delete REVISION_NAME --region $REGION
```

---

## 🔒 Optional: Make It Private

If you want only authorized users to access it, remove `--allow-unauthenticated` from the deploy command and grant viewer roles to specific Google accounts:

```bash
gcloud run services add-iam-policy-binding fitnesspark-visualizer \
  --member="user:youremail@gmail.com" \
  --role="roles/run.invoker" \
  --region $REGION
```

Then users must log in with their Google account to access the dashboard.

---

## ✅ Summary

* **Purpose:** visualize historical gym attendance data from Cloud Storage
* **Technology:** Flask + Chart.js + Cloud Run
* **Access:** public or private, your choice
* **Maintenance:** redeploy with `gcloud builds submit` + `gcloud run deploy`

---

💡 *Tip:* You can extend this dashboard with more charts, filters, or even average attendance per weekday for richer insights.
