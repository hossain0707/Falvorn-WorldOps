"""Persistence model: transactional world-state and immutable append-only audit/events."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

def uuid(): return str(uuid4())
def utcnow(): return datetime.now(timezone.utc)

class World(Base):
    __tablename__ = 'worlds'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario: Mapped[str] = mapped_column(String(24), default='town', nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='paused', nullable=False)
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    turn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    policies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class Agent(Base):
    __tablename__ = 'agents'
    __table_args__ = (UniqueConstraint('world_id', 'name'), CheckConstraint('credits >= 0'), CheckConstraint('energy >= 0 AND energy <= 100'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    world_id: Mapped[str] = mapped_column(ForeignKey('worlds.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(90), nullable=False)
    persona: Mapped[str] = mapped_column(Text, default='', nullable=False)
    provider: Mapped[str] = mapped_column(String(24), default='heuristic', nullable=False)
    model: Mapped[str] = mapped_column(String(100), default='heuristic-v1', nullable=False)
    location: Mapped[str] = mapped_column(String(24), default='Commons', nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    trust: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    turns_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str] = mapped_column(ForeignKey('worlds.id', ondelete='CASCADE'), index=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
    turn: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(36), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

Index('ix_events_world_id_id', Event.world_id, Event.id)

class Memory(Base):
    __tablename__ = 'memories'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    world_id: Mapped[str] = mapped_column(ForeignKey('worlds.id', ondelete='CASCADE'), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    trust: Mapped[str] = mapped_column(String(20), default='verified', nullable=False)
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey('events.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class Proposal(Base):
    __tablename__ = 'proposals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    world_id: Mapped[str] = mapped_column(ForeignKey('worlds.id', ondelete='CASCADE'), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='open', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class Vote(Base):
    __tablename__ = 'votes'
    __table_args__ = (UniqueConstraint('proposal_id', 'agent_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey('proposals.id', ondelete='CASCADE'))
    agent_id: Mapped[str] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'))
    decision: Mapped[str] = mapped_column(String(8), nullable=False)

class Approval(Base):
    __tablename__ = 'approvals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    world_id: Mapped[str] = mapped_column(ForeignKey('worlds.id', ondelete='CASCADE'), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'))
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(18), default='pending', nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Idempotency(Base):
    __tablename__ = 'idempotency'
    __table_args__ = (UniqueConstraint('world_id', 'key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid)
    world_id: Mapped[str] = mapped_column(ForeignKey('worlds.id', ondelete='CASCADE'))
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
