def test_schema_conformance(client, auth_headers):
    r = client.post("/api/v1/contributions", headers=auth_headers, json={
        "member_id":"M001","institution_id":"INS-A","employer_id":"EMP-1",
        "period":"2025-01","amount":100.0,"currency":"USD","contribution_type":"employee"})
    assert r.status_code == 200
    assert r.json()["status"] in ("accepted","duplicate_ignored")

def test_all_institutions_share_contract(client, auth_headers):
    for inst in ["INS-A","INS-B","INS-C"]:
        r = client.post("/api/v1/members/consent", headers=auth_headers,
                        json={"member_id":"M001","institution_id":inst})
        assert r.status_code == 200
    r = client.get("/api/v1/members/M001/contributions", headers=auth_headers)
    assert r.status_code == 200
    assert "contributions" in r.json()
