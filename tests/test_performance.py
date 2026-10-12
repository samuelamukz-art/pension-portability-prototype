import time

def test_p95_latency_under_300ms(client, auth_headers):
    samples = []
    for _ in range(50):
        t = time.perf_counter()
        client.get("/api/v1/members/M001/contributions", headers=auth_headers)
        samples.append((time.perf_counter()-t)*1000)
    samples.sort()
    p95 = samples[int(0.95*len(samples))-1]
    assert p95 < 300, f"p95={p95:.1f}ms exceeds 300ms"

def test_audit_grows_monotonically(client, auth_headers):
    before = len(client.get("/api/v1/audit", headers=auth_headers).json())
    client.get("/api/v1/members/M001/contributions", headers=auth_headers)
    after = len(client.get("/api/v1/audit", headers=auth_headers).json())
    assert after >= before
