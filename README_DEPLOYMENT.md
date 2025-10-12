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
gsutil mb -p fitnesspark-attendance -l europe-west6 gs://fitnesspark-attendance-data/
```

### 1.5 Grant Permissions to Cloud Run Service Account

Cloud Run Jobs use a service account to access resources. Ensure it can write to your bucket.

```bash
export PROJECT_NUMBER=$(gcloud projects describe fitnesspark-attendance --format="value(projectNumber)")
gsutil iam ch serviceAccount:service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com:roles/storage.objectAdmin gs://fitnesspark-attendance-data
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

Cloud Scheduler triggers your Cloud Run Job every 10 minutes by calling the Cloud Run Job execution API via HTTPS with IAM authentication.

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

The Cloud Run Job execution endpoint:

```
https://europe-west6-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/fitnesspark-attendance/jobs/fitnesspark-attendance-job:run
```

Create the scheduler job:

```bash
gcloud scheduler jobs create http fitnesspark-attendance-schedule \
  --schedule="*/10 * * * *" \
  --time-zone="Europe/Zurich" \
  --uri="https://europe-west6-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/fitnesspark-attendance/jobs/fitnesspark-attendance-job:run" \
  --http-method=POST \
  --oauth-service-account-email="scheduler-sa@fitnesspark-attendance.iam.gserviceaccount.com" \
  --location=europe-west6
```

This securely triggers your Cloud Run Job every 10 minutes using OAuth authentication.

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
gsutil cat gs://fitnesspark-attendance-data/attendance/attendance_data.jsonl
```

### List Executions

```bash
gcloud run jobs executions list --region europe-west6
```

### Update Schedule Timing

```bash
gcloud scheduler jobs update http fitnesspark-attendance-schedule \
  --schedule="*/15 * * * *" \
  --time-zone="Europe/Zurich" \
  --location=europe-west6
```

---

## ✅ Summary

You now have a fully automated, cloud-native Python scraper that:

* Runs every 10 minutes via Cloud Scheduler → Cloud Run Jobs (authenticated trigger)
* Logs visitor counts to Cloud Storage
* Can be redeployed easily with one command (`gcloud builds submit`)
* Requires no manual servers or VMs
* Uses least-privilege IAM roles and regional Artifact Registry for deployment
