"""
Phase 10 end-to-end verification script.

Run inside the backend container:
  docker compose exec backend python scripts/phase10_verify.py

Credentials are read from application settings — no hard-coded secrets.
Test-created schemes are deleted in cleanup.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"

sys.path.insert(0, "/app")
from app.core.config import settings  # noqa: E402

ADMIN_EMAIL = settings.admin_email
ADMIN_PASSWORD = settings.admin_password

created_scheme_ids: list[int] = []


def req(url, *, method="GET", data=None, headers=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        resp = urllib.request.urlopen(r)
        body = resp.read()
        return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, json.loads(body) if body else {}


def ok(step, code, body, expected=200):
    if code != expected:
        print(f"  FAIL [{step}] expected HTTP {expected}, got {code}: {body}")
        cleanup()
        sys.exit(1)
    print(f"  OK   [{step}]")
    return body


def jbody(payload):
    return json.dumps(payload).encode()


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def cleanup():
    for sid in list(created_scheme_ids):
        req(BASE + f"/api/admin/schemes/{sid}", method="DELETE", headers=admin_auth)
        created_scheme_ids.remove(sid)


print("=" * 60)
print("Phase 10 E2E Verification")
print("=" * 60)

# 1. Admin login
code, body = req(BASE + "/api/auth/login", method="POST",
                 data=jbody({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}),
                 headers={"Content-Type": "application/json"})
body = ok("1. Admin login", code, body)
admin_auth = auth(body["access_token"])

# 2. Farmer login
code, body = req(BASE + "/api/auth/register", method="POST",
                 data=jbody({"email": "p10e2e@jansahay.internal",
                              "password": "E2E10Farm!",
                              "full_name": "Phase10 Farmer"}),
                 headers={"Content-Type": "application/json"})
if code == 400:
    code, body = req(BASE + "/api/auth/login", method="POST",
                     data=jbody({"email": "p10e2e@jansahay.internal", "password": "E2E10Farm!"}),
                     headers={"Content-Type": "application/json"})
ok("2. Farmer login", code, body, expected=code if code in (200, 201) else 200)
farmer_auth = auth(body["access_token"])
print("  OK   [2. Farmer login]")

# 3. Farmer accessing /api/recommendations without profile → 404
code, body = req(BASE + "/api/recommendations", headers=farmer_auth)
assert code == 404, f"Expected 404 (no profile), got {code}"
print("  OK   [3. /api/recommendations without profile → 404]")

# 4. Admin create a test scheme
scheme_payload = {
    "name": "Phase10 E2E Scheme",
    "short_description": "E2E test scheme.",
    "detailed_description": "Created by phase10_verify.py.",
    "department": "Test Dept",
    "state": "Telangana",
    "scheme_type": "Financial",
    "benefits": "Test benefits.",
    "application_process": "Apply at office.",
    "official_website": None,
    "is_active": True,
    "eligibility_criteria": [],
}
code, body = req(BASE + "/api/admin/schemes", method="POST",
                 data=jbody(scheme_payload), headers=admin_auth)
body = ok("4. Admin create scheme", code, body, expected=201)
scheme_id = body["id"]
created_scheme_ids.append(scheme_id)
print(f"       scheme id={scheme_id}")

# 5. Create farmer profile
profile = {
    "state": "Telangana", "district": "Nalgonda", "village": "TestVillage",
    "gender": "male", "land_size": "3.5", "land_unit": "acres",
    "land_ownership": "owned", "primary_crop": "cotton",
    "secondary_crop": None, "soil_type": "black", "irrigation_type": "canal",
    "farming_type": "traditional", "annual_income": "80000", "date_of_birth": "1985-06-15",
}
code, _ = req(BASE + "/api/profile", method="POST",
              data=jbody(profile), headers=farmer_auth)
assert code in (200, 201), f"Profile creation failed: {code}"
print("  OK   [5. Farmer profile created]")

# 6. GET /api/recommendations now works
code, body = req(BASE + "/api/recommendations", headers=farmer_auth)
ok("6. GET /api/recommendations with profile", code, body)
assert "recommendations" in body
print(f"       {body['total']} recommendations")

# 7. GET /api/recommendations/summary returns ≤5
code, body = req(BASE + "/api/recommendations/summary", headers=farmer_auth)
ok("7. GET /api/recommendations/summary", code, body)
assert len(body["recommendations"]) <= 5
print(f"       {len(body['recommendations'])} summary items (≤5)")

# 8. Existing /api/schemes/recommendations still works
code, body = req(BASE + "/api/schemes/recommendations", headers=farmer_auth)
ok("8. Existing /api/schemes/recommendations unbroken", code, body)

# 9. Farmer saves a scheme
code, body = req(BASE + f"/api/schemes/{scheme_id}/save", method="POST",
                 data=b"", headers=farmer_auth)
ok("9. POST /api/schemes/{id}/save", code, body, expected=201)
assert body["scheme_id"] == scheme_id
assert "saved_at" in body
print(f"       saved record id={body['id']}")

# 10. Farmer duplicate save is idempotent
code, body2 = req(BASE + f"/api/schemes/{scheme_id}/save", method="POST",
                  data=b"", headers=farmer_auth)
assert code in (200, 201), f"Duplicate save should succeed, got {code}"
assert body["id"] == body2["id"], "Duplicate should return same record"
print("  OK   [10. Duplicate save idempotent]")

# 11. GET /api/saved-schemes lists saved scheme
code, body = req(BASE + "/api/saved-schemes", headers=farmer_auth)
ok("11. GET /api/saved-schemes", code, body)
saved_ids = [s["scheme_id"] for s in body["saved_schemes"]]
assert scheme_id in saved_ids
print(f"       {body['total']} saved scheme(s)")

# 12. Another farmer cannot see first farmer's saves
code, body_r = req(BASE + "/api/auth/register", method="POST",
                   data=jbody({"email": "p10e2e2@jansahay.internal",
                                "password": "E2E10Farm2!",
                                "full_name": "Phase10 Farmer2"}),
                   headers={"Content-Type": "application/json"})
if code == 400:
    code, body_r = req(BASE + "/api/auth/login", method="POST",
                       data=jbody({"email": "p10e2e2@jansahay.internal", "password": "E2E10Farm2!"}),
                       headers={"Content-Type": "application/json"})
farmer2_auth = auth(body_r["access_token"])
code, body = req(BASE + "/api/saved-schemes", headers=farmer2_auth)
ok("12. Farmer2 list saved (should be empty)", code, body)
assert scheme_id not in [s["scheme_id"] for s in body["saved_schemes"]]
print("       Farmer2 cannot see Farmer1's saves ✓")

# 13. DELETE /api/schemes/{id}/save — unsave
code, _ = req(BASE + f"/api/schemes/{scheme_id}/save", method="DELETE",
              headers=farmer_auth)
assert code == 204, f"Expected 204, got {code}"
print("  OK   [13. DELETE /api/schemes/{id}/save → 204]")

# 14. After unsave, not in list
code, body = req(BASE + "/api/saved-schemes", headers=farmer_auth)
ok("14. Scheme absent from saved list after unsave", code, body)
assert scheme_id not in [s["scheme_id"] for s in body["saved_schemes"]]

# 15. Unsave non-saved scheme → 404
code, _ = req(BASE + f"/api/schemes/{scheme_id}/save", method="DELETE",
              headers=farmer_auth)
assert code == 404, f"Expected 404, got {code}"
print("  OK   [15. Re-unsave → 404]")

# 16. Farmer accessing /api/admin/farmers → 403
code, _ = req(BASE + "/api/admin/farmers", headers=farmer_auth)
assert code == 403, f"Expected 403, got {code}"
print("  OK   [16. Farmer /api/admin/farmers → 403]")

# 17. RAG search still works
code, body = req(BASE + "/api/rag/search", method="POST",
                 data=jbody({"query": "crop insurance", "top_k": 3}),
                 headers=farmer_auth)
ok("17. RAG search still works", code, body)

cleanup()
print()
print("=" * 60)
print("Phase 10 E2E Verification PASSED — all 17 steps OK")
print("=" * 60)
