from app import security
from app.main import SessionLocal, engine
from app.models import Base, Institution, Member

Base.metadata.create_all(engine)
db = SessionLocal()

if not db.query(Member).get("M001"):
    db.add(Member(id="M001", full_name="Demo Member",
                  national_id_hash=security.tokenize_national_id("NID1"),
                  password_hash=security.hash_password("demo1234")))

for iid, name in [("INS-A","Alpha Pension"),("INS-B","Beta Retirement"),("INS-C","Gamma Fund")]:
    if not db.query(Institution).get(iid):
        db.add(Institution(id=iid, name=name, api_base=f"https://mock/{iid}", public_key="demo-pub"))

db.commit()
print("Seeded. Login: M001 / demo1234")