"""
seed.py  –  One-time script to create starter data (Section 12.4 of the guide).

Run ONCE after `alembic upgrade head` or to refresh credentials:
    cd backend
    python seed.py

Creates/updates:
  1. The fixed list of 7 committees from the baseline.
  2. The President account (Head President, AICHECUSCgeneral@gmail.com).
  3. The Committee Admin accounts from admins_credentials.csv.

This script is idempotent — safe to run multiple times without duplicating rows.
"""

import os
import csv
from app.database import SessionLocal
from app.models.user import Committee, User, RoleEnum
from app.dependencies import hash_password

db = SessionLocal()

# ── 1. Committees (from the baseline's fixed list) ───────────────────────────
COMMITTEES_MAP = {
    "Marketing Head": "Marketing",
    "OC Head": "OC",
    "Technical Head": "Technical",
    "Web Development Head": "Web Development",
    "PR Head": "PR",
    "QC Head": "QC",
    "General Committee Head": "General Committee",
    "Head President": "General Committee",
}

COMMITTEES = [
    ("Marketing",        "AIChECU.Marketing@gmail.com"),
    ("OC",               "AIChECU.OC@gmail.com"),
    ("Technical",        "AIChECU.Technical@gmail.com"),
    ("Web Development",  "AIChECU.WebDevelopment@gmail.com"),
    ("PR",               "aichecu.pr@gmail.com"),
    ("QC",               "aiche.cu.qc@gmail.com"),
    ("General Committee","AICHECUSCgeneral@gmail.com"),
]

for name, email in COMMITTEES:
    existing_comm = db.query(Committee).filter_by(name=name).first()
    if not existing_comm:
        db.add(Committee(name=name, login_email=email))
        print(f"  [OK] Created committee: {name}")
    else:
        existing_comm.login_email = email
        print(f"  - Committee exists: {name}")

db.commit()

general_comm = db.query(Committee).filter_by(name="General Committee").first()
general_comm_id = general_comm.id if general_comm else None

# ── 2. Seed accounts from admins_credentials.csv ───────────────────────────
csv_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "admins_credentials.csv"),
    os.path.join(os.path.dirname(__file__), "admins_credentials.csv"),
    "admins_credentials.csv",
    "../admins_credentials.csv",
]

csv_file = None
for p in csv_paths:
    if os.path.exists(p):
        csv_file = p
        break

if csv_file:
    print(f"\n--- Seeding from {csv_file} ---")
    with open(csv_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            role_str = (row.get("Role") or "").strip()
            full_name = (row.get("Full Name") or "").strip()
            username = (row.get("Username") or "").strip()
            email = (row.get("Email") or "").strip()
            password = (row.get("Default Password") or "").strip()

            if not username or not email:
                continue

            # President and General Committee Head share the High Board account
            if username == "president" or role_str.lower() == "president":
                role_enum = RoleEnum.president
            else:
                role_enum = RoleEnum.committee_admin

            comm_name = COMMITTEES_MAP.get(full_name, "General Committee")
            comm = db.query(Committee).filter_by(name=comm_name).first()
            comm_id = comm.id if comm else general_comm_id

            # Look up existing user by username first to avoid duplicate email clash
            user = db.query(User).filter(User.username == username).first()
            if not user:
                # Check if another user already has this email (e.g. shared General Committee email)
                email_user = db.query(User).filter(User.email == email).first()
                if email_user and email_user.username != username:
                    print(f"  [Notice] Email '{email}' is shared by {email_user.username}; keeping {email_user.username}")
                    continue

                user = User(
                    full_name=full_name,
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role=role_enum,
                    committee_id=comm_id,
                )
                db.add(user)
                print(f"  [OK] Created {role_str}: {username} ({email}) | Password: {password}")
            else:
                user.full_name = full_name
                user.email = email
                user.password_hash = hash_password(password)
                user.role = role_enum
                user.committee_id = comm_id
                print(f"  [OK] Updated {role_str}: {username} ({email}) | Password: {password}")

    db.commit()
else:
    print("admins_credentials.csv not found.")

db.close()
print("\nSeed completed successfully.")
