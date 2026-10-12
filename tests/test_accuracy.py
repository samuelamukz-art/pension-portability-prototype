def test_dedup_accuracy(client, auth_headers):
    payload = {"member_id":"M001","institution_id":"INS-A","employer_id":"EMP-1",
               "period":"2025-02","amount":250.0,"currency":"USD","contribution_type":"employee"}
    client.post("/api/v1/contributions", headers=auth_headers, json=payload)
    client.post("/api/v1/contributions", headers=auth_headers, json=payload)
    rows = client.get("/api/v1/members/M001/contributions", headers=auth_headers).json()["contributions"]
    matches = [r for r in rows if r["period"]=="2025-02" and r["amount"]==250.0]
    assert len(matches) == 1

def test_total_reconciliation(client, auth_headers):
    data = client.get("/api/v1/members/M001/contributions", headers=auth_headers).json()
    manual = sum(c["amount"] for c in data["contributions"])
    assert abs(manual - data["total"]) < 0.001
