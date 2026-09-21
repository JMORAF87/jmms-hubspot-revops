import sys
import unittest
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path


SRC_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "src"
)

sys.path.insert(
    0,
    str(SRC_DIR),
)

from revenue_leak_monitor import (  # noqa: E402
    classify_revenue_leak,
)


class RevenueLeakMonitorTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.now = datetime(
            2026,
            9,
            17,
            21,
            0,
            tzinfo=timezone.utc,
        )

        self.base = {
            "dealstage": "qualifiedtobuy",
            "hubspot_owner_id": "123",
            "num_associated_contacts": "1",
            "hs_next_step": (
                "Send implementation plan"
            ),
            "closedate": None,
            "notes_next_activity_date": (
                (
                    self.now
                    + timedelta(days=2)
                ).isoformat()
            ),
            "notes_last_updated": (
                (
                    self.now
                    - timedelta(days=2)
                ).isoformat()
            ),
            "createdate": (
                (
                    self.now
                    - timedelta(days=5)
                ).isoformat()
            ),
        }

    def classify(
        self,
        overrides=None,
    ):
        properties = dict(
            self.base
        )

        if overrides:
            properties.update(
                overrides
            )

        return classify_revenue_leak(
            properties,
            self.now,
        )

    def test_data_incomplete(self):
        status, _ = self.classify(
            {
                "hubspot_owner_id": None,
                "num_associated_contacts": "0",
            }
        )

        self.assertEqual(
            status,
            "Data Incomplete",
        )

    def test_close_date_overdue(self):
        status, _ = self.classify(
            {
                "closedate": (
                    (
                        self.now
                        - timedelta(days=1)
                    ).isoformat()
                )
            }
        )

        self.assertEqual(
            status,
            "Close Date Overdue",
        )

    def test_follow_up_overdue(self):
        status, _ = self.classify(
            {
                "notes_next_activity_date": (
                    (
                        self.now
                        - timedelta(hours=4)
                    ).isoformat()
                )
            }
        )

        self.assertEqual(
            status,
            "Follow-up Overdue",
        )

    def test_missing_next_step(self):
        status, _ = self.classify(
            {
                "hs_next_step": None,
                "notes_next_activity_date": None,
            }
        )

        self.assertEqual(
            status,
            "Missing Next Step",
        )

    def test_stale_opportunity(self):
        status, _ = self.classify(
            {
                "notes_last_updated": (
                    (
                        self.now
                        - timedelta(days=15)
                    ).isoformat()
                ),
                "notes_next_activity_date": (
                    (
                        self.now
                        + timedelta(days=2)
                    ).isoformat()
                ),
            }
        )

        self.assertEqual(
            status,
            "Stale Opportunity",
        )

    def test_healthy(self):
        status, _ = self.classify()

        self.assertEqual(
            status,
            "Healthy",
        )

    def test_new_opportunity_does_not_require_next_step(self):
        status, _ = self.classify(
            {
                "dealstage": (
                    "appointmentscheduled"
                ),
                "hs_next_step": None,
                "notes_next_activity_date": None,
            }
        )

        self.assertEqual(
            status,
            "Healthy",
        )


if __name__ == "__main__":
    unittest.main()