import hashlib
from sqlalchemy.orm import Session
from .models import Contribution, Consent, Institution
from .mock_institutions import fetch_contributions

def _source_hash(c: dict) -> str:
    key = f"{c['institution_id']}|{c['member_id']}|{c['period']}|{c['amount']}|{c['contribution_type']}"
    return hashlib.sha256(key.encode()).hexdigest()

def consolidate(db: Session, member_id: str):
    institutions = db.query(Institution).filter(Institution.active == True).all()
    inserted, skipped = 0, 0
    for inst in institutions:
        # Enforce consent check (security)
        consent = (db.query(Consent)
                   .filter(Consent.member_id == member_id,
                           Consent.institution_id == inst.id,
                           Consent.revoked == False)
                   .first())
        if not consent:
            continue
        for raw in fetch_contributions(inst.id, member_id):
            sh = _source_hash(raw)
            exists = db.query(Contribution).filter(Contribution.source_hash == sh).first()
            if exists:
                skipped += 1
                continue
            db.add(Contribution(
                id=raw["id"], member_id=raw["member_id"],
                institution_id=raw["institution_id"], employer_id=raw["employer_id"],
                period=raw["period"], amount=raw["amount"], currency=raw["currency"],
                contribution_type=raw["contribution_type"], source_hash=sh,
            ))
            inserted += 1
    db.commit()
    return {"inserted": inserted, "duplicates_skipped": skipped}