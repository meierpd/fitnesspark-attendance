# 🏠 Fitnesspark Attendance Visualizer

This visualizer is a Flask-based dashboard that reads gym attendance data from **Google Cloud Storage**, processes it in real time, and displays it interactively using **Plotly**.

It provides:

* 🔢 **Today vs Typical (Same Weekday)** comparison chart (focused on open hours 06:30–22:00)
* 📈 **Weekly Attendance Patterns** — multi-line chart showing each weekday’s average attendance profile over time (last 4 weeks)
* 🗒️ **Weekly Summary Table (Last 4 Weeks)** including average visitors per hour and daily peak counts
* ⛔ **Built-in rate limiter** to protect against excessive refreshes or abuse

---

## ⚙️ Project Structure

```
visualizer/
├── app.py                  # Flask app with charts, data loading, and rate limiting
├── requirements.txt        # Dependencies
├── Dockerfile              # Container definition
└── templates/
    └── index.html          # HTML + Plotly dashboard (includes 2 charts + table)
```

---

## 🛠️ Local Development

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run locally

```bash
python app.py
```

Then open [http://localhost:8080](http://localhost:8080) to view the dashboard.

> Note: The app connects to your Google Cloud project automatically if you’re authenticated with `gcloud auth application-default login`.

---

## 🚀 Deployment to Cloud Run

### 1. Build the image

```bash
export PROJECT_ID=fitnesspark-attendance
export IMAGE="europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/visualizer:latest"
gcloud config set project fitnesspark-attendance

gcloud builds submit --tag $IMAGE
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy fitnesspark-visualizer \
  --image $IMAGE \
  --region europe-west6 \
  --allow-unauthenticated
```

Once deployed, you’ll see a public URL like:

```
https://fitnesspark-visualizer-xxxxxx-ew.a.run.app
```

Visit that link to access your dashboard.

---

## 🔐 Security and Cost Control

### Built-in Rate Limiter

The app uses a simple in-memory rate limiter:

```python
@app.before_request
def limit_requests():
    ip = request.remote_addr
    now = time()
    if ip in last_access and now - last_access[ip] < 2:
        abort(429)
    last_access[ip] = now
```

This prevents refresh spam by limiting requests to **one every 2 seconds per IP**.

### Optional: Restrict Access

You can make the dashboard private:

```bash
gcloud run services update fitnesspark-visualizer --no-allow-unauthenticated
```

Then grant yourself access:

```bash
gcloud run services add-iam-policy-binding fitnesspark-visualizer \
  --member="user:pascal.d.meier@gmail.com" \
  --role="roles/run.invoker" \
  --region europe-west6
```

### Cost Notes

Cloud Run and Cloud Storage have generous free tiers. Occasional refreshes or normal use will **stay well within free limits**.

---

## 🔁 Redeploy After Code Changes

Whenever you modify the dashboard (Python, HTML, or data logic):

### Step 1 — Rebuild the container image

```bash
cd ~/src/fitnesspark-attendance/visualizer
export PROJECT_ID=fitnesspark-attendance
export IMAGE="europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/visualizer:latest"

gcloud builds submit --tag $IMAGE
```

### Step 2 — Redeploy the updated service

```bash
gcloud run deploy fitnesspark-visualizer \
  --image $IMAGE \
  --region europe-west6 \
  --allow-unauthenticated
```

✅ The URL stays the same, and Cloud Run will automatically create a new revision.

To verify deployment logs:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="fitnesspark-visualizer"' --limit 50 --format="value(textPayload)"
```

---

## 🔢 Data and Charts

### Charts

1. **Today vs Typical (Same Weekday)** – compares today’s attendance with the average of the past 4 weeks for the same weekday, limited to gym opening hours (06:30–22:00).
2. **Weekly Attendance Patterns** – multi-line chart comparing the average visitor trends across weekdays (each line represents one weekday’s average attendance profile over the past 4 weeks).

### Summary Table

* Shows **average visitor counts** per hour slot for each weekday (last 4 weeks)
* Displays **daily peak** visitor count and the **time of that peak**

Example:

| Day | 06:00–07:00 | 07:00–08:00 | … | 21:00–22:00 | Peak | Peak Time  |
| --- | ----------- | ----------- | - | ----------- | ---- | ----- |
| Mon | 35          | 58          | … | 44          | 120  | 18:10 |
| Tue | 40          | 65          | … | 47          | 135  | 18:30 |

---

## 💡 Tips

* Refresh the page to get the **latest data** (new data logged every 10 minutes).
* You can enable automatic refresh with:

  ```html
  <meta http-equiv="refresh" content="600"> <!-- every 10 min -->
  ```
* Logs are visible in Cloud Run:

  ```bash
  gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="fitnesspark-visualizer"' --limit 50
  ```
* To verify visual changes after redeployment, simply refresh the dashboard — Cloud Run hot-swaps the new revision automatically.

---

## 🛡️ Summary

Your visualizer is a secure, auto-updating, zero-maintenance dashboard that:

* Fetches live data from Cloud Storage
* Visualizes trends and weekday patterns
* Focuses on open hours for clear insights
* Protects against spam and unnecessary costs
* Runs fully serverless on Google Cloud Run
