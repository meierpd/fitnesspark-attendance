# 🏗️ Deployment Guide — fitnesspark-attendance

This document explains how to build, deploy, and automate the `fitnesspark-attendance` project using **Google Cloud Run Jobs**, **Artifact Registry**, and **Cloud Scheduler**.

---

## ☁️ 1. One-Time Project Setup

These steps are required once per Google Cloud project.

### 1.1 Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com
```

### 1.2 Set Your Project

```bash
gcloud config set project fitnesspark-attendance
```

### 1.3 Create Artifact Registry Repository

Create a regional Docker repository to store container images:

```bash
gcloud artifacts repositories create fitnesspark-attendance \
  --repository-format=docker \
  --location=europe-west6 \
  --description="Docker images for fitnesspark-attendance"
```

### 1.4 Create Cloud Storage Bucket

Used to store attendance logs.

```bash
gcloud storage buckets create gs://fitnesspark-attendance-data/ \
  --project=fitnesspark-attendance \
  --location=europe-west6
```

### 1.5 Grant Permissions to Cloud Run Service Account

Cloud Run Jobs use a service account to access resources. Ensure it can write to your bucket.

```bash
export PROJECT_NUMBER=$(gcloud projects describe fitnesspark-attendance --format="value(projectNumber)")
gcloud storage buckets add-iam-policy-binding gs://fitnesspark-attendance-data \
  --member="serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## 🚀 2. Build & Deploy

### 2.1 Set Variables

```bash
export PROJECT_ID=fitnesspark-attendance
export IMAGE="europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/runner:latest"
```

### 2.2 Build and Push Docker Image

```bash
gcloud builds submit --tag $IMAGE
```

This command packages your code and builds the container image in **Artifact Registry**.

### 2.3 Create Cloud Run Job

```bash
gcloud run jobs create fitnesspark-attendance-job \
  --image $IMAGE \
  --region europe-west6 \
  --max-retries 1 \
  --memory 512Mi \
  --cpu 1 \
  --task-timeout 600
```

This defines a job that runs your scraper once and exits.

### 2.4 Test Run Manually

```bash
gcloud run jobs execute fitnesspark-attendance-job --region europe-west6
```

Check logs to confirm successful execution:

```bash
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="fitnesspark-attendance-job"' \
  --limit 30 --project fitnesspark-attendance --format="value(textPayload)"
```

---

## ⏰ 3. Automate with Cloud Scheduler (Direct HTTP Trigger)

Cloud Scheduler triggers your Cloud Run Job every 10 minutes during opening hours by calling the Cloud Run Job execution API via HTTPS with IAM authentication.

### 3.1 Create a Scheduler Service Account

```bash
gcloud iam service-accounts create scheduler-sa \
  --display-name="Scheduler trigger account for Fitnesspark Job"
```

Grant it permission to invoke Cloud Run Jobs:

```bash
gcloud projects add-iam-policy-binding fitnesspark-attendance \
  --member="serviceAccount:scheduler-sa@fitnesspark-attendance.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### 3.2 Create Cloud Scheduler Job

From the repository root, preview or apply the schedules:

```bash
python3 ops/configure_schedules.py
python3 ops/configure_schedules.py --apply
```

The script updates the original `fitnesspark-attendance-schedule` instead of leaving
its old 24-hour trigger running, and creates or updates two additional triggers.
It can be rerun after a partial failure. Preview mode shows create commands without
contacting Google Cloud; apply mode discovers which jobs need updating.

| Trigger | Europe/Zurich local time | Cron |
| --- | --- | --- |
| Weekday opening | Mon–Fri 06:30, 06:40, 06:50 | `30,40,50 6 * * 1-5` |
| Weekday daytime | Mon–Fri 07:00–21:50, every ten minutes | `*/10 7-21 * * 1-5` |
| Weekend | Sat–Sun 09:00–19:50, every ten minutes | `*/10 9-19 * * 0,6` |

Opening time is included and closing time is excluded. This gives 93 observations
per weekday and 66 per weekend day. Schedules follow local daylight-saving time;
holidays use the normal weekday/weekend schedule. All triggers use OAuth and the
existing Scheduler service account to invoke the Cloud Run Job.

Cloud Scheduler includes three free jobs per billing account, shared with other
projects: https://cloud.google.com/scheduler/pricing

### 3.3 Verify Setup

```bash
gcloud scheduler jobs list --location=europe-west6
gcloud run jobs executions list --region=europe-west6
```

---

## 🔁 4. Redeploy After Code Changes

Whenever you modify your code:

1. **Rebuild the image**

   ```bash
   gcloud builds submit --tag $IMAGE
   ```

2. **Update the Cloud Run Job**

   ```bash
   gcloud run jobs update fitnesspark-attendance-job \
     --image $IMAGE \
     --region europe-west6
   ```

3. **Run manually or wait for the scheduler**

   ```bash
   gcloud run jobs execute fitnesspark-attendance-job --region europe-west6
   ```

---

## 🧹 5. Maintenance & Debugging

### Check Logs

```bash
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="fitnesspark-attendance-job"' \
  --limit 50 --project fitnesspark-attendance --format="value(textPayload)"
```

### Inspect Cloud Storage Data

```bash
gcloud storage cat gs://fitnesspark-attendance-data/attendance/attendance_data.jsonl
```

### List Executions

```bash
gcloud run jobs executions list --region europe-west6
```

### Update Opening Hours

Edit `ops/schedules.json`, run `python3 -m unittest discover -s tests`, and apply
with `python3 ops/configure_schedules.py --apply`. Update the schedule tests when
opening hours intentionally change. Do not restore the previous all-day trigger.

### Container Image Retention

`ops/artifact-cleanup.json` targets only untagged images older than 30 days. It
keeps all tagged images and the three newest versions of each image package.
Tagged versions must eventually be reviewed manually if obsolete tags accumulate.

Before enabling deletion, inspect the images referenced by the Cloud Run Job and
all service revisions that must remain deployable or available for rollback.
Protect each required digest with a tag; `latest` alone might point to a newer,
not-yet-deployed build. For each required image, use its actual digest:

```bash
gcloud artifacts docker tags add \
  europe-west6-docker.pkg.dev/fitnesspark-attendance/fitnesspark-attendance/runner@sha256:DIGEST \
  europe-west6-docker.pkg.dev/fitnesspark-attendance/fitnesspark-attendance/runner:retain-DEPLOYMENT
```

Do the same for required `visualizer` digests. Keep these retention tags until the
corresponding deployments and rollback versions are retired.

Start with a dry run (does not delete images):

```bash
gcloud artifacts repositories set-cleanup-policies fitnesspark-attendance \
  --project=fitnesspark-attendance --location=europe-west6 \
  --policy=ops/artifact-cleanup.json --dry-run
```

This replaces the repository's cleanup policies: inspect existing policies first.
Review dry-run results after the background evaluation (approximately one day).
Once candidates contain no required images, enable the reviewed policy:

```bash
gcloud artifacts repositories set-cleanup-policies fitnesspark-attendance \
  --project=fitnesspark-attendance --location=europe-west6 \
  --policy=ops/artifact-cleanup.json --no-dry-run
```

Policy behavior and dry-run inspection:
https://cloud.google.com/artifact-registry/docs/repositories/cleanup-policy

### Smaller Builds

The scraper installs only its three direct runtime dependencies; development tools
are in `requirements-dev.txt`. Both Dockerfiles copy dependency manifests before
application code and exclude test/development files from runtime images. Rebuild
and redeploy to use the smaller images; historical image storage is only reclaimed
when obsolete versions are removed by the reviewed cleanup policy.

---

## ✅ Summary

You now have a fully automated, cloud-native Python scraper that:

* Runs every 10 minutes during opening hours via Cloud Scheduler → Cloud Run Jobs (authenticated trigger)
* Logs visitor counts to Cloud Storage
* Can be redeployed easily with one command (`gcloud builds submit`)
* Requires no manual servers or VMs
* Uses least-privilege IAM roles and regional Artifact Registry for deployment
