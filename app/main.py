# pyright: reportMissingImports=false

import uuid
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, func, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from . import aggregation, audit, models, risk, schemas, security
from .models import Base

engine = create_engine("sqlite:///./prototype.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# create_all creates new tables but does not add columns to existing SQLite DBs.
if "is_admin" not in {column["name"] for column in inspect(engine).get_columns("members")}:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE members ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))

app = FastAPI(title="Pension Portability Prototype", version="1.0.0")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def auth(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    try:
        return security.decode_token(authorization.split()[1])
    except ValueError:
        raise HTTPException(401, "invalid token")

def admin_required(me: str = Depends(auth), db: Session = Depends(get_db)) -> str:  # noqa: B008
    member = db.query(models.Member).get(me)
    if not member or not member.is_admin:
        raise HTTPException(403, "admin privileges required")
    return me

# ---------- Auth ----------
@app.post("/api/v1/auth/register")
def register(member_id: str, full_name: str, national_id: str, password: str, db: Session = Depends(get_db)):  # noqa: B008
    if db.query(models.Member).get(member_id):
        raise HTTPException(400, "member exists")
    db.add(models.Member(id=member_id, full_name=full_name,
                         national_id_hash=security.tokenize_national_id(national_id),
                         password_hash=security.hash_password(password)))
    db.commit()
    audit.log(db, member_id, "REGISTER", {"member_id": member_id})
    return {"member_id": member_id}

@app.post("/api/v1/auth/login")
def login(member_id: str, password: str, db: Session = Depends(get_db)):  # noqa: B008
    m = db.query(models.Member).get(member_id)
    if not m or not security.verify_password(password, m.password_hash):
        raise HTTPException(401, "bad credentials")
    audit.log(db, member_id, "LOGIN", {"member_id": member_id})
    return {"access_token": security.make_token(member_id), "token_type": "bearer"}

# ---------- Institutions ----------
@app.get("/api/v1/institutions")
def list_institutions(db: Session = Depends(get_db), _: str = Depends(auth)):  # noqa: B008
    return [{"id": i.id, "name": i.name, "active": i.active}
            for i in db.query(models.Institution).all()]

# ---------- Consent ----------
@app.post("/api/v1/members/consent")
def grant_consent(body: schemas.ConsentIn, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    if body.member_id != me:
        raise HTTPException(403, "cannot consent for another member")
    # If an active consent already exists for this institution, return it
    existing = (db.query(models.Consent)
                  .filter(models.Consent.member_id == body.member_id,
                          models.Consent.institution_id == body.institution_id,
                          models.Consent.revoked == False)
                  .first())
    if existing:
        return {"consent_id": existing.id, "status": "already_granted"}
    c = models.Consent(id=str(uuid.uuid4()), member_id=body.member_id,
                       institution_id=body.institution_id, scope=body.scope,
                       expires_at=body.expires_at or (datetime.utcnow() + timedelta(days=365)))  # noqa: DTZ003
    db.add(c); db.commit()
    audit.log(db, me, "CONSENT_GRANTED", {"institution_id": body.institution_id})
    return {"consent_id": c.id, "status": "granted"}

@app.delete("/api/v1/members/consent/{consent_id}")
def revoke_consent(consent_id: str, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    c = db.query(models.Consent).get(consent_id)
    if not c or c.member_id != me:
        raise HTTPException(404, "consent not found")
    c.revoked = True; db.commit()
    audit.log(db, me, "CONSENT_REVOKED", {"consent_id": consent_id})
    return {"status": "revoked"}

# ---------- Consent list ----------
@app.get("/api/v1/members/{member_id}/consents")
def list_consents(member_id: str, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    if member_id != me:
        raise HTTPException(403, "cannot read another member's consents")
    rows = (db.query(models.Consent)
              .filter(models.Consent.member_id == member_id)
              .order_by(models.Consent.granted_at.desc())
              .all())
    return [
        {
            "id": c.id,
            "institution_id": c.institution_id,
            "scope": c.scope,
            "granted_at": c.granted_at,
            "expires_at": c.expires_at,
            "revoked": c.revoked,
        }
        for c in rows
    ]

# ---------- Contributions (standard API) ----------
@app.post("/api/v1/contributions")
def submit_contribution(body: schemas.ContributionIn, db: Session = Depends(get_db), _: str = Depends(auth)):  # noqa: B008
    sh = aggregation._source_hash(body.model_dump())
    if db.query(models.Contribution).filter(models.Contribution.source_hash == sh).first():
        return {"status": "duplicate_ignored"}
    db.add(models.Contribution(
        id=str(uuid.uuid4()), member_id=body.member_id, institution_id=body.institution_id,
        employer_id=body.employer_id, period=body.period, amount=body.amount,
        currency=body.currency, contribution_type=body.contribution_type, source_hash=sh))
    db.commit()
    audit.log(db, body.member_id, "CONTRIBUTION_SUBMITTED", body.model_dump())
    return {"status": "accepted"}

@app.get("/api/v1/members/{member_id}/contributions")
def get_contributions(member_id: str, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    if member_id != me:
        raise HTTPException(403, "cannot read another member's data")
    result = aggregation.consolidate(db, member_id)
    rows = db.query(models.Contribution).filter(models.Contribution.member_id == member_id).all()
    audit.log(db, me, "CONTRIBUTIONS_READ", {"count": len(rows)})
    return {"consolidation": result,
            "total": sum(r.amount for r in rows),
            "contributions": [
                {"id": r.id, "institution_id": r.institution_id, "employer_id": r.employer_id,
                 "period": r.period, "amount": r.amount, "currency": r.currency,
                 "contribution_type": r.contribution_type} for r in rows
            ]}

# ---------- Transfers (employment transition) ----------
@app.post("/api/v1/transfers")
def create_transfer(body: schemas.TransferIn, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    if body.member_id != me:
        raise HTTPException(403, "cannot transfer for another member")
    t = models.TransferRequest(id=str(uuid.uuid4()), member_id=body.member_id,
                               from_institution=body.from_institution,
                               to_institution=body.to_institution, status="PENDING")
    db.add(t); db.commit()
    audit.log(db, me, "TRANSFER_REQUESTED", body.model_dump())
    return {"transfer_id": t.id, "status": t.status}

@app.get("/api/v1/transfers/{transfer_id}")
def get_transfer(transfer_id: str, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    t = db.query(models.TransferRequest).get(transfer_id)
    if not t or t.member_id != me:
        raise HTTPException(404, "not found")
    return {"transfer_id": t.id, "status": t.status,
            "from": t.from_institution, "to": t.to_institution}

# ---------- Transfers list ----------
@app.get("/api/v1/members/{member_id}/transfers")
def list_transfers(member_id: str, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    if member_id != me:
        raise HTTPException(403, "cannot read another member's transfers")
    rows = (db.query(models.TransferRequest)
              .filter(models.TransferRequest.member_id == member_id)
              .order_by(models.TransferRequest.created_at.desc())
              .all())
    return [
        {
            "id": t.id,
            "from_institution": t.from_institution,
            "to_institution": t.to_institution,
            "status": t.status,
            "created_at": t.created_at,
        }
        for t in rows
    ]

# ---------- Risk & Sustainability (AI dashboard feed) ----------
@app.get("/api/v1/risk/fund/{fund_id}", response_model=schemas.RiskOut)
def risk_for_fund(fund_id: str, db: Session = Depends(get_db), _: str = Depends(auth)):  # noqa: B008
    rows = db.query(models.Contribution).filter(models.Contribution.institution_id == fund_id).all()
    data = [{"amount": r.amount, "institution_id": r.institution_id, "employer_id": r.employer_id}
            for r in rows]
    return risk.score_fund(data)

@app.get("/api/v1/risk/member/{member_id}", response_model=schemas.RiskOut)
def risk_for_member(member_id: str, db: Session = Depends(get_db), me: str = Depends(auth)):  # noqa: B008
    if member_id != me:
        raise HTTPException(403, "forbidden")
    rows = db.query(models.Contribution).filter(models.Contribution.member_id == member_id).all()
    data = [{"amount": r.amount, "institution_id": r.institution_id, "employer_id": r.employer_id}
            for r in rows]
    return risk.score_fund(data)

# ---------- Audit (regulator read) ----------
@app.get("/api/v1/audit")
def read_audit(db: Session = Depends(get_db), _: str = Depends(auth)):  # noqa: B008
    rows = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(50).all()
    return [{"id": r.id, "actor": r.actor, "action": r.action,
             "entry_hash": r.entry_hash[:16] + "...", "timestamp": r.timestamp} for r in rows]

@app.get("/api/v1/audit/full")
def read_audit_full(db: Session = Depends(get_db), _: str = Depends(auth)):  # noqa: B008
    rows = db.query(models.AuditLog).order_by(models.AuditLog.id.asc()).all()
    return [{"id": r.id, "actor": r.actor, "action": r.action,
             "payload_hash": r.payload_hash, "prev_hash": r.prev_hash,
             "entry_hash": r.entry_hash, "timestamp": r.timestamp} for r in rows]

# ---------- Admin (read-only oversight) ----------
@app.get("/api/v1/admin/summary")
def admin_summary(db: Session = Depends(get_db), _: str = Depends(admin_required)):  # noqa: B008
    return {
        "members": db.query(models.Member).count(),
        "institutions": db.query(models.Institution).count(),
        "consents": db.query(models.Consent).count(),
        "active_consents": db.query(models.Consent).filter(models.Consent.revoked == False).count(),  # noqa: E712
        "transfers": db.query(models.TransferRequest).count(),
        "pending_transfers": db.query(models.TransferRequest).filter(models.TransferRequest.status == "PENDING").count(),  # noqa: E712
        "contributions": db.query(models.Contribution).count(),
        "total_contributions_usd": float(
            db.query(func.coalesce(func.sum(models.Contribution.amount), 0)).scalar()
        ),
    }

@app.get("/api/v1/admin/members")
def admin_members(db: Session = Depends(get_db), _: str = Depends(admin_required)):  # noqa: B008
    members = db.query(models.Member).all()
    out = []
    for member in members:
        contrib_count = db.query(models.Contribution).filter(models.Contribution.member_id == member.id).count()
        consent_count = db.query(models.Consent).filter(
            models.Consent.member_id == member.id,
            models.Consent.revoked == False).count()  # noqa: E712
        transfer_count = db.query(models.TransferRequest).filter(
            models.TransferRequest.member_id == member.id).count()
        out.append({
            "id": member.id,
            "full_name": member.full_name,
            "is_admin": bool(member.is_admin),
            "created_at": member.created_at,
            "contributions": contrib_count,
            "active_consents": consent_count,
            "transfers": transfer_count,
        })
    return out

@app.get("/api/v1/admin/consents")
def admin_consents(db: Session = Depends(get_db), _: str = Depends(admin_required)):  # noqa: B008
    rows = db.query(models.Consent).order_by(models.Consent.granted_at.desc()).all()
    return [{
        "id": consent.id,
        "member_id": consent.member_id,
        "institution_id": consent.institution_id,
        "scope": consent.scope,
        "granted_at": consent.granted_at,
        "expires_at": consent.expires_at,
        "revoked": consent.revoked,
    } for consent in rows]

@app.get("/api/v1/admin/transfers")
def admin_transfers(db: Session = Depends(get_db), _: str = Depends(admin_required)):  # noqa: B008
    rows = db.query(models.TransferRequest).order_by(models.TransferRequest.created_at.desc()).all()
    return [{
        "id": transfer.id,
        "member_id": transfer.member_id,
        "from_institution": transfer.from_institution,
        "to_institution": transfer.to_institution,
        "status": transfer.status,
        "created_at": transfer.created_at,
    } for transfer in rows]

# ---------- UI ----------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def ui():
    return FileResponse("static/index.html")

@app.get("/admin")
def admin_ui():
    return FileResponse("static/admin-login.html")

@app.get("/admin/login")
def admin_login_ui():
    return FileResponse("static/admin-login.html")

@app.get("/admin/dashboard")
def admin_dashboard_ui():
    return FileResponse("static/admin.html")
