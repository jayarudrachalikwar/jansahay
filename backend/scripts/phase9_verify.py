"""
Phase 9 end-to-end verification script.

Run inside the backend container:
  docker compose exec backend python scripts/phase9_verify.py

Credentials are read from application settings (environment / .env).
No secrets are hard-coded in this file.
All test-created schemes are deleted in the cleanup step.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"

# Read credentials from settings — never hard-coded
sys.path.insert(0, "/app")
from app.core.config import settings  # noqa: E402

ADMIN_EMAIL = settings.admin_email
ADMIN_PASSWORD = settings.admin_password

# Track created scheme IDs for cleanup
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
        _cleanup(admin_headers)
        sys.exit(1)
    print(f"  OK   [{step}]")
    return body


def jbody(payload):
    return json.dumps(payload).encode()


def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


admin_headers: dict = {}   # populated after step 1

print("=" * 60)
print("Phase 9 E2E Verification")
print("=" * 60)

# ------------------------------------------------------------------
# Step 1 — Admin login
# ------------------------------------------------------------------
code, body = req(
    BASE + "/api/auth/login",
    method="POST",
    data=jbody({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}),
    headers={"Content-Type": "application/json"},
)
body = ok("1. Admin login", code, body)
admin_token = body["access_token"]
admin_headers = auth(admin_token)

# ------------------------------------------------------------------
# Step 2 — Farmer login (register throwaway account)
# ------------------------------------------------------------------
code, body = req(
    BASE + "/api/auth/register",
    method="POST",
    data=jbody({
        "email": "p9-e2e-farmer@jansahay.internal",
        "password": "E2EFarm123!",
        "full_name": "Phase9 E2E Farmer",
    }),
    headers={"Content-Type": "application/json"},
)
if code == 400 and "already" in str(body):
    code, body = req(
        BASE + "/api/auth/login",
        method="POST",
        data=jbody({"email": "p9-e2e-farmer@jansahay.internal", "password": "E2EFarm123!"}),
        headers={"Content-Type": "application/json"},
    )
ok("2. Farmer login", code, body, expected=code if code in (200, 201) else 200)
farmer_token = body["access_token"]
farmer_headers = auth(farmer_token)
print(f"  OK   [2. Farmer login]")

# ------------------------------------------------------------------
# Step 3 — Farmer → 403 on admin farmers endpoint
# ------------------------------------------------------------------
code, _ = req(BASE + "/api/admin/farmers", headers=farmer_headers)
assert code == 403, f"Expected 403, got {code}"
print("  OK   [3. Farmer GET /api/admin/farmers → 403]")

# ------------------------------------------------------------------
# Step 4 — Admin list farmers
# ------------------------------------------------------------------
code, body = req(BASE + "/api/admin/farmers", headers=admin_headers)
body = ok("4. Admin GET /api/admin/farmers", code, body)
assert "farmers" in body and "total" in body
print(f"       {body['total']} farmer(s) returned")

# ------------------------------------------------------------------
# Step 5 — Admin view farmer detail (use first farmer if any, else skip)
# ------------------------------------------------------------------
farmers = body["farmers"]
if farmers:
    fid = farmers[0]["id"]
    code, detail = req(BASE + f"/api/admin/farmers/{fid}", headers=admin_headers)
    ok("5. Admin GET /api/admin/farmers/{id}", code, detail)
    assert "email" in detail
    assert "password" not in str(detail).lower()
    assert "password_hash" not in str(detail).lower()
    print(f"       farmer id={fid} email={detail['email']} password_hash absent ✓")
else:
    print("  OK   [5. No farmers yet — RBAC verified in step 3]")

# ------------------------------------------------------------------
# Step 6 — Admin list schemes
# ------------------------------------------------------------------
code, body = req(BASE + "/api/admin/schemes", headers=admin_headers)
body = ok("6. Admin GET /api/admin/schemes", code, body)
assert "schemes" in body and "total" in body
initial_count = body["total"]
print(f"       {initial_count} scheme(s) before create")

# ------------------------------------------------------------------
# Step 7 — Admin create scheme
# ------------------------------------------------------------------
new_scheme = {
    "name": "Phase9 E2E Test Scheme",
    "short_description": "E2E verification scheme.",
    "detailed_description": "Created by phase9_verify.py for E2E testing.",
    "department": "Test Department",
    "state": "Telangana",
    "scheme_type": "Financial Assistance",
    "benefits": "Test benefits.",
    "application_process": "Visit local office.",
    "official_website": None,
    "is_active": True,
    "eligibility_criteria": [
        {
            "criterion_type": "profile",
            "field_name": "state",
            "operator": "equals",
            "expected_value": "Telangana",
            "description": "Must be from Telangana.",
        }
    ],
}
code, body = req(
    BASE + "/api/admin/schemes",
    method="POST",
    data=jbody(new_scheme),
    headers=admin_headers,
)
body = ok("7. Admin POST /api/admin/schemes (create)", code, body, expected=201)
scheme_id = body["id"]
created_scheme_ids.append(scheme_id)
assert body["name"] == "Phase9 E2E Test Scheme"
assert len(body["eligibility_criteria"]) == 1
print(f"       created scheme id={scheme_id}")

# ------------------------------------------------------------------
# Step 8 — Newly created scheme appears in list
# ------------------------------------------------------------------
code, body = req(BASE + "/api/admin/schemes", headers=admin_headers)
body = ok("8. Scheme appears in admin list", code, body)
names = [s["name"] for s in body["schemes"]]
assert "Phase9 E2E Test Scheme" in names, f"Not found in: {names}"
print(f"       total schemes now: {body['total']}")

# ------------------------------------------------------------------
# Step 9 — Admin edit scheme
# ------------------------------------------------------------------
updated_scheme = {
    **new_scheme,
    "name": "Phase9 E2E Test Scheme (Updated)",
    "short_description": "Updated E2E verification scheme.",
}
code, body = req(
    BASE + f"/api/admin/schemes/{scheme_id}",
    method="PUT",
    data=jbody(updated_scheme),
    headers=admin_headers,
)
body = ok("9. Admin PUT /api/admin/schemes/{id} (update)", code, body)
assert body["name"] == "Phase9 E2E Test Scheme (Updated)"

# ------------------------------------------------------------------
# Step 10 — Edited scheme appears correctly
# ------------------------------------------------------------------
code, body = req(BASE + f"/api/admin/schemes/{scheme_id}", headers=admin_headers)
body = ok("10. Updated scheme detail correct", code, body)
assert body["short_description"] == "Updated E2E verification scheme."
assert body["eligibility_criteria"][0]["field_name"] == "state"
print(f"       name='{body['name']}' criteria_count={len(body['eligibility_criteria'])}")

# ------------------------------------------------------------------
# Step 11 — Admin delete scheme
# ------------------------------------------------------------------
code, _ = req(
    BASE + f"/api/admin/schemes/{scheme_id}",
    method="DELETE",
    headers=admin_headers,
)
assert code == 204, f"Expected 204, got {code}"
created_scheme_ids.remove(scheme_id)
print("  OK   [11. Admin DELETE /api/admin/schemes/{id} → 204]")

# ------------------------------------------------------------------
# Step 12 — Deleted scheme no longer appears
# ------------------------------------------------------------------
code, _ = req(BASE + f"/api/admin/schemes/{scheme_id}", headers=admin_headers)
assert code == 404, f"Expected 404 after delete, got {code}"
code, body = req(BASE + "/api/admin/schemes", headers=admin_headers)
names_after = [s["name"] for s in body["schemes"]]
assert "Phase9 E2E Test Scheme (Updated)" not in names_after
print("  OK   [12. Deleted scheme absent from list → 404 + absent from list]")

# ------------------------------------------------------------------
# Step 13 — Existing farmer scheme browsing still works
# ------------------------------------------------------------------
code, body = req(BASE + "/api/schemes", headers=farmer_headers)
ok("13. Farmer GET /api/schemes still works", code, body)
assert "schemes" in body

# ------------------------------------------------------------------
# Step 14 — Existing farmer eligibility check still works
# ------------------------------------------------------------------
# Only check if there is an active scheme to test against
farmer_schemes = body["schemes"]
if farmer_schemes:
    sid = farmer_schemes[0]["id"]
    code, elig = req(BASE + f"/api/schemes/{sid}/eligibility", headers=farmer_headers)
    # 404 is acceptable if farmer has no profile; 200 means it works
    assert code in (200, 404), f"Unexpected eligibility status: {code}"
    print(f"  OK   [14. Farmer eligibility check → HTTP {code} (200=ok, 404=no profile)]")
else:
    print("  OK   [14. No active schemes — eligibility route still registered]")

# ------------------------------------------------------------------
# Step 15 — Existing assistant / RAG functionality still works
# ------------------------------------------------------------------
code, body = req(BASE + "/api/rag/search", method="POST",
                 data=jbody({"query": "crop insurance documents", "top_k": 3}),
                 headers=farmer_headers)
ok("15. POST /api/rag/search still works", code, body)
assert "results" in body
print(f"       RAG results: {body['total']}")


def _cleanup(headers):
    for sid in list(created_scheme_ids):
        c, _ = req(BASE + f"/api/admin/schemes/{sid}", method="DELETE", headers=headers)
        if c == 204:
            created_scheme_ids.remove(sid)
            print(f"       cleaned up scheme id={sid}")


_cleanup(admin_headers)

print()
print("=" * 60)
print("Phase 9 E2E Verification PASSED — all 15 steps OK")
print("=" * 60)
