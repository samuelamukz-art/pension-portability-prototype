def test_requires_token(client):
    assert client.get("/api/v1/members/M001/contributions").status_code == 401

def test_cannot_read_other_member(client, auth_headers):
    assert client.get("/api/v1/members/M999/contributions", headers=auth_headers).status_code == 403

def test_consent_required_for_consolidation(client, auth_headers, fresh_db):
    r = client.get("/api/v1/members/M001/contributions", headers=auth_headers)
    assert r.json()["consolidation"]["inserted"] == 0

def test_revoked_consent_blocks(client, auth_headers):
    c = client.post("/api/v1/members/consent", headers=auth_headers,
                    json={"member_id":"M001","institution_id":"INS-A"}).json()["consent_id"]
    client.delete(f"/api/v1/members/consent/{c}", headers=auth_headers)
    r = client.get("/api/v1/members/M001/contributions", headers=auth_headers)
    assert r.json()["consolidation"]["inserted"] == 0
