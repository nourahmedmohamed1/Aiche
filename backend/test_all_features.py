import sys
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, RoleEnum, Committee
from app.dependencies import create_access_token

client = TestClient(app)

print("=== STARTING AUTOMATED FEATURE & VERIFICATION TESTS ===")

# 1. Test Auth & Permissions on GET /api/auth/me
db = SessionLocal()
pres = db.query(User).filter_by(role=RoleEnum.president).first()
webdev_head = db.query(User).filter_by(username="webdev_head").first()

pres_token = create_access_token({"user_id": pres.id, "role": pres.role.value})
webdev_token = create_access_token({"user_id": webdev_head.id, "role": webdev_head.role.value})

print("\n1. Testing GET /api/auth/me for President...")
res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {pres_token}"})
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
data = res.json()
assert data["role"] == "president"
assert data["permissions"]["add_course"] == True
assert data["permissions"]["add_workshop"] == True
print("   [OK] President permissions verified!")

pr_head = db.query(User).filter_by(username="pr_head").first()
pr_token = create_access_token({"user_id": pr_head.id, "role": pr_head.role.value})

print("\n2. Testing GET /api/auth/me for PR Head...")
res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {pr_token}"})
assert res.status_code == 200
data = res.json()
assert data["role"] == "committee_admin"
assert data["committee"] == "PR"
assert data["permissions"]["add_course"] == False  # PR Head cannot add courses
assert data["permissions"]["add_workshop"] == True  # PR Head CAN add workshops
print("   [OK] PR Head committee & permissions verified!")

# 2. Test Dashboard Endpoints
print("\n3. Testing GET /api/dashboard/stats...")
res = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {pres_token}"})
assert res.status_code == 200
stats = res.json()
assert "students" in stats and "courses" in stats and "workshops" in stats
print(f"   [OK] Stats returned: {stats}")

print("\n4. Testing GET /api/dashboard/recent-activity...")
res = client.get("/api/dashboard/recent-activity", headers={"Authorization": f"Bearer {pres_token}"})
assert res.status_code == 200
activity = res.json()
assert isinstance(activity, list)
print(f"   [OK] Recent activity returned {len(activity)} items!")

# 3. Test 403 Forbidden Security Guard on Course Creation
print("\n5. Testing 403 Forbidden Guard on POST /api/courses...")
res = client.post(
    "/api/courses/",
    json={"title": "Unauthorized Course", "description": "Should fail"},
    headers={"Authorization": f"Bearer {pr_token}"}
)
assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
print("   [OK] 403 Forbidden correctly returned for unauthorized course creation!")

print("\n6. Testing Authorized Course Creation by President...")
res = client.post(
    "/api/courses/",
    json={"title": "Process Safety Foundations", "description": "Core safety course"},
    headers={"Authorization": f"Bearer {pres_token}"}
)
assert res.status_code == 201, f"Expected 201, got {res.status_code}"
course_data = res.json()
course_id = course_data["id"]
print(f"   [OK] Course created successfully! ID: {course_id}")

# 4. Test Workshop Creation by WebDev Head
print("\n7. Testing Workshop Creation by Web Dev Head...")
res = client.post(
    "/api/workshops/",
    json={"title": "Web Dev Bootcamp", "description": "Learn HTML/CSS/JS"},
    headers={"Authorization": f"Bearer {webdev_token}"}
)
assert res.status_code == 201, f"Expected 201, got {res.status_code}"
workshop_data = res.json()
workshop_id = workshop_data["id"]
print(f"   [OK] Workshop created successfully! ID: {workshop_id}")

# 5. Test Dynamic PNG Certificate Generation
print("\n8. Testing Automated Dynamic PNG Certificate Generation...")
res = client.post(
    "/api/certificates/generate",
    json={"source_type": "course", "source_id": course_id},
    headers={"Authorization": f"Bearer {pres_token}"}
)
assert res.status_code == 201, f"Expected 201, got {res.status_code}"
cert_data = res.json()
assert "static/certificates" in cert_data["pdf_url"]
print(f"   [OK] PNG Certificate generated dynamically: {cert_data['pdf_url']}")

print("\n=== ALL TEST VERIFICATIONS PASSED 100% SUCCESSFULLY! ===")
db.close()
