import pytest
from fastapi.testclient import TestClient
from app.main import app, SessionLocal, engine
from app.models import Base, Member, Institution
from app import security

@pytest.fixture
def client():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db = SessionLocal()
    db.add(Member(id="M001", full_name="T", national_id_hash="x",
                  password_hash=security.hash_password("p")))
    for iid in ["INS-A","INS-B","INS-C"]:
        db.add(Institution(id=iid, name=iid, api_base="x", public_key="k"))
    db.commit(); db.close()
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    token = client.post("/api/v1/auth/login?member_id=M001&password=p").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def fresh_db(client):
    return client
