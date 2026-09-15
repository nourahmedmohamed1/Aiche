"""
seed.py  –  One-time script to create starter data (Section 12.4 of the guide).

Run ONCE after `alembic upgrade head`:
    cd backend
    python seed.py

Creates:
  1. The fixed list of committees from the baseline.
  2. A default President account to bootstrap the system
     (no other admin can be created without a President existing first).

This script is idempotent — safe to run multiple times without duplicating rows.
"""

from app.database import SessionLocal
from app.models.user import Committee, User, RoleEnum
from app.dependencies import hash_password

db = SessionLocal()

# ── 1. Committees (from the baseline's fixed list) ───────────────────────────
COMMITTEES = [
    ("Marketing",        "aiche.marketing@gmail.com"),
    ("OC",               "aiche.oc@gmail.com"),
    ("Technical",        "aiche.technical@gmail.com"),
    ("Web Development",  "aiche.webdevelopment@gmail.com"),
    ("PR",               "aiche.pr@gmail.com"),
    ("QC",               "aiche.qc@gmail.com"),
    ("General Committee","aiche.generalcommittee@gmail.com"),
]

for name, email in COMMITTEES:
    if not db.query(Committee).filter_by(name=name).first():
        db.add(Committee(name=name, login_email=email))
        print(f"  [OK] Created committee: {name}")
    else:
        print(f"  - Committee already exists: {name}")

db.commit()

# ── 2. Default President account ─────────────────────────────────────────────
if not db.query(User).filter_by(role=RoleEnum.president).first():
    db.add(User(
        full_name="Head President",
        username="president",
        email="president@aiche.com",
        password_hash=hash_password("ChangeMe123!"),
        role=RoleEnum.president,
    ))
    db.commit()
    print("  [OK] Created default president account (username: president)")
    print("  IMPORTANT: Log in and change the password immediately!")
else:
    print("  - President account already exists")

# ── 3. Committee Admin (Head) accounts ───────────────────────────────────────
COMMITTEE_ADMINS = [
    ("Marketing Head",        "marketing_head", "marketing.head@aiche.com", "Marketing"),
    ("OC Head",               "oc_head",        "oc.head@aiche.com",        "OC"),
    ("Technical Head",        "technical_head", "technical.head@aiche.com", "Technical"),
    ("Web Development Head",  "webdev_head",    "webdev.head@aiche.com",    "Web Development"),
    ("PR Head",               "pr_head",        "pr.head@aiche.com",        "PR"),
    ("QC Head",               "qc_head",        "qc.head@aiche.com",        "QC"),
]

for full_name, username, email, comm_name in COMMITTEE_ADMINS:
    if not db.query(User).filter_by(username=username).first():
        comm = db.query(Committee).filter_by(name=comm_name).first()
        if comm:
            db.add(User(
                full_name=full_name,
                username=username,
                email=email,
                password_hash=hash_password("AdminPass123!"),
                role=RoleEnum.committee_admin,
                committee_id=comm.id,
            ))
            print(f"  [OK] Created committee admin: {username} ({comm_name})")

db.commit()
db.close()
print("\nSeed complete.")
