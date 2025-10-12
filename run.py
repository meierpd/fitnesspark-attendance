import logging
from scraper.fetcher import AttendanceFetcher
from scraper.storage import CloudStorageLogger

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

def main():
    setup_logging()
    fetcher = AttendanceFetcher()
    storage = CloudStorageLogger(bucket_name="fitnesspark-attendance-data")

    count, status = fetcher.fetch_attendance()
    if count is not None:
        logging.info("Fetched visitors=%d, status=%s", count, status)
        storage.upload(count, status)
    else:
        logging.warning("Fetch failed (status=%s)", status)

if __name__ == "__main__":
    main()