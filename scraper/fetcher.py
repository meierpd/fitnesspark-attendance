import logging
import requests
from bs4 import BeautifulSoup


class AttendanceFetcher:
    """
    Fetches the current visitor count from the Fitnesspark Baden-Trafo page.
    """

    URL = (
        "https://www.fitnesspark.ch/wp/wp-admin/admin-ajax.php"
        "?action=single_park_update_visitors"
        "&park_id=680"
        "&location_id=57"
        "&location_name=FP_Trafo_Baden"
    )

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_attendance(self) -> tuple[int | None, str]:
        """Fetch the current visitor count and return (count, status)."""
        try:
            response = requests.get(self.URL, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            html = response.text.strip()

            # Case 1: Normal number
            if html.isdigit():
                count = int(html)
                self.logger.info("Fetched visitor count: %d", count)
                return count, "ok"

            # Case 2: Known 'no visitors' message
            if "Aktuell keine Besucher" in html:
                self.logger.info("No visitors currently at the gym.")
                return 0, "no_visitors"

            # Case 3: 'data not available' or dash response
            if (
                "Aktuelle Besucherzahl konnte nicht abgerufen werden" in html
                or html in ("—", "-", "–")
            ):
                self.logger.info("Visitor data unavailable or gym closed.")
                return 0, "closed_no_data"

            # Case 4: HTML span fallback
            soup = BeautifulSoup(html, "html.parser")
            span = soup.find("span")
            if span:
                text = span.text.strip()
                if text.isdigit():
                    return int(text), "ok"
                if "keine Besucher" in text:
                    return 0, "no_visitors"
                if "nicht abgerufen" in text or text in ("—", "-", "–"):
                    return 0, "closed_no_data"

            self.logger.warning("Unexpected response: %s", html[:200])
            return 0, "closed_no_data"

        except Exception as e:
            self.logger.error("Failed to fetch attendance: %s", e, exc_info=True)
            return None, "error"
