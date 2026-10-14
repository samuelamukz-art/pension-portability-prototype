from datetime import datetime

# pyright: reportMissingImports=false
try:
    from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
    from sqlalchemy.orm import declarative_base
except ImportError:  # pragma: no cover - compatibility for older SQLAlchemy installs
    from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
    from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Member(Base):
    __tablename__ = "members"
    id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    national_id_hash = Column(String, nullable=False)   # tokenized
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Institution(Base):
    __tablename__ = "institutions"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    api_base = Column(String, nullable=False)
    public_key = Column(String, nullable=False)
    active = Column(Boolean, default=True)

class Contribution(Base):
    __tablename__ = "contributions"
    id = Column(String, primary_key=True)
    member_id = Column(String, ForeignKey("members.id"), index=True)
    institution_id = Column(String, ForeignKey("institutions.id"))
    employer_id = Column(String)
    period = Column(String)          # YYYY-MM
    amount = Column(Float)
    currency = Column(String, default="USD")
    contribution_type = Column(String)  # employee|employer|voluntary
    timestamp = Column(DateTime, default=datetime.utcnow)
    source_hash = Column(String)     # for dedup

class Consent(Base):
    __tablename__ = "consents"
    id = Column(String, primary_key=True)
    member_id = Column(String, ForeignKey("members.id"), index=True)
    institution_id = Column(String, ForeignKey("institutions.id"))
    scope = Column(String)           # e.g. "read:contributions"
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)

class TransferRequest(Base):
    __tablename__ = "transfers"
    id = Column(String, primary_key=True)
    member_id = Column(String, ForeignKey("members.id"))
    from_institution = Column(String)
    to_institution = Column(String)
    status = Column(String, default="PENDING")  # PENDING|APPROVED|COMPLETED|REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String)
    action = Column(String)
    payload_hash = Column(String)
    prev_hash = Column(String)
    entry_hash = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
