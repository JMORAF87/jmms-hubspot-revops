import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://api.hubapi.com"

# Current HubSpot date-versioned CRM object API.
UPSERT_URL = f"{BASE_URL}/crm/objects/2026-03/deals/batch/upsert"

ID_PROPERTY = "jmms_external_opportunity_id"
DEFAULT_EXTERNAL_ID = "test_opp_002"

READ_PROPERTIES = [
    "dealname",
    "pipeline",
    "dealstage",
    "amount",
    "jmms_service_line",
    "jmms_acquisition_source",
    "jmms_qualification_score",
    "jmms_revenue_leak_status",
    "jmms_external_opportunity_id",
]


def get_service_key() -> str:
    key = os.getenv("HUBSPOT_SERVICE_KEY")

    if not key:
        raise RuntimeError(
            "HUBSPOT_SERVICE_KEY is not set. "
            "Load .env before running."
        )

    return key


def safety_check(external_id: str) -> None:
    if not external_id.startswith("test_"):
        raise RuntimeError(
            "Safety check failed: upsert_deal.py may only operate "
            "on Lab identifiers beginning with 'test_'."
        )


def request_json(
    url: str,
    method: str,
    payload: dict | None = None,
) -> dict:
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
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")

            if not raw:
                return {}

            return json.loads(raw)

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        print(
            f"HubSpot API HTTP {exc.code}",
            file=sys.stderr,
        )
        print(body, file=sys.stderr)

        raise SystemExit(1) from exc

    except urllib.error.URLError as exc:
        print(
            f"HubSpot API connection error: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1) from exc


def upsert_deal(
    external_id: str,
    amount: str,
    revenue_leak_status: str,
) -> dict:
    safety_check(external_id)

    payload = {
        "inputs": [
            {
                "id": external_id,
                "idProperty": ID_PROPERTY,
                "properties": {
                    "dealname": "TEST | Idempotent Deal Upsert",
                    "pipeline": "default",
                    "dealstage": "appointmentscheduled",
                    "amount": amount,
                    "jmms_service_line": "CRM / RevOps",
                    "jmms_acquisition_source": "Direct Outreach",
                    "jmms_qualification_score": "85",
                    "jmms_revenue_leak_status": revenue_leak_status,
                },
            }
        ]
    }

    result = request_json(
        UPSERT_URL,
        method="POST",
        payload=payload,
    )

    results = result.get("results", [])

    if len(results) != 1:
        print(
            "FAIL: Expected exactly one HubSpot upsert result.",
            file=sys.stderr,
        )
        print(json.dumps(result, indent=2), file=sys.stderr)
        raise SystemExit(2)

    return results[0]


def read_by_external_id(external_id: str) -> dict:
    safety_check(external_id)

    encoded_id = urllib.parse.quote(external_id, safe="")
    encoded_id_property = urllib.parse.quote(ID_PROPERTY, safe="")

    params = urllib.parse.urlencode(
        {
            "idProperty": encoded_id_property,
            "properties": ",".join(READ_PROPERTIES),
        }
    )

    url = (
        f"{BASE_URL}/crm/objects/2026-03/deals/"
        f"{encoded_id}?{params}"
    )

    return request_json(
        url,
        method="GET",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely create or update a HubSpot Lab Deal "
            "using JMMS External Opportunity ID."
        )
    )

    parser.add_argument(
        "--external-id",
        default=DEFAULT_EXTERNAL_ID,
        help=(
            "JMMS external opportunity ID. "
            "Must begin with test_."
        ),
    )

    parser.add_argument(
        "--amount",
        default="1500",
        help="Deal amount to persist.",
    )

    parser.add_argument(
        "--status",
        default="Healthy",
        choices=[
            "Healthy",
            "Missing Next Step",
            "Follow-up Overdue",
            "Stale Opportunity",
            "Close Date Overdue",
            "Data Incomplete",
            "Review Required",
        ],
        help="JMMS Revenue Leak Status.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    upsert_result = upsert_deal(
        external_id=args.external_id,
        amount=args.amount,
        revenue_leak_status=args.status,
    )

    verified = read_by_external_id(args.external_id)

    properties = verified.get("properties", {})

    action = (
        "CREATED"
        if upsert_result.get("new") is True
        else "UPDATED"
    )

    output = {
        "action": action,
        "hubspot_deal_id": verified.get("id"),
        "external_opportunity_id": properties.get(
            "jmms_external_opportunity_id"
        ),
        "deal_name": properties.get("dealname"),
        "deal_stage": properties.get("dealstage"),
        "amount": properties.get("amount"),
        "jmms_service_line": properties.get(
            "jmms_service_line"
        ),
        "jmms_acquisition_source": properties.get(
            "jmms_acquisition_source"
        ),
        "jmms_qualification_score": properties.get(
            "jmms_qualification_score"
        ),
        "jmms_revenue_leak_status": properties.get(
            "jmms_revenue_leak_status"
        ),
    }

    if (
        output["external_opportunity_id"]
        != args.external_id
    ):
        print(
            "FAIL: Read-back external ID does not match input.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    if output["amount"] != args.amount:
        print(
            "FAIL: Read-back amount does not match requested value.",
            file=sys.stderr,
        )
        raise SystemExit(4)

    if (
        output["jmms_revenue_leak_status"]
        != args.status
    ):
        print(
            "FAIL: Read-back revenue leak status does not match.",
            file=sys.stderr,
        )
        raise SystemExit(5)

    print(f"PASS: Deal upsert {action}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()