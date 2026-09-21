import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://api.hubapi.com"

# HubSpot's supported object API version used for CRM CRUD/search.
OBJECT_API_VERSION = "2026-03"

# Current associations API version.
ASSOCIATION_API_VERSION = "2026-09"

COMPANY_NAME = "TEST | JMMS RevOps Lab Company"
COMPANY_DOMAIN = "example-revops-lab.test"

CONTACT_FIRSTNAME = "HubSpot"
CONTACT_LASTNAME = "Lab Contact"
CONTACT_EMAIL = "revops-lab-contact@example.test"

DEAL_EXTERNAL_ID = "test_opp_002"
DEAL_ID_PROPERTY = "jmms_external_opportunity_id"

# HubSpot-defined directional association IDs.
CONTACT_TO_PRIMARY_COMPANY = 1
DEAL_TO_PRIMARY_COMPANY = 5
DEAL_TO_CONTACT = 3


def get_service_key() -> str:
    key = os.getenv("HUBSPOT_SERVICE_KEY")

    if not key:
        raise RuntimeError(
            "HUBSPOT_SERVICE_KEY is not set. "
            "Load .env before running."
        )

    return key


def safety_check() -> None:
    if not DEAL_EXTERNAL_ID.startswith("test_"):
        raise RuntimeError(
            "Safety check failed: Deal external ID must begin with test_."
        )

    if not COMPANY_DOMAIN.endswith(".example"):
        raise RuntimeError(
            "Safety check failed: Lab company domain must use .example."
        )

    if not CONTACT_EMAIL.endswith("@example.com"):
        raise RuntimeError(
            "Safety check failed: Lab contact email must use example.com."
        )


def request_json(
    url: str,
    method: str,
    payload: dict | list | None = None,
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


def search_one(
    object_type: str,
    property_name: str,
    value: str,
    properties: list[str],
) -> dict | None:
    url = (
        f"{BASE_URL}/crm/objects/"
        f"{OBJECT_API_VERSION}/{object_type}/search"
    )

    payload = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": property_name,
                        "operator": "EQ",
                        "value": value,
                    }
                ]
            }
        ],
        "properties": properties,
        "limit": 2,
    }

    response = request_json(
        url=url,
        method="POST",
        payload=payload,
    )

    results = response.get("results", [])

    if len(results) > 1:
        print(
            f"FAIL: Multiple {object_type} records matched "
            f"{property_name}={value}.",
            file=sys.stderr,
        )
        print(
            "Manual deduplication is required before automation continues.",
            file=sys.stderr,
        )
        print(json.dumps(response, indent=2), file=sys.stderr)
        raise SystemExit(2)

    if not results:
        return None

    return results[0]


def create_object(
    object_type: str,
    properties: dict,
) -> dict:
    url = (
        f"{BASE_URL}/crm/objects/"
        f"{OBJECT_API_VERSION}/{object_type}"
    )

    return request_json(
        url=url,
        method="POST",
        payload={"properties": properties},
    )


def update_object(
    object_type: str,
    object_id: str,
    properties: dict,
) -> dict:
    encoded_id = urllib.parse.quote(
        str(object_id),
        safe="",
    )

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{OBJECT_API_VERSION}/{object_type}/{encoded_id}"
    )

    return request_json(
        url=url,
        method="PATCH",
        payload={"properties": properties},
    )


def upsert_company() -> tuple[dict, str]:
    properties = {
        "name": COMPANY_NAME,
        "domain": COMPANY_DOMAIN,
    }

    existing = search_one(
        object_type="companies",
        property_name="domain",
        value=COMPANY_DOMAIN,
        properties=[
            "name",
            "domain",
        ],
    )

    if existing is None:
        created = create_object(
            object_type="companies",
            properties=properties,
        )

        return created, "CREATED"

    updated = update_object(
        object_type="companies",
        object_id=existing["id"],
        properties=properties,
    )

    return updated, "UPDATED"


def upsert_contact() -> tuple[dict, str]:
    properties = {
        "firstname": CONTACT_FIRSTNAME,
        "lastname": CONTACT_LASTNAME,
        "email": CONTACT_EMAIL,
    }

    existing = search_one(
        object_type="contacts",
        property_name="email",
        value=CONTACT_EMAIL,
        properties=[
            "firstname",
            "lastname",
            "email",
        ],
    )

    if existing is None:
        created = create_object(
            object_type="contacts",
            properties=properties,
        )

        return created, "CREATED"

    updated = update_object(
        object_type="contacts",
        object_id=existing["id"],
        properties=properties,
    )

    return updated, "UPDATED"


def read_deal_by_external_id() -> dict:
    encoded_id = urllib.parse.quote(
        DEAL_EXTERNAL_ID,
        safe="",
    )

    params = urllib.parse.urlencode(
        {
            "idProperty": DEAL_ID_PROPERTY,
            "properties": (
                "dealname,"
                "jmms_external_opportunity_id"
            ),
        }
    )

    url = (
        f"{BASE_URL}/crm/objects/"
        f"{OBJECT_API_VERSION}/deals/"
        f"{encoded_id}?{params}"
    )

    return request_json(
        url=url,
        method="GET",
    )


def associate(
    from_object: str,
    from_id: str,
    to_object: str,
    to_id: str,
    association_type_id: int,
) -> dict:
    url = (
        f"{BASE_URL}/crm/objects/"
        f"{ASSOCIATION_API_VERSION}/"
        f"{from_object}/{from_id}/associations/"
        f"{to_object}/{to_id}"
    )

    payload = [
        {
            "associationCategory": "HUBSPOT_DEFINED",
            "associationTypeId": association_type_id,
        }
    ]

    return request_json(
        url=url,
        method="PUT",
        payload=payload,
    )


def read_associations(
    from_object: str,
    from_id: str,
    to_object: str,
) -> dict:
    url = (
        f"{BASE_URL}/crm/objects/"
        f"{ASSOCIATION_API_VERSION}/"
        f"{from_object}/{from_id}/associations/"
        f"{to_object}"
    )

    return request_json(
        url=url,
        method="GET",
    )


def verify_association(
    response: dict,
    expected_target_id: str,
    expected_type_id: int,
    description: str,
) -> None:
    expected_target_id = str(expected_target_id)

    for association in response.get("results", []):
        target_id = str(
            association.get("toObjectId", "")
        )

        if target_id != expected_target_id:
            continue

        association_types = association.get(
            "associationTypes",
            [],
        )

        type_ids = {
            int(item["typeId"])
            for item in association_types
            if item.get("typeId") is not None
        }

        if expected_type_id in type_ids:
            print(f"PASS: {description}")
            return

    print(
        f"FAIL: {description}",
        file=sys.stderr,
    )
    print(
        json.dumps(response, indent=2),
        file=sys.stderr,
    )
    raise SystemExit(3)


def main() -> None:
    safety_check()

    company, company_action = upsert_company()
    company_id = str(company["id"])

    print(
        f"PASS: Company {company_action}"
    )
    print(f"Company ID: {company_id}")

    contact, contact_action = upsert_contact()
    contact_id = str(contact["id"])

    print(
        f"PASS: Contact {contact_action}"
    )
    print(f"Contact ID: {contact_id}")

    deal = read_deal_by_external_id()
    deal_id = str(deal["id"])

    print("PASS: Existing Deal found")
    print(f"Deal ID: {deal_id}")

    associate(
        from_object="contact",
        from_id=contact_id,
        to_object="company",
        to_id=company_id,
        association_type_id=CONTACT_TO_PRIMARY_COMPANY,
    )

    associate(
        from_object="deal",
        from_id=deal_id,
        to_object="company",
        to_id=company_id,
        association_type_id=DEAL_TO_PRIMARY_COMPANY,
    )

    associate(
        from_object="deal",
        from_id=deal_id,
        to_object="contact",
        to_id=contact_id,
        association_type_id=DEAL_TO_CONTACT,
    )

    contact_companies = read_associations(
        from_object="contact",
        from_id=contact_id,
        to_object="company",
    )

    verify_association(
        response=contact_companies,
        expected_target_id=company_id,
        expected_type_id=CONTACT_TO_PRIMARY_COMPANY,
        description=(
            "Contact → Primary Company association verified"
        ),
    )

    deal_companies = read_associations(
        from_object="deal",
        from_id=deal_id,
        to_object="company",
    )

    verify_association(
        response=deal_companies,
        expected_target_id=company_id,
        expected_type_id=DEAL_TO_PRIMARY_COMPANY,
        description=(
            "Deal → Primary Company association verified"
        ),
    )

    deal_contacts = read_associations(
        from_object="deal",
        from_id=deal_id,
        to_object="contact",
    )

    verify_association(
        response=deal_contacts,
        expected_target_id=contact_id,
        expected_type_id=DEAL_TO_CONTACT,
        description=(
            "Deal → Contact association verified"
        ),
    )

    print()
    print("PASS: Relationship graph verified")

    print(
        json.dumps(
            {
                "company": {
                    "id": company_id,
                    "name": COMPANY_NAME,
                    "domain": COMPANY_DOMAIN,
                    "action": company_action,
                },
                "contact": {
                    "id": contact_id,
                    "email": CONTACT_EMAIL,
                    "action": contact_action,
                },
                "deal": {
                    "id": deal_id,
                    "external_opportunity_id": (
                        DEAL_EXTERNAL_ID
                    ),
                },
                "associations": {
                    "contact_primary_company": True,
                    "deal_primary_company": True,
                    "deal_contact": True,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()