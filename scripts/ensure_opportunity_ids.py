import csv
import hashlib
import os
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "opportunity-log.csv"

ID_FIELD = "opportunity_id"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def build_base_seed(row: dict[str, str]) -> str:
    """
    Build the one-time bootstrap identity seed.

    Once opportunity_id is persisted, this seed is no longer used
    for identity resolution.
    """

    parts = [
        normalize(row.get("date_discovered")),
        normalize(row.get("company")),
        normalize(row.get("opportunity")),
        normalize(row.get("primary_url")),
    ]

    if not any(parts):
        raise ValueError(
            "Cannot generate opportunity_id: row has no usable identity fields."
        )

    return "|".join(parts)


def hash_id(seed: str) -> str:
    digest = hashlib.sha256(
        seed.encode("utf-8")
    ).hexdigest()[:16]

    return f"opp_{digest}"


def main() -> None:
    if not CSV_PATH.exists():
        raise SystemExit(
            f"Opportunity log not found: {CSV_PATH}"
        )

    with CSV_PATH.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames:
        raise SystemExit(
            "Opportunity log has no CSV header."
        )

    if ID_FIELD not in fieldnames:
        insert_at = (
            fieldnames.index("date_discovered") + 1
            if "date_discovered" in fieldnames
            else 0
        )

        fieldnames.insert(
            insert_at,
            ID_FIELD,
        )

    existing_ids = {
        normalize(row.get(ID_FIELD))
        for row in rows
        if normalize(row.get(ID_FIELD))
    }

    generated = 0
    occurrence_by_seed: dict[str, int] = defaultdict(int)

    for row in rows:
        existing = normalize(
            row.get(ID_FIELD)
        )

        if existing:
            continue

        base_seed = build_base_seed(row)

        occurrence = occurrence_by_seed[base_seed]
        occurrence_by_seed[base_seed] += 1

        candidate_seed = (
            base_seed
            if occurrence == 0
            else f"{base_seed}|duplicate_ordinal={occurrence}"
        )

        candidate_id = hash_id(candidate_seed)

        # Extremely defensive collision handling.
        salt = 1

        while candidate_id in existing_ids:
            candidate_id = hash_id(
                f"{candidate_seed}|collision_salt={salt}"
            )
            salt += 1

        row[ID_FIELD] = candidate_id
        existing_ids.add(candidate_id)
        generated += 1

    ids = [
        normalize(row.get(ID_FIELD))
        for row in rows
    ]

    if any(not value for value in ids):
        raise SystemExit(
            "FAIL: At least one opportunity_id is blank."
        )

    if len(ids) != len(set(ids)):
        raise SystemExit(
            "FAIL: Duplicate opportunity_id values detected."
        )

    backup_path = (
        Path(tempfile.gettempdir())
        / "jmms-opportunity-log-before-ids.csv"
    )

    if not backup_path.exists():
        shutil.copy2(
            CSV_PATH,
            backup_path,
        )

    temp_path = CSV_PATH.with_suffix(".csv.tmp")

    with temp_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    os.replace(
        temp_path,
        CSV_PATH,
    )

    duplicate_seed_groups = sum(
        1
        for count in occurrence_by_seed.values()
        if count > 1
    )

    print(
        f"PASS: {len(rows)} opportunity rows validated"
    )
    print(
        f"Generated opportunity IDs: {generated}"
    )
    print(
        f"Unique opportunity IDs: {len(set(ids))}"
    )
    print(
        f"Duplicate bootstrap seed groups handled: "
        f"{duplicate_seed_groups}"
    )
    print(
        f"Backup: {backup_path}"
    )


if __name__ == "__main__":
    main()