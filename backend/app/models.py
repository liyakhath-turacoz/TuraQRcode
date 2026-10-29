from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_version: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuthSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('tura.users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('tura.users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default='#087e70')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Code(Base):
    __tablename__ = 'codes'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('tura.users.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey('tura.projects.id', ondelete='SET NULL'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20), default='url')
    mode: Mapped[str] = mapped_column(String(10), default='dynamic')
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    design: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_hash: Mapped[str | None] = mapped_column(Text)
    mobile_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code_id: Mapped[str] = mapped_column(ForeignKey('tura.codes.id', ondelete='CASCADE'), index=True)
    channel: Mapped[str] = mapped_column(String(10))
    device: Mapped[str] = mapped_column(String(20))
    referrer: Mapped[str] = mapped_column(String(253), default='Direct')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    __table_args__ = (Index('ix_events_code_created', 'code_id', 'created_at'),)


class BusinessCard(Base):
    __tablename__ = 'business_cards'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('tura.users.id', ondelete='CASCADE'), index=True)
    slug: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(120), default='')
    company: Mapped[str] = mapped_column(String(120), default='')
    email: Mapped[str] = mapped_column(String(254), default='')
    phone: Mapped[str] = mapped_column(String(30), default='')
    website: Mapped[str] = mapped_column(Text, default='')
    color: Mapped[str] = mapped_column(String(7), default='#087e70')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ResetToken(Base):
    __tablename__ = 'reset_tokens'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('tura.users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Audit(Base):
    __tablename__ = 'audit_log'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('tura.users.id', ondelete='SET NULL'))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(254), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
