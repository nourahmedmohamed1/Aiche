"""
import_members.py — Import or update members & committee admins from a CSV file.

CSV Columns Required:
  - full_name
  - username
  - email
  - role            (either 'committee_admin' or 'member')
  - committee_name  (e.g., 'Web Development', 'PR', 'Marketing', etc.)
"""

import csv
from app.database import SessionLocal
from app.models.user import User, Committee, RoleEnum
from app.dependencies import hash_password

db = SessionLocal()

print("Processing members.csv...\n")

try:
    with open("members.csv", mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row["full_name"].strip()
            username = row["username"].strip()
            email = row["email"].strip()
            role_str = row["role"].strip()
            comm_name = row["committee_name"].strip()

            # 1. Match committee in database
            committee = db.query(Committee).filter_by(name=comm_name).first()
            if not committee:
                print(f"  [X] Warning: Committee '{comm_name}' not found for user '{full_name}'. Skipping.")
                continue

            # 2. Parse role enum
            try:
                role_enum = RoleEnum(role_str)
            except ValueError:
                print(f"  [X] Warning: Invalid role '{role_str}' for user '{full_name}'. Skipping.")
                continue

            # 3. Find existing user by email or username
            user = db.query(User).filter(
                (User.email == email) | (User.username == username)
            ).first()

            if user:
                # Update existing user profile with real details from CSV
                user.full_name = full_name
                user.role = role_enum
                user.committee_id = committee.id
                print(f"  [OK] Updated existing user: '{username}' -> Role: {role_str} | Committee: {comm_name}")
            else:
                # Create new user with default initial password
                new_user = User(
                    full_name=full_name,
                    username=username,
                    email=email,
                    password_hash=hash_password("Welcome123!"),  # Default password
                    role=role_enum,
                    committee_id=committee.id
                )
                db.add(new_user)
                print(f"  [OK] Created new user: '{username}' -> Role: {role_str} | Committee: {comm_name}")

    db.commit()
    print("\nBulk import completed successfully!")
except FileNotFoundError:
    print("  [X] Error: 'members.csv' not found in the backend folder. Please place 'members.csv' in backend/ and try again.")
finally:
    db.close()