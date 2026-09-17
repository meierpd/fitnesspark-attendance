"""Create/update opening-hour schedules; preview unless --apply is supplied."""

import argparse
import json
from pathlib import Path
import shlex
import subprocess


def configure(project, region, apply=False):
    schedules = json.loads(Path(__file__).with_name("schedules.json").read_text())
    common = [f"--project={project}", f"--location={region}"]
    existing = set()
    if apply:
        # Listing must succeed before any writes; auth failures are not treated
        # as missing jobs. Reuse the original name to remove its 24-hour schedule.
        result = subprocess.run(
            ["gcloud", "scheduler", "jobs", "list", *common, "--format=json"],
            check=True, capture_output=True, text=True,
        )
        existing = {job["name"].rsplit("/", 1)[-1] for job in json.loads(result.stdout)}
    for name, cron in schedules.items():
        action = "update" if name in existing else "create"
        command = [
            "gcloud", "scheduler", "jobs", action, "http", name, *common,
            f"--schedule={cron}", "--time-zone=Europe/Zurich",
            f"--uri=https://{region}-run.googleapis.com/apis/run.googleapis.com/v1/"
            f"namespaces/{project}/jobs/fitnesspark-attendance-job:run",
            "--http-method=POST",
            f"--oauth-service-account-email=scheduler-sa@{project}.iam.gserviceaccount.com",
        ]
        print(shlex.join(command), flush=True)
        if apply:
            subprocess.run(command, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="fitnesspark-attendance")
    parser.add_argument("--region", default="europe-west6")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    configure(args.project, args.region, args.apply)
