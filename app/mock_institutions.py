# Each mock institution returns contributions in the SAME standard schema.
MOCK_DATA = {
    "INS-A": [
        {"id":"c1","member_id":"M001","institution_id":"INS-A","employer_id":"EMP-1",
         "period":"2022-01","amount":300.0,"currency":"USD","contribution_type":"employee"},
        {"id":"c2","member_id":"M001","institution_id":"INS-A","employer_id":"EMP-1",
         "period":"2022-02","amount":300.0,"currency":"USD","contribution_type":"employee"},
    ],
    "INS-B": [
        {"id":"c3","member_id":"M001","institution_id":"INS-B","employer_id":"EMP-2",
         "period":"2023-05","amount":420.0,"currency":"USD","contribution_type":"employee"},
        {"id":"c4","member_id":"M001","institution_id":"INS-B","employer_id":"EMP-2",
         "period":"2023-06","amount":420.0,"currency":"USD","contribution_type":"employer"},
    ],
    "INS-C": [
        {"id":"c5","member_id":"M001","institution_id":"INS-C","employer_id":"EMP-3",
         "period":"2024-09","amount":500.0,"currency":"USD","contribution_type":"employee"},
    ],
}

def fetch_contributions(institution_id: str, member_id: str):
    return [c for c in MOCK_DATA.get(institution_id, []) if c["member_id"] == member_id]