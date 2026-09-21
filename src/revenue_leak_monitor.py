import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from sync_growth_os import (
    API_VERSION,
    BASE_URL,
    request_json,
)


LEAK_PROPERTY = "jmms_revenue_leak_status"

CLOSED_STAGES = {
    "closedwon",
    "closedlost",
}

NEW_OPPORTUNITY_STAGE = "appointmentscheduled"

STALE_AFTER_DAYS = 14

DEAL_PROPERTIES = [
    "dealname",
    "pipeline",
    "dealstage",
    "amount",
    "closedate",
    "createdate",
    "hubspot_owner_id",
    "hs_next_step",
    "notes_last_contacted",
    "notes_last_updated",
    "notes_next_activity_date",
    "num_associated_contacts",
    LEAK_PROPERTY,
    "jmms_external_opportunity_id",
]


def normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def parse_datetime(
    value: Any,
) -> datetime | None:
    text = normalize(value)

    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(timezone.utc)


def parse_int(
    value: Any,
    default: int = 0,
) -> int:
    text = normalize(value)

    if not text:
        return default

    try:
        return int(text)
    except ValueError:
        return default


def is_open_deal(
    properties: dict[str, Any],
) -> bool:
    stage = normalize(
        properties.get("dealstage")
    )

    return stage not in CLOSED_STAGES


def classify_revenue_leak(
    properties: dict[str, Any],
    now: datetime,
) -> tuple[str, list[str]]:
    """
    Return one deterministic Revenue Leak Status
    plus the reasons that caused the classification.

    Priority:
    1. Data Incomplete
    2. Close Date Overdue
    3. Follow-up Overdue
    4. Missing Next Step
    5. Stale Opportunity
    6. Healthy
    """

    stage = normalize(
        properties.get("dealstage")
    )

    owner_id = normalize(
        properties.get("hubspot_owner_id")
    )

    associated_contacts = parse_int(
        properties.get(
            "num_associated_contacts"
        )
    )

    next_step = normalize(
        properties.get("hs_next_step")
    )

    close_date = parse_datetime(
        properties.get("closedate")
    )

    next_activity = parse_datetime(
        properties.get(
            "notes_next_activity_date"
        )
    )

    last_activity = parse_datetime(
        properties.get(
            "notes_last_updated"
        )
    )

    created_at = parse_datetime(
        properties.get("createdate")
    )

    # 1. Data completeness
    incomplete_reasons = []

    if not owner_id:
        incomplete_reasons.append(
            "Deal owner is missing"
        )

    if associated_contacts < 1:
        incomplete_reasons.append(
            "No associated Contact"
        )

    if incomplete_reasons:
        return (
            "Data Incomplete",
            incomplete_reasons,
        )

    # 2. Close date overdue
    if (
        close_date is not None
        and close_date < now
    ):
        return (
            "Close Date Overdue",
            [
                (
                    "Close date is in the past: "
                    f"{close_date.isoformat()}"
                )
            ],
        )

    # 3. Follow-up overdue
    if (
        next_activity is not None
        and next_activity < now
    ):
        return (
            "Follow-up Overdue",
            [
                (
                    "Next activity is overdue: "
                    f"{next_activity.isoformat()}"
                )
            ],
        )

    # 4. Missing next step
    #
    # New Opportunity is allowed to exist briefly without
    # a defined next step. Any later open stage should have
    # either a written next step or a future activity.
    requires_next_step = (
        stage
        and stage != NEW_OPPORTUNITY_STAGE
        and stage not in CLOSED_STAGES
    )

    has_future_activity = (
        next_activity is not None
        and next_activity >= now
    )

    if (
        requires_next_step
        and not next_step
        and not has_future_activity
    ):
        return (
            "Missing Next Step",
            [
                (
                    "Open Deal beyond New Opportunity "
                    "has no next step or future activity"
                )
            ],
        )

    # 5. Stale opportunity
    #
    # Prefer actual activity timestamp. If there has never
    # been activity, use record creation as the baseline.
    activity_baseline = (
        last_activity
        if last_activity is not None
        else created_at
    )

    if activity_baseline is not None:
        age_days = (
            now - activity_baseline
        ).total_seconds() / 86400

        if age_days >= STALE_AFTER_DAYS:
            return (
                "Stale Opportunity",
                [
                    (
                        "No recorded activity for "
                        f"{age_days:.1f} days"
                    )
                ],
            )

    return (
        "Healthy",
        [
            (
                "No Revenue Leak Monitor rule "
                "currently triggered"
            )
        ],
    )


def read_deal(
    deal_id: str,
) -> dict:
    encoded_id = urllib.parse.quote(
        deal_id,
        safe="",
    )

    params = urllib.parse.urlencode(
        {
            "properties": ",".join(
                DEAL_PROPERTIES
            ),
        }
    )

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{API_VERSION}/deals/"
        f"{encoded_id}?{params}"
    )

    result = request_json(
        url=url,
        method="GET",
    )

    if result is None:
        raise RuntimeError(
            f"Deal not found: {deal_id}"
        )

    return result


def read_all_deals() -> list[dict]:
    deals = []
    after = None

    while True:
        params = {
            "limit": "100",
            "archived": "false",
            "properties": ",".join(
                DEAL_PROPERTIES
            ),
        }

        if after is not None:
            params["after"] = after

        query = urllib.parse.urlencode(
            params
        )

        url = (
            f"{BASE_URL}/crm/objects/"
            f"{API_VERSION}/deals?"
            f"{query}"
        )

        result = request_json(
            url=url,
            method="GET",
        )

        if result is None:
            break

        deals.extend(
            result.get("results", [])
        )

        after = (
            result.get("paging", {})
            .get("next", {})
            .get("after")
        )

        if not after:
            break

    return deals


def write_leak_status(
    deal_id: str,
    status: str,
) -> None:
    encoded_id = urllib.parse.quote(
        deal_id,
        safe="",
    )

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{API_VERSION}/deals/"
        f"{encoded_id}"
    )

    request_json(
        url=url,
        method="PATCH",
        payload={
            "properties": {
                LEAK_PROPERTY: status,
            }
        },
    )


def evaluate_deal(
    deal: dict,
    now: datetime,
) -> dict:
    properties = deal.get(
        "properties",
        {},
    )

    proposed_status, reasons = (
        classify_revenue_leak(
            properties=properties,
            now=now,
        )
    )

    current_status = normalize(
        properties.get(
            LEAK_PROPERTY
        )
    )

    return {
        "hubspot_deal_id": str(
            deal.get("id")
        ),
        "dealname": normalize(
            properties.get("dealname")
        ),
        "external_opportunity_id": (
            normalize(
                properties.get(
                    "jmms_external_opportunity_id"
                )
            )
        ),
        "dealstage": normalize(
            properties.get("dealstage")
        ),
        "current_status": (
            current_status or None
        ),
        "proposed_status": (
            proposed_status
        ),
        "changed": (
            current_status
            != proposed_status
        ),
        "reasons": reasons,
    }


def verify_write(
    deal_id: str,
    expected_status: str,
) -> None:
    deal = read_deal(
        deal_id
    )

    actual = normalize(
        deal.get(
            "properties",
            {},
        ).get(
            LEAK_PROPERTY
        )
    )

    if actual != expected_status:
        raise RuntimeError(
            "Revenue Leak Status read-back "
            "verification failed: "
            f"expected={expected_status!r}, "
            f"actual={actual!r}"
        )


def safe_to_apply(
    result: dict,
    allow_real: bool,
) -> bool:
    external_id = normalize(
        result.get(
            "external_opportunity_id"
        )
    )

    if external_id.startswith("test_"):
        return True

    return allow_real


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic JMMS HubSpot "
            "Revenue Leak Monitor."
        )
    )

    parser.add_argument(
        "--deal-id",
        help=(
            "Evaluate one HubSpot Deal "
            "instead of all Deals."
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Write JMMS Revenue Leak Status. "
            "Default behavior is dry-run."
        ),
    )

    parser.add_argument(
        "--allow-real",
        action="store_true",
        help=(
            "Allow --apply against Deals whose "
            "external ID does not begin with test_."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    now = datetime.now(
        timezone.utc
    )

    if args.deal_id:
        deals = [
            read_deal(
                args.deal_id
            )
        ]
    else:
        deals = read_all_deals()

    open_deals = [
        deal
        for deal in deals
        if is_open_deal(
            deal.get(
                "properties",
                {},
            )
        )
    ]

    print(
        "MODE:",
        "APPLY"
        if args.apply
        else "DRY RUN",
    )

    print(
        f"Open Deals evaluated: "
        f"{len(open_deals)}"
    )

    results = []

    for deal in open_deals:
        result = evaluate_deal(
            deal=deal,
            now=now,
        )

        if args.apply:
            if not safe_to_apply(
                result=result,
                allow_real=args.allow_real,
            ):
                raise RuntimeError(
                    "Refusing to modify non-test Deal "
                    "without --allow-real: "
                    f"{result['hubspot_deal_id']}"
                )

            if result["changed"]:
                write_leak_status(
                    deal_id=(
                        result[
                            "hubspot_deal_id"
                        ]
                    ),
                    status=(
                        result[
                            "proposed_status"
                        ]
                    ),
                )

                verify_write(
                    deal_id=(
                        result[
                            "hubspot_deal_id"
                        ]
                    ),
                    expected_status=(
                        result[
                            "proposed_status"
                        ]
                    ),
                )

                result["write"] = "UPDATED"

            else:
                result["write"] = "NO_CHANGE"

        results.append(result)

        print()
        print(
            json.dumps(
                result,
                indent=2,
            )
        )

    print()

    if args.apply:
        print(
            "PASS: Revenue Leak Monitor "
            "completed with read-back verification"
        )
    else:
        print(
            "PASS: Revenue Leak Monitor "
            "dry-run completed"
        )


if __name__ == "__main__":
    main()