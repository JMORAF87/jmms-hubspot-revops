import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://api.hubapi.com"

PROPERTIES = [
    "dealname",
    "dealstage",
    "amount",
    "jmms_service_line",
    "jmms_acquisition_source",
    "jmms_qualification_score",
    "jmms_revenue_leak_status",
    "jmms_external_opportunity_id",
]

TARGET_EXTERNAL_ID = "test_opp_001"


def get_service_key() -> str:
    key = os.getenv("HUBSPOT_SERVICE_KEY")

    if not key:
        raise RuntimeError(
            "HUBSPOT_SERVICE_KEY is not set. "
            "Load .env before running."
        )

    return key


def fetch_deals() -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "limit": 100,
            "archived": "false",
            "properties": ",".join(PROPERTIES),
        }
    )

    url = f"{BASE_URL}/crm/v3/objects/deals?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {get_service_key()}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HubSpot API HTTP {exc.code}", file=sys.stderr)
        print(body, file=sys.stderr)
        raise SystemExit(1) from exc

    except urllib.error.URLError as exc:
        print(f"HubSpot API connection error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    return payload.get("results", [])


def find_target(deals: list[dict]) -> dict | None:
    for deal in deals:
        properties = deal.get("properties", {})

        if (
            properties.get("jmms_external_opportunity_id")
            == TARGET_EXTERNAL_ID
        ):
            return deal

    return None


def main() -> None:
    deals = fetch_deals()

    print(f"Deals returned: {len(deals)}")

    target = find_target(deals)

    if not target:
        print(
            f"FAIL: No deal found with "
            f"JMMS External Opportunity ID={TARGET_EXTERNAL_ID}"
        )
        raise SystemExit(2)

    properties = target.get("properties", {})

    output = {
        "hubspot_deal_id": target.get("id"),
        "deal_name": properties.get("dealname"),
        "deal_stage": properties.get("dealstage"),
        "amount": properties.get("amount"),
        "jmms_service_line": properties.get("jmms_service_line"),
        "jmms_acquisition_source": properties.get(
            "jmms_acquisition_source"
        ),
        "jmms_qualification_score": properties.get(
            "jmms_qualification_score"
        ),
        "jmms_revenue_leak_status": properties.get(
            "jmms_revenue_leak_status"
        ),
        "jmms_external_opportunity_id": properties.get(
            "jmms_external_opportunity_id"
        ),
    }

    print("PASS: Target HubSpot Deal found")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()