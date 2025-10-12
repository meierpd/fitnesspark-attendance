# 🏋️‍♂️ fitnesspark-attendance

A Python-based Google Cloud project that monitors live gym attendance from the Fitnesspark website and tracks it over time.

## 🚀 Overview
This project:
- Scrapes the public attendance data from the Fitnesspark website every 10 minutes.
- Stores the data for trend analysis.
- Provides a simple dashboard to visualize attendance now and historically.

## 🧱 Tech Stack
- **Python 3.9+**
- **Google Cloud Run** / **Cloud Scheduler**
- **Google Cloud Storage** or **Firestore**
- **BeautifulSoup4** for scraping
- **Matplotlib** or **Plotly** for visualization

## ⚙️ Project Structure# 🏋️‍♂️ fitnesspark-attendance

A Python-based Google Cloud project that monitors live gym attendance from the Fitnesspark website and tracks it over time.

## 🚀 Overview

This project:

* Scrapes the public attendance data from the Fitnesspark website every 10 minutes.
* Stores the data for trend analysis.
* Provides a simple dashboard to visualize attendance now and historically.

## 🧱 Tech Stack

* **Python 3.9+**
* **Google Cloud Run** / **Cloud Scheduler**
* **Google Cloud Storage** or **Firestore**
* **BeautifulSoup4** for scraping
* **Matplotlib** or **Plotly** for visualization

## ⚙️ Project Structure

```
fitnesspark-attendance/
├── scraper/
│   └── fetcher.py        # Fetches live attendance data
├── run.py                # Entry point for scheduler / Cloud Run
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── .gitignore            # Ignored files and folders
```

## 🧰 Development

1. Clone this repo:

   ```bash
   git clone git@github.com:yourusername/fitnesspark-attendance.git
   cd fitnesspark-attendance
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run the scraper locally:

   ```bash
   python run.py
   ```

## 🗕️ Roadmap

* [ ] Implement the scraper logic
* [ ] Store results in Cloud Storage
* [ ] Deploy as a Cloud Run service
* [ ] Schedule runs every 10 minutes
* [ ] Build a simple web dashboard

## 🛡️ License

MIT License (add later if desired)
