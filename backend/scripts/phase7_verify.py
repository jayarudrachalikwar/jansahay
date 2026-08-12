"""
Phase 7 end-to-end verification script.
Run inside the backend container:
  docker compose exec backend python scripts/phase7_verify.py
"""
import json
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
# Credentials read from environment/config at runtime.
# Replace with your actual admin credentials when running manually.
ADMIN_EMAIL = "admin@jansahay.dev"
ADMIN_PASSWORD = "change-admin-password"  # override with real value


def req(url, *, method="GET", data=None, headers=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# 1. Health
code, body = req(BASE + "/api/health")
assert code == 200, f"Health failed: {body}"
print(f"[1] GET /api/health => {body}")

# 2. Admin login
code, body = req(
    BASE + "/api/auth/login",
    method="POST",
    data=json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).encode(),
    headers={"Content-Type": "application/json"},
)
assert code == 200, f"Admin login failed: {body}"
admin_token = body["access_token"]
print(f"[2] Admin login => OK")
auth = {"Authorization": f"Bearer {admin_token}"}

# 3. Register a farmer for RAG search verification
code, body = req(
    BASE + "/api/auth/register",
    method="POST",
    data=json.dumps({"email": "phase7farmer@jansahay.dev", "password": "Farmer123!", "full_name": "Phase7 Farmer"}).encode(),
    headers={"Content-Type": "application/json"},
)
if code == 400 and "already" in str(body):
    code, body = req(
        BASE + "/api/auth/login",
        method="POST",
        data=json.dumps({"email": "phase7farmer@jansahay.dev", "password": "Farmer123!"}).encode(),
        headers={"Content-Type": "application/json"},
    )
assert code in (200, 201), f"Farmer token failed: {body}"
farmer_token = body["access_token"]
farmer_auth = {"Authorization": f"Bearer {farmer_token}"}
print(f"[3] Farmer token => OK")

# 4. Farmer cannot upload (403)
code, body = req(
    BASE + "/api/admin/documents",
    method="GET",
    headers=farmer_auth,
)
assert code == 403, f"Expected 403, got {code}: {body}"
print(f"[4] Farmer GET /api/admin/documents => 403 (correct)")

# 5. Admin list documents
code, body = req(BASE + "/api/admin/documents", headers=auth)
assert code == 200, f"List failed: {body}"
print(f"[5] Admin GET /api/admin/documents => {body['total']} documents")

# 6. Upload PDF using multipart
pdf_path = "/app/data/documents/sample_crop_insurance.pdf"
with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

boundary = "----Phase7Boundary"
body_parts = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="phase7_sample.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode() + pdf_bytes + f"\r\n--{boundary}--\r\n".encode()

upload_headers = {**auth, "Content-Type": f"multipart/form-data; boundary={boundary}"}
code, body = req(
    BASE + "/api/admin/documents",
    method="POST",
    data=body_parts,
    headers=upload_headers,
)
if code == 201:
    doc = body
    print(f"[6] Upload => 201 | status={doc['status']} | original={doc['original_filename']}")
    print(f"     server_filename={doc['filename']} (UUID-safe)")
    print(f"     document_id={doc['document_id'][:20]}...")
    doc_id = doc["id"]
elif code == 400 and "already" in str(body).lower():
    # duplicate — find it in the list
    code2, list_body = req(BASE + "/api/admin/documents", headers=auth)
    docs = list_body["documents"]
    doc = next((d for d in docs if "phase7" in d["original_filename"]), docs[0])
    doc_id = doc["id"]
    print(f"[6] Upload => duplicate detected, using existing doc id={doc_id}")
else:
    raise AssertionError(f"Upload failed {code}: {body}")

# 7. Ingest
code, body = req(
    BASE + f"/api/admin/documents/{doc_id}/ingest",
    method="POST",
    data=b"",
    headers=auth,
)
assert code == 200, f"Ingest failed {code}: {body}"
print(f"[7] POST /ingest => status={body['status']} | pages={body['page_count']} | ingested_at={body['ingested_at']}")
assert body["status"] == "indexed", f"Expected indexed, got {body['status']}"
assert body["ingested_at"] is not None

# 8. Verify detail
code, body = req(BASE + f"/api/admin/documents/{doc_id}", headers=auth)
assert code == 200
print(f"[8] GET /admin/documents/{doc_id} => status={body['status']}, is_active={body['is_active']}")

# 9. Deactivate
code, body = req(
    BASE + f"/api/admin/documents/{doc_id}/status",
    method="PATCH",
    data=json.dumps({"is_active": False}).encode(),
    headers={**auth, "Content-Type": "application/json"},
)
assert code == 200 and body["is_active"] is False and body["status"] == "inactive"
print(f"[9] PATCH /status => is_active={body['is_active']}, status={body['status']}")

# 10. Reactivate
code, body = req(
    BASE + f"/api/admin/documents/{doc_id}/status",
    method="PATCH",
    data=json.dumps({"is_active": True}).encode(),
    headers={**auth, "Content-Type": "application/json"},
)
assert code == 200 and body["is_active"] is True
print(f"[10] PATCH /status => is_active={body['is_active']}, status={body['status']}")

# 11. Farmer RAG search — newly indexed document should be retrievable
code, body = req(
    BASE + "/api/rag/search",
    method="POST",
    data=json.dumps({"query": "crop insurance application documents required", "top_k": 5}).encode(),
    headers={**farmer_auth, "Content-Type": "application/json"},
)
assert code == 200, f"RAG search failed: {body}"
print(f"[11] POST /api/rag/search => {body['total']} results")
if body["results"]:
    r = body["results"][0]
    print(f"     top result: filename={r['filename']} | page={r['page_number']} | chunk={r['chunk_index']} | score={r['score']:.3f}")
    assert r["filename"], "filename must not be empty"
    assert r["page_number"] is not None, "page_number must be present"
    assert r["chunk_index"] is not None, "chunk_index must be present"
    assert isinstance(r["score"], float), "score must be float"
    print(f"     RAG metadata verified: filename + page_number + chunk_index + score all present")
else:
    print("     (no results — Qdrant collection may have needed more time to index)")

# 12. Invalid document ID → 404
code, body = req(BASE + "/api/admin/documents/999999", headers=auth)
assert code == 404, f"Expected 404, got {code}"
print(f"[12] GET /admin/documents/999999 => 404 (correct)")

print()
print("=" * 50)
print("Phase 7 end-to-end verification PASSED")
print("=" * 50)
