# 🏋️‍♂️ fitnesspark-attendance

A Python-based cloud project that monitors live gym attendance data from the Fitnesspark Trafo Baden website and stores it in Google Cloud Storage for historical analysis and visualization.

---

## 🧭 Overview

The project periodically fetches the current visitor count from the Fitnesspark Baden Trafo web page and logs it to a Google Cloud Storage bucket as structured JSONL records. Each entry includes:

* Timestamp
* Visitor count
* Status (e.g., `ok`, `closed_no_data`, `no_visitors`, or `error`)

This enables later visualization of gym attendance trends over time.

---

## ⚙️ Architecture

```
Cloud Scheduler → Cloud Run Job → Python scraper → Cloud Storage
```

1. **Cloud Scheduler** triggers the job every 10 minutes during opening hours (Mon–Fri 06:30–22:00; Sat–Sun 09:00–20:00, Europe/Zurich; closing time excluded).
2. **Cloud Run Job** runs the Python scraper container.
3. **Python scraper** fetches data from the Fitnesspark website.
4. **Cloud Storage** stores results in `gs://fitnesspark-attendance-data/attendance/attendance_data.jsonl`.

---

## 🧩 Components

* `scraper/fetcher.py` – Fetches visitor data from the Fitnesspark website.
* `scraper/storage.py` – Appends results to Cloud Storage (JSONL format).
* `run.py` – Main entry point for Cloud Run Job execution.
* `requirements.txt` – Python dependencies.
* `README_DEPLOYMENT.md` – Full deployment instructions.

---

## 🧰 Local Development

To run locally for testing:

```bash
# Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the scraper manually
python run.py
```

You will need a valid `gcloud auth application-default login` session for credentials to access Cloud Storage.

---

## ☁️ Deployment

Deployment and automation details (including containerization, Cloud Run Job creation, and Scheduler setup) are documented in [**README_DEPLOYMENT.md**](./README_DEPLOYMENT.md).

---

## 📊 Future Enhancements

* Web dashboard for real-time and historical attendance visualization.
* Data quality monitoring and alerting.
* Support for multiple Fitnesspark locations.

---

## 🪪 License

MIT License © 2025 Pascal D. Meier
