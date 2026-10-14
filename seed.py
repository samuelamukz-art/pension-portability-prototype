from datetime import datetime, timedelta  # noqa: I001
import uuid

from app import security
from app.main import SessionLocal, engine
from app.models import Base, Consent, Contribution, Institution, Member, TransferRequest

Base.metadata.create_all(engine)
db = SessionLocal()

try:
    # Keep the demo and administrator accounts available for local development.
    demo_member = db.query(Member).get("M001")
    if not demo_member:
        db.add(Member(
            id="M001",
            full_name="Samuel Amukusana",
            national_id_hash=security.tokenize_national_id("NID1"),
            password_hash=security.hash_password("demo1234"),
            is_admin=False,
        ))
    else:
        demo_member.full_name = "Samuel Amukusana"
        demo_member.is_admin = False

    admin = db.query(Member).get("ADMIN")
    if not admin:
        db.add(Member(
            id="ADMIN",
            full_name="Platform Administrator",
            national_id_hash=security.tokenize_national_id("ADMIN-NID"),
            password_hash=security.hash_password("admin1234"),
            is_admin=True,
        ))

    for member_id, password in (("M001", "demo1234"), ("ADMIN", "admin1234")):
        member = db.query(Member).get(member_id)
        if member and not security.verify_password(password, member.password_hash):
            member.password_hash = security.hash_password(password)

    # Add 100 deterministic synthetic accounts. Re-running the seed is safe:
    # existing records and their passwords are left intact.
    first_names = [
        "Avery", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Cameron",
        "Quinn", "Jamie", "Drew", "Reese", "Skyler", "Parker", "Rowan",
        "Emerson", "Finley", "Harper", "Kendall", "Logan", "Payton",
    ]
    last_names = [
        "Adams", "Bennett", "Carter", "Diaz", "Ellis", "Foster", "Garcia",
        "Hayes", "Ibrahim", "Jones", "Kim", "Lopez", "Morris", "Nguyen",
        "Owens", "Patel", "Reed", "Singh", "Turner", "Wilson",
    ]
    synthetic_password_hash = security.hash_password("Synthetic123!")
    for number in range(1, 101):
        member_id = f"SYN{number:04d}"
        if db.query(Member).get(member_id):
            continue
        first_name = first_names[(number - 1) % len(first_names)]
        last_name = last_names[((number - 1) // len(first_names)) % len(last_names)]
        db.add(Member(
            id=member_id,
            full_name=f"{first_name} {last_name}",
            national_id_hash=security.tokenize_national_id(f"SYNTHETIC-NID-{number:04d}"),
            password_hash=synthetic_password_hash,
            is_admin=False,
        ))

    for iid, name in [("INS-A", "Alpha Pension"), ("INS-B", "Beta Retirement"), ("INS-C", "Gamma Fund")]:
        if not db.query(Institution).get(iid):
            db.add(Institution(id=iid, name=name, api_base=f"https://mock/{iid}", public_key="demo-pub"))

    db.flush()

    # Give each synthetic profile varied, repeatable dashboard activity.
    for number in range(1, 101):
        member_id = f"SYN{number:04d}"
        contribution_total = 1 + number % 5
        for index in range(contribution_total):
            record_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"pension-demo:{member_id}:contribution:{index}"))
            if db.query(Contribution).get(record_id):
                continue
            institution_id = ("INS-A", "INS-B", "INS-C")[(number + index) % 3]
            month_offset = (number + index) % 24
            year, month_index = divmod((2026 * 12 + 9) - month_offset, 12)
            db.add(Contribution(
                id=record_id,
                member_id=member_id,
                institution_id=institution_id,
                employer_id=f"EMP-{1 + (number + index) % 3}",
                period=f"{year:04d}-{month_index + 1:02d}",
                amount=float(120 + ((number * 37 + index * 53) % 1881)),
                currency="USD",
                contribution_type=("employee", "employer", "voluntary")[(number + index) % 3],
                source_hash=security.tokenize_national_id(f"SYNTHETIC-CONTRIBUTION-{member_id}-{index}"),
            ))

        for index in range(1 + number % 3):
            record_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"pension-demo:{member_id}:consent:{index}"))
            if db.query(Consent).get(record_id):
                continue
            db.add(Consent(
                id=record_id,
                member_id=member_id,
                institution_id=("INS-A", "INS-B", "INS-C")[(number + index) % 3],
                scope="read:contributions",
                expires_at=datetime.utcnow() + timedelta(days=365),  # noqa: DTZ003
                revoked=False,
            ))

        for index in range(1 + number % 2):
            record_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"pension-demo:{member_id}:transfer:{index}"))
            if db.query(TransferRequest).get(record_id):
                continue
            from_institution = ("INS-A", "INS-B", "INS-C")[(number + index) % 3]
            to_institution = ("INS-A", "INS-B", "INS-C")[(number + index + 1) % 3]
            db.add(TransferRequest(
                id=record_id,
                member_id=member_id,
                from_institution=from_institution,
                to_institution=to_institution,
                status=("PENDING", "COMPLETED", "APPROVED")[(number + index) % 3],
            ))

    db.commit()
finally:
    db.close()

print("Seeded 100 synthetic member accounts. Synthetic login password: Synthetic123!")
print("Demo login: M001 / demo1234")
