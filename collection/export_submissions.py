#!/usr/bin/env python3
"""Export collected parameters to CSV.

The programme has no read endpoint by design — submissions go in over HTTP and
come out only here, run by someone with server access. That keeps a public form
from doubling as a way to read everyone else's answers.

The output columns match the desktop tool's CSV exactly, so anything already
built against HHS_Missing_Parameters_Local.csv keeps working:

    Full Name, Company Employee Code, Collection Date,
    <the 25 parameter labels>, Notes, Last Updated Local

Usage, from the repo root:

    python -m collection.export_submissions               # to stdout
    python -m collection.export_submissions -o out.csv

On the server, where the code lives inside the container:

    docker compose exec api python -m collection.export_submissions -o /tmp/x.csv
    docker compose cp api:/tmp/x.csv ./submissions.csv
"""

import argparse
import csv
import sys
from typing import Any

from collection.schema import FIELDS
from collection.store import _collection

COLUMNS = [
    "Full Name",
    "Company Employee Code",
    "Collection Date",
    *[field["label"] for field in FIELDS],
    "Notes",
    "Last Updated Local",
]


def _cell(answer: dict[str, Any] | None) -> str:
    """An unanswered parameter is impossible — the API rejects those — so a
    blank here would mean data loss upstream. Unknown is written as the literal
    word, matching the desktop tool."""

    if answer is None:
        return ""
    if answer.get("unknown"):
        return "Unknown"
    value = answer.get("value")
    return "" if value is None else str(value)


def rows() -> list[dict[str, str]]:
    out = []

    for doc in _collection().find({}).sort("employee_code", 1):
        answers = doc.get("answers", {})
        created = doc.get("created_at")
        updated = doc.get("updated_at")

        row = {
            "Full Name": doc.get("full_name", ""),
            "Company Employee Code": doc.get("employee_code", ""),
            "Collection Date": created.date().isoformat() if created else "",
            "Notes": _cell(answers.get("_notes")),
            "Last Updated Local": updated.isoformat() if updated else "",
        }
        for field in FIELDS:
            row[field["label"]] = _cell(answers.get(field["key"]))

        out.append(row)

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", help="write here instead of stdout")
    args = parser.parse_args()

    data = rows()
    stream = open(args.out, "w", newline="", encoding="utf-8-sig") if args.out else sys.stdout

    try:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(data)
    finally:
        if args.out:
            stream.close()

    if args.out:
        print(f"{len(data)} submission(s) -> {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
