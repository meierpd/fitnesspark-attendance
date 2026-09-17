import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from ops.configure_schedules import configure


def matches(value, field):
    if field == "*":
        return True
    if field.startswith("*/"):
        return value % int(field[2:]) == 0
    return any(
        int(part.split("-")[0]) <= value <= int(part.split("-")[-1])
        for part in field.split(",")
    )


class ScheduleTests(unittest.TestCase):
    def test_every_minute_of_week_matches_opening_hours_without_overlap(self):
        schedules = json.loads(Path("ops/schedules.json").read_text())
        self.assertEqual(len(schedules), 3)
        for day in range(7):  # cron: Sunday=0
            opening, closing = (390, 1320) if 1 <= day <= 5 else (540, 1200)
            for minute in range(1440):
                hits = 0
                for cron in schedules.values():
                    m, h, dom, month, dow = cron.split()
                    self.assertEqual((dom, month), ("*", "*"))
                    hits += (matches(minute % 60, m) and
                             matches(minute // 60, h) and matches(day, dow))
                expected = int(opening <= minute < closing and minute % 10 == 0)
                self.assertEqual(hits, expected, (day, minute))

    @patch("ops.configure_schedules.subprocess.run")
    def test_preview_does_not_contact_cloud(self, run):
        configure("test-project", "europe-west6")
        run.assert_not_called()

    @patch("ops.configure_schedules.subprocess.run")
    def test_apply_updates_original_and_creates_missing_jobs(self, run):
        run.return_value.stdout = json.dumps([
            {"name": "projects/p/locations/r/jobs/fitnesspark-attendance-schedule"}
        ])
        configure("test-project", "europe-west6", True)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual([c[3] for c in commands], ["list", "update", "create", "create"])
        for command in commands[1:]:
            self.assertIn("--time-zone=Europe/Zurich", command)
            self.assertIn("--project=test-project", command)

    @patch("ops.configure_schedules.subprocess.run")
    def test_failed_inventory_prevents_writes(self, run):
        run.side_effect = subprocess.CalledProcessError(1, "gcloud")
        with self.assertRaises(subprocess.CalledProcessError):
            configure("test-project", "europe-west6", True)
        self.assertEqual(run.call_count, 1)
