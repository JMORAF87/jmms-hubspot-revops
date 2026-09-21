#!/usr/bin/env python3
"""
Structural and value validator for data/opportunity-log.csv.

Read-only: never mutates the CSV. Run before any commit that touches
opportunity-log.csv, and after any bulk/scripted append to it.

Usage:
    python3 scripts/validate_opportunity_log.py
"""

from pathlib import Path
import csv
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "data" / "opportunity-log.csv"

# Accepted lifecycle states for the public sample opportunity dataset.
VALID_PIPELINE_STATUSES = {
    "DISCOVERED", "VERIFIED", "QUALIFIED", "APPROVED", "PACKAGE_READY",
    "FORM_FILLED", "SUBMITTED", "FOLLOW_UP", "RESPONSE", "INTERVIEW",
    "WON", "LOST", "PASS", "STALE",
}

# Accepted pursuit decisions for the public sample opportunity dataset.
VALID_DECISIONS = {"PURSUE", "CONDITIONAL", "PASS"}

# Score fields are 0-100 per pipeline.md SS2, but a row may legitimately carry
# a non-numeric placeholder instead of a score (e.g. a hard-pass reached before
# scoring was computed).
SCORE_FIELDS = ["capability_fit", "market_quality", "pursuit_score"]
TOLERATED_SCORE_PLACEHOLDERS = {"n/a", "n/a - hard pass"}

# Fields that may legitimately be blank at any point in an opportunity's life.
OPTIONAL_BLANK_FIELDS = {
    "posted_date", "age_days", "applicant_count", "competition",
    "source_tier", "intermediary", "application_platform",
    "application_friction", "requires_vetting",
    "capability_fit", "market_quality", "pursuit_score",
    "date_applied", "response", "interview", "outcome", "revenue_value",
    "notes",
}


def is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def main() -> int:
    if not CSV_PATH.exists():
        print(f"ERROR: file not found: {CSV_PATH}")
        return 2

    with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("ERROR: CSV has no header row.")
            return 2

        expected_cols = len(header)
        col_index = {name: i for i, name in enumerate(header)}

        errors: list[str] = []
        warnings: list[str] = []
        row_count = 0

        for line_no, row in enumerate(reader, start=2):
            if not row:
                continue  # tolerate a genuinely blank trailing line
            row_count += 1

            if len(row) != expected_cols:
                errors.append(
                    f"Line {line_no}: {len(row)} columns, expected {expected_cols} "
                    f"(company={row[1] if len(row) > 1 else '?'!r})"
                )
                continue  # column-count mismatch makes indexed checks unreliable

            for field in SCORE_FIELDS:
                idx = col_index.get(field)
                if idx is None:
                    continue
                value = row[idx].strip()
                if value == "" or value.lower() in TOLERATED_SCORE_PLACEHOLDERS:
                    continue
                if not is_number(value):
                    errors.append(
                        f"Line {line_no}: {field}={value!r} is not numeric or a "
                        f"tolerated placeholder (blank, 'n/a', 'n/a - HARD PASS')"
                    )
                    continue
                num = float(value)
                if not (0 <= num <= 100):
                    errors.append(
                        f"Line {line_no}: {field}={value!r} is outside the 0-100 range"
                    )

            idx = col_index.get("pipeline_status")
            if idx is not None:
                value = row[idx].strip()
                if value and value not in VALID_PIPELINE_STATUSES:
                    errors.append(
                        f"Line {line_no}: pipeline_status={value!r} is not a known "
                        f"value (see VALID_PIPELINE_STATUSES)"
                    )

            idx = col_index.get("decision")
            if idx is not None:
                value = row[idx].strip()
                if value and value not in VALID_DECISIONS:
                    errors.append(
                        f"Line {line_no}: decision={value!r} is not a known value "
                        f"(expected one of {sorted(VALID_DECISIONS)})"
                    )

            # Fields not in OPTIONAL_BLANK_FIELDS are expected to be populated;
            # flag as a warning (not a hard error) if empty, since this is a
            # structural/value validator, not a completeness gate.
            for field, idx in col_index.items():
                if field in OPTIONAL_BLANK_FIELDS:
                    continue
                if row[idx].strip() == "":
                    warnings.append(f"Line {line_no}: {field!r} is blank")

        print(f"Checked {row_count} data row(s) against {expected_cols} expected columns.")

        if warnings:
            print(f"\n{len(warnings)} warning(s):")
            for w in warnings:
                print(f"  WARN: {w}")

        if errors:
            print(f"\n{len(errors)} error(s):")
            for e in errors:
                print(f"  FAIL: {e}")
            print("\nINVALID: fix the errors above before committing.")
            return 1

        print("\nVALID: no structural or value errors found.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
