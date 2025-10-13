import logging
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from google.cloud import storage
import tempfile
import os


class CloudStorageLogger:
    """
    Handles appending attendance records to a single JSONL file in Cloud Storage.
    Each line = one JSON object: {"timestamp": ..., "count": ...}
    """

    def __init__(
        self, bucket_name: str, filename: str = "attendance/attendance_data.jsonl"
    ):
        self.bucket_name = bucket_name
        self.filename = filename
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.logger = logging.getLogger(self.__class__.__name__)

    def upload(self, count: int, status: str) -> None:
        """Append a new record to the JSONL file in Cloud Storage."""
        timestamp = datetime.now(ZoneInfo("Europe/Zurich")).isoformat()
        record = {"timestamp": timestamp, "count": count, "status": status}

        try:
            blob = self.bucket.blob(self.filename)

            # download existing content (if file exists)
            tmp_path = tempfile.mktemp()
            if blob.exists():
                blob.download_to_filename(tmp_path)
            else:
                open(tmp_path, "w").close()

            # append new record
            with open(tmp_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # re-upload file
            blob.upload_from_filename(tmp_path, content_type="application/json")
            os.remove(tmp_path)

            self.logger.info(
                "Appended record to gs://%s/%s (%s, %d)",
                self.bucket_name,
                self.filename,
                timestamp,
                count,
            )

        except Exception as e:
            self.logger.error("Failed to append record: %s", e, exc_info=True)
