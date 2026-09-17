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
        print(f"  - Committee already exists (updated email): {name}")

db.commit()

# ── 2. Default President account ─────────────────────────────────────────────
if not db.query(User).filter_by(role=RoleEnum.president).first():
    db.add(User(
        full_name="Head President",
        username="president",
        email="AICHECUSCgeneral@gmail.com",
        password_hash=hash_password("AICHECUSCgeneral@2026"),
        role=RoleEnum.president,
    ))
    db.commit()
    print("  [OK] Created default president account (username: president)")
    print("  IMPORTANT: Log in and change the password immediately!")
else:
    pres = db.query(User).filter_by(role=RoleEnum.president).first()
    pres.email = "AICHECUSCgeneral@gmail.com"
    pres.password_hash = hash_password("AICHECUSCgeneral@2026")
    db.commit()
    print("  - President account already exists (updated credentials)")

# ── 3. Committee Admin (Head) accounts ───────────────────────────────────────
COMMITTEE_ADMINS = [
    ("Marketing Head",        "marketing_head", "AIChECU.Marketing@gmail.com",        "Marketing"),
    ("OC Head",               "oc_head",        "AIChECU.OC@gmail.com",               "OC"),
    ("Technical Head",        "technical_head", "AIChECU.Technical@gmail.com",        "Technical"),
    ("Web Development Head",  "webdev_head",    "AIChECU.WebDevelopment@gmail.com",   "Web Development"),
    ("PR Head",               "pr_head",        "aichecu.pr@gmail.com",               "PR"),
    ("QC Head",               "qc_head",        "aiche.cu.qc@gmail.com",              "QC"),
    ("General Committee Head","general_head",   "AICHECUSCgeneral@gmail.com",         "General Committee"),
]

for full_name, username, email, comm_name in COMMITTEE_ADMINS:
    email_name = email.split("@")[0]
    default_pass = f"{email_name}@2026"
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()

    if not existing_user:
        comm = db.query(Committee).filter_by(name=comm_name).first()
        if comm:
            db.add(User(
                full_name=full_name,
                username=username,
                email=email,
                password_hash=hash_password(default_pass),
                role=RoleEnum.committee_admin,
                committee_id=comm.id,
            ))
            print(f"  [OK] Created committee admin: {username} ({comm_name}) | Password: {default_pass}")
    else:
        comm = db.query(Committee).filter_by(name=comm_name).first()
        if comm:
            existing_user.committee_id = comm.id
        existing_user.email = email
        existing_user.password_hash = hash_password(default_pass)
        print(f"  - Updated committee admin: {username} ({comm_name}) | Password: {default_pass}")

db.commit()
db.close()
print("\nSeed complete.")
