"""
Create API accounts from the command line.

Every endpoint requires a token and accounts are not self-serve, so the first
clinician has to be made here — after that, clinicians can create accounts over
the API with POST /api/v1/auth/users.

    python seed_users.py --email you@example.com --role clinician --name "Dr Rao"
    python seed_users.py --email pat@example.com --role patient \
        --patient-id HHS-TREND-0001
    python seed_users.py --list

Omit --password and one is generated and printed.
"""

import argparse
import secrets
import sys

from backend import users


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an HHS API account.")
    parser.add_argument("--email")
    parser.add_argument("--password", help="Generated and printed if omitted.")
    parser.add_argument("--role", choices=list(users.ROLES), default="clinician")
    parser.add_argument("--name", default="")
    parser.add_argument(
        "--patient-id",
        dest="patient_id",
        help="Required for --role patient. Must match an existing patient record.",
    )
    parser.add_argument("--list", action="store_true", help="List accounts and exit.")
    args = parser.parse_args()

    users.ensure_indexes()

    if args.list:
        found = users.list_users()
        if not found:
            print("No accounts yet.")
        for user in found:
            link = f" -> {user['patient_id']}" if user.get("patient_id") else ""
            print(f"{user['role']:>9}  {user['email']}{link}")
        return 0

    if not args.email:
        parser.error("--email is required (or use --list)")

    password = args.password or secrets.token_urlsafe(12)

    try:
        created = users.create_user(
            email=args.email,
            password=password,
            role=args.role,
            name=args.name,
            patient_id=args.patient_id,
        )
    except users.EmailTaken as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Created {created['role']} account {created['email']}")
    if created.get("patient_id"):
        print(f"  linked to patient {created['patient_id']}")
    if not args.password:
        print(f"  password: {password}")
        print("  Shown once — store it now.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
