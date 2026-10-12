import hashlib, json
from sqlalchemy.orm import Session
from .models import AuditLog

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def log(db: Session, actor: str, action: str, payload: dict):
    prev = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = prev.entry_hash if prev else "GENESIS"
    payload_hash = _hash(json.dumps(payload, sort_keys=True, default=str))
    entry_hash = _hash(prev_hash + actor + action + payload_hash)
    db.add(AuditLog(actor=actor, action=action, payload_hash=payload_hash,
                    prev_hash=prev_hash, entry_hash=entry_hash))
    db.commit()