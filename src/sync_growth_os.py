import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE_URL = "https://api.hubapi.com"
API_VERSION = "2026-09"

REPO_ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_LOG = REPO_ROOT / "data" / "opportunity-log.csv"

ID_PROPERTY = "jmms_external_opportunity_id"

DEFAULT_PIPELINE = "default"
DEFAULT_STAGE = "appointmentscheduled"

APPROVED_STATUS = "APPROVED"

REAL_ID_PATTERN = re.compile(
    r"^opp_[0-9a-f]{16}$"
)

TEST_ID_PATTERN = re.compile(
    r"^test_[A-Za-z0-9_-]+$"
)


def get_service_key() -> str:
    key = os.getenv("HUBSPOT_SERVICE_KEY")

    if not key:
        raise RuntimeError(
            "HUBSPOT_SERVICE_KEY is not set. "
            "Load .env first."
        )

    return key


def request_json(
    url: str,
    method: str,
    payload: dict | None = None,
    allow_not_found: bool = False,
) -> dict | None:
    headers = {
        "Authorization": f"Bearer {get_service_key()}",
        "Accept": "application/json",
    }

    data = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            raw = response.read().decode("utf-8")

            if not raw:
                return {}

            return json.loads(raw)

    except urllib.error.HTTPError as exc:
        if exc.code == 404 and allow_not_found:
            return None

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        print(
            f"HubSpot API HTTP {exc.code}",
            file=sys.stderr,
        )
        print(
            body,
            file=sys.stderr,
        )

        raise SystemExit(1) from exc

    except urllib.error.URLError as exc:
        print(
            f"HubSpot API connection error: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def normalize(value: str | None) -> str:
    return (value or "").strip()


def normalize_score(value: str) -> str | None:
    value = normalize(value)

    if not value:
        return None

    try:
        score = Decimal(value)
    except InvalidOperation:
        raise ValueError(
            f"Invalid pursuit_score: {value!r}"
        )

    if score < 0 or score > 100:
        raise ValueError(
            f"pursuit_score outside 0-100: {value!r}"
        )

    if score == score.to_integral():
        return str(int(score))

    return format(score.normalize(), "f")


def normalize_amount(value: str) -> str | None:
    """
    Accept only unambiguous numeric currency values.

    Examples accepted:
    4000
    4,000
    $4000
    $4,000.00

    Examples intentionally rejected:
    1500/mo
    75-100/hr
    TBD
    negotiable
    """

    value = normalize(value)

    if not value:
        return None

    cleaned = (
        value.replace("$", "")
        .replace(",", "")
        .strip()
    )

    if not re.fullmatch(
        r"\d+(?:\.\d{1,2})?",
        cleaned,
    ):
        return None

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None

    if amount < 0:
        return None

    if amount == amount.to_integral():
        return str(int(amount))

    return format(amount.normalize(), "f")


def map_acquisition_source(
    source: str,
) -> str:
    value = normalize(source).lower()

    if "linkedin" in value:
        return "LinkedIn"

    if "contra" in value:
        return "Contra"

    if "referral" in value:
        return "Referral"

    if "website" in value:
        return "Website"

    if "inbound" in value and "email" in value:
        return "Inbound Email"

    if "partner" in value:
        return "Partner"

    if "existing relationship" in value:
        return "Existing Relationship"

    if "direct outreach" in value:
        return "Direct Outreach"

    return "Other"


def read_growth_os_rows() -> list[dict[str, str]]:
    if not OPPORTUNITY_LOG.exists():
        raise RuntimeError(
            f"Opportunity log not found: "
            f"{OPPORTUNITY_LOG}"
        )

    with OPPORTUNITY_LOG.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def fixture_row() -> dict[str, str]:
    return {
        "opportunity_id": "test_growth_os_001",
        "company": "TEST | Growth OS Company",
        "opportunity": "Growth OS HubSpot Sync",
        "source": "Direct Outreach",
        "pursuit_score": "88",
        "pipeline_status": "APPROVED",
        "revenue_value": "2200",
    }


def validate_identity(
    opportunity_id: str,
    fixture: bool,
) -> None:
    pattern = (
        TEST_ID_PATTERN
        if fixture
        else REAL_ID_PATTERN
    )

    if not pattern.fullmatch(opportunity_id):
        raise ValueError(
            f"Invalid opportunity_id: "
            f"{opportunity_id!r}"
        )


def build_source_properties(
    row: dict[str, str],
    fixture: bool,
) -> dict[str, str]:
    opportunity_id = normalize(
        row.get("opportunity_id")
    )

    validate_identity(
        opportunity_id,
        fixture=fixture,
    )

    company = normalize(
        row.get("company")
    )

    opportunity = normalize(
        row.get("opportunity")
    )

    if not company:
        raise ValueError(
            f"{opportunity_id}: company is required"
        )

    if not opportunity:
        raise ValueError(
            f"{opportunity_id}: opportunity is required"
        )

    score = normalize_score(
        row.get("pursuit_score", "")
    )

    source = map_acquisition_source(
        row.get("source", "")
    )

    amount = normalize_amount(
        row.get("revenue_value", "")
    )

    properties = {
        "dealname": (
            f"LAB | {company} | {opportunity}"
        ),
        ID_PROPERTY: opportunity_id,
        "jmms_acquisition_source": source,
    }

    if score is not None:
        properties[
            "jmms_qualification_score"
        ] = score

    if amount is not None:
        properties["amount"] = amount

    return properties


def eligible_rows(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if normalize(
            row.get("pipeline_status")
        ).upper() == APPROVED_STATUS
    ]


def read_deal_by_external_id(
    external_id: str,
) -> dict | None:
    encoded_id = urllib.parse.quote(
        external_id,
        safe="",
    )

    params = urllib.parse.urlencode(
        {
            "idProperty": ID_PROPERTY,
            "properties": ",".join(
                [
                    "dealname",
                    "pipeline",
                    "dealstage",
                    "amount",
                    ID_PROPERTY,
                    "jmms_acquisition_source",
                    "jmms_qualification_score",
                ]
            ),
        }
    )

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{API_VERSION}/deals/"
        f"{encoded_id}?{params}"
    )

    return request_json(
        url=url,
        method="GET",
        allow_not_found=True,
    )


def create_deal(
    source_properties: dict[str, str],
) -> dict:
    properties = dict(source_properties)

    properties["pipeline"] = DEFAULT_PIPELINE
    properties["dealstage"] = DEFAULT_STAGE

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{API_VERSION}/deals"
    )

    result = request_json(
        url=url,
        method="POST",
        payload={
            "properties": properties,
        },
    )

    assert result is not None

    return result


def update_deal(
    deal_id: str,
    source_properties: dict[str, str],
) -> dict:
    """
    Update only Growth-OS-owned fields.

    Deliberately does NOT write:
    - pipeline
    - dealstage
    - Revenue Leak Status
    - activities / next steps
    """

    encoded_id = urllib.parse.quote(
        deal_id,
        safe="",
    )

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{API_VERSION}/deals/"
        f"{encoded_id}"
    )

    result = request_json(
        url=url,
        method="PATCH",
        payload={
            "properties": source_properties,
        },
    )

    assert result is not None

    return result


def amounts_equal(
    expected: str,
    actual: str | None,
) -> bool:
    try:
        return (
            Decimal(expected)
            == Decimal(normalize(actual))
        )
    except InvalidOperation:
        return False


def verify_readback(
    expected: dict[str, str],
    actual: dict,
) -> None:
    properties = actual.get(
        "properties",
        {},
    )

    simple_fields = [
        "dealname",
        ID_PROPERTY,
        "jmms_acquisition_source",
        "jmms_qualification_score",
    ]

    for field in simple_fields:
        if field not in expected:
            continue

        actual_value = normalize(
            properties.get(field)
        )

        if actual_value != expected[field]:
            raise RuntimeError(
                f"Read-back mismatch for {field}: "
                f"expected={expected[field]!r}, "
                f"actual={actual_value!r}"
            )

    if "amount" in expected:
        if not amounts_equal(
            expected["amount"],
            properties.get("amount"),
        ):
            raise RuntimeError(
                "Read-back mismatch for amount: "
                f"expected={expected['amount']!r}, "
                f"actual={properties.get('amount')!r}"
            )


def apply_row(
    row: dict[str, str],
    fixture: bool,
) -> dict:
    source_properties = (
        build_source_properties(
            row,
            fixture=fixture,
        )
    )

    external_id = source_properties[
        ID_PROPERTY
    ]

    existing = read_deal_by_external_id(
        external_id
    )

    if existing is None:
        written = create_deal(
            source_properties
        )
        action = "CREATED"
        hubspot_id = str(written["id"])

    else:
        hubspot_id = str(existing["id"])

        update_deal(
            deal_id=hubspot_id,
            source_properties=source_properties,
        )

        action = "UPDATED"

    verified = read_deal_by_external_id(
        external_id
    )

    if verified is None:
        raise RuntimeError(
            f"{external_id}: Deal missing "
            f"after write"
        )

    if str(verified["id"]) != hubspot_id:
        raise RuntimeError(
            f"{external_id}: HubSpot Deal ID "
            f"changed unexpectedly"
        )

    verify_readback(
        expected=source_properties,
        actual=verified,
    )

    return {
        "action": action,
        "hubspot_deal_id": hubspot_id,
        "external_opportunity_id": external_id,
        "dealname": source_properties[
            "dealname"
        ],
        "amount": source_properties.get(
            "amount"
        ),
        "qualification_score": (
            source_properties.get(
                "jmms_qualification_score"
            )
        ),
        "acquisition_source": (
            source_properties[
                "jmms_acquisition_source"
            ]
        ),
        "verified": True,
    }


def print_dry_run(
    rows: list[dict[str, str]],
    fixture: bool,
) -> None:
    print("MODE: DRY RUN")
    print(
        f"Eligible opportunities: {len(rows)}"
    )

    for row in rows:
        properties = build_source_properties(
            row,
            fixture=fixture,
        )

        print()
        print(
            json.dumps(
                {
                    "external_opportunity_id": (
                        properties[
                            ID_PROPERTY
                        ]
                    ),
                    "hubspot_properties": (
                        properties
                    ),
                    "create_only_defaults": {
                        "pipeline": (
                            DEFAULT_PIPELINE
                        ),
                        "dealstage": (
                            DEFAULT_STAGE
                        ),
                    },
                },
                indent=2,
            )
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize approved JMMS Growth OS "
            "opportunities into the HubSpot Lab."
        )
    )

    parser.add_argument(
        "--fixture",
        action="store_true",
        help=(
            "Use one in-memory fake approved "
            "opportunity instead of the real CSV."
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Perform HubSpot writes. "
            "Without this flag the command is dry-run."
        ),
    )

    parser.add_argument(
        "--allow-real-approved",
        action="store_true",
        help=(
            "Required with --apply when using "
            "real opportunity-log.csv rows."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if (
        args.apply
        and not args.fixture
        and not args.allow_real_approved
    ):
        raise SystemExit(
            "FAIL: Real Growth OS writes require "
            "--apply --allow-real-approved"
        )

    if args.fixture:
        rows = [
            fixture_row()
        ]
    else:
        rows = eligible_rows(
            read_growth_os_rows()
        )

    if not args.apply:
        print_dry_run(
            rows=rows,
            fixture=args.fixture,
        )
        return

    get_service_key()

    print("MODE: APPLY")
    print("TARGET: HubSpot Lab")
    print(
        f"Eligible opportunities: {len(rows)}"
    )

    results = []

    for row in rows:
        result = apply_row(
            row=row,
            fixture=args.fixture,
        )

        results.append(result)

        print()
        print(
            f"PASS: "
            f"{result['external_opportunity_id']} "
            f"{result['action']}"
        )
        print(
            f"HubSpot Deal ID: "
            f"{result['hubspot_deal_id']}"
        )

    print()
    print(
        "PASS: Growth OS → HubSpot "
        "sync completed"
    )
    print(
        json.dumps(
            results,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()