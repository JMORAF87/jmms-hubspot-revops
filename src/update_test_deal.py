import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://api.hubapi.com"

TARGET_EXTERNAL_ID = "test_opp_001"
ID_PROPERTY = "jmms_external_opportunity_id"

NEW_REVENUE_LEAK_STATUS = "Review Required"


def get_service_key() -> str:
    key = os.getenv("HUBSPOT_SERVICE_KEY")

    if not key:
        raise RuntimeError(
            "HUBSPOT_SERVICE_KEY is not set. "
            "Load .env before running."
        )

    return key


def safety_check() -> None:
    if not TARGET_EXTERNAL_ID.startswith("test_"):
        raise RuntimeError(
            "Safety check failed: this script may only modify "
            "test opportunities."
        )


def update_test_deal() -> dict:
    safety_check()

    encoded_id = urllib.parse.quote(TARGET_EXTERNAL_ID, safe="")
    encoded_property = urllib.parse.quote(ID_PROPERTY, safe="")

    url = (
        f"{BASE_URL}/crm/v3/objects/deals/{encoded_id}"
        f"?idProperty={encoded_property}"
    )

    payload = {
        "properties": {
            "jmms_revenue_leak_status": NEW_REVENUE_LEAK_STATUS
        }
    }

    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {get_service_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="PATCH",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")

        print(
            f"HubSpot API HTTP {exc.code}",
            file=sys.stderr,
        )
        print(response_body, file=sys.stderr)

        raise SystemExit(1) from exc

    except urllib.error.URLError as exc:
        print(
            f"HubSpot API connection error: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1) from exc


def main() -> None:
    result = update_test_deal()

    properties = result.get("properties", {})

    print("PASS: Lab test Deal updated")
    print(
        json.dumps(
            {
                "hubspot_deal_id": result.get("id"),
                "external_opportunity_id": TARGET_EXTERNAL_ID,
                "jmms_revenue_leak_status": properties.get(
                    "jmms_revenue_leak_status"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()