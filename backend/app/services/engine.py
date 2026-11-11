"""Transactional turn loop and mandatory action policy. No unapproved real-world side effects."""
from datetime import datetime, timezone
import hashlib
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.domain.models import World, Agent, Event, Memory, Proposal, Vote, Approval, Idempotency
from app.services.seeds import LANDMARKS
from app.services.strategies import DecisionError, heuristic_decision, llm_decision, ALLOWED_ACTIONS

class WorldNotFound(Exception): pass

class WorldConflict(Exception): pass

LOCATIONS = set(LANDMARKS)

def emit(db, world, kind, message, agent=None, detail=None):
    event = Event(world_id=world.id, agent_id=agent.id if agent else None, turn=world.turn,
                  kind=kind, message=message[:1200], detail=detail or {})
    db.add(event)
    db.flush()
    return event

def memory(db, world, agent, event, content, kind='episodic', trust='verified'):
    db.add(Memory(world_id=world.id, agent_id=agent.id, source_event_id=event.id if event else None,
                  content=content[:600], kind=kind, trust=trust))

def _pending_for_agent(db, world_id, agent_id):
    voted = select(Vote.proposal_id).where(Vote.agent_id == agent_id)
    return db.scalars(select(Proposal).where(Proposal.world_id == world_id,
                    Proposal.status == 'open', ~Proposal.id.in_(voted)).order_by(Proposal.created_at).limit(3)).all()

def _record_vote(db, world, agent, proposal, decision):
    if proposal.status != 'open':
        return emit(db, world, 'blocked_action', 'Vote rejected: proposal already closed', agent)
    existing = db.scalar(select(Vote).where(Vote.proposal_id == proposal.id, Vote.agent_id == agent.id))
    if existing:
        return emit(db, world, 'blocked_action', 'Duplicate vote rejected', agent)
    db.add(Vote(proposal_id=proposal.id, agent_id=agent.id, decision=decision))
    db.flush()
    yes = db.scalar(select(func.count()).select_from(Vote).where(Vote.proposal_id == proposal.id, Vote.decision == 'yes')) or 0
    no = db.scalar(select(func.count()).select_from(Vote).where(Vote.proposal_id == proposal.id, Vote.decision == 'no')) or 0
    total = db.scalar(select(func.count()).select_from(Agent).where(Agent.world_id == world.id)) or 1
    if yes > total // 2:
        proposal.status = 'passed'
        # Governance cannot change technical security policy (approval, authorization, allowlist).
        world.policies = list(world.policies) + [{'title': proposal.title, 'text': proposal.text[:200]}]
        emit(db, world, 'policy_passed', proposal.title, agent)
    elif no >= (total + 1) // 2 or yes + no >= total:
        proposal.status = 'rejected'
        emit(db, world, 'policy_rejected', proposal.title, agent)
    return emit(db, world, 'vote', f'{agent.name} voted {decision} on {proposal.title}', agent)

def apply_action(db, world, agent, agents, decision):
    """Every model-proposed action is passed through a deterministic allowlist and validated."""
    action = decision.get('action', '')
    target = (decision.get('target') or '')[:120]
    content = (decision.get('content') or '')[:250]
    if action not in ALLOWED_ACTIONS:
        return emit(db, world, 'blocked_action', f'{agent.name} requested forbidden action: {action[:60]}', agent,
                    {'rejected_action': action[:80]})
    if action == 'move':
        if target not in LOCATIONS:
            return emit(db, world, 'blocked_action', 'Unknown destination rejected', agent)
        agent.location = target
        agent.energy = max(0, agent.energy-3)
        return emit(db, world, 'move', f'{agent.name} traveled to {target}', agent, {'location': target})
    if action == 'rest':
        agent.energy = min(100, agent.energy + 28)
        return emit(db, world, 'rest', f'{agent.name} rested and recovered energy', agent)
    if action == 'work':
        if agent.location not in {'Lab', 'Market'} or agent.energy < 15:
            return emit(db, world, 'blocked_action', 'Work requires a workplace and sufficient energy', agent)
        agent.credits += 9
        agent.energy = max(0, agent.energy - 15)
        return emit(db, world, 'work', f'{agent.name} completed useful work (+9 credits)', agent)
    if action == 'talk':
        peer = next((a for a in agents if a.id == target or a.name == target), None)
        if not peer or peer.id == agent.id or peer.location != agent.location:
            return emit(db, world, 'blocked_action', 'Conversation requires a colocated peer', agent)
        agent.energy = max(0, agent.energy - 3)
        t = dict(agent.trust)
        t[peer.id] = min(100, int(t.get(peer.id, 50)) + 2)
        agent.trust = t
        ev = emit(db, world, 'talk', f'{agent.name} spoke with {peer.name}: {content or "Sharing ideas"}', agent,
                  {'target_agent_id': peer.id})
        memory(db, world, peer, ev, f'{agent.name} told me: {content}', trust='untrusted')
        return ev
    if action == 'reflect':
        agent.energy = max(0, agent.energy-2)
        ev = emit(db, world, 'reflect', f'{agent.name} reflected: {content or "Reviewed experience"}', agent)
        memory(db, world, agent, ev, content or 'Reviewed recent work', kind='reflection')
        return ev
    if action == 'propose':
        if agent.location != 'Hall' or agent.credits < 10:
            return emit(db, world, 'blocked_action', 'Proposals require Hall location and 10 credits', agent)
        if not content.strip():
            return emit(db, world, 'blocked_action', 'Proposal cannot be empty', agent)
        agent.credits -= 10
        proposal = Proposal(world_id=world.id, author_id=agent.id, title='Community proposal', text=content)
        db.add(proposal)
        db.flush()
        return emit(db, world, 'proposal', f'{agent.name} submitted a proposal: {content}', agent,
                    {'proposal_id': proposal.id})
    if action == 'vote':
        if agent.location != 'Hall':
            return emit(db, world, 'blocked_action', 'Voting requires Hall location', agent)
        proposal = db.get(Proposal, target)
        if not proposal or proposal.world_id != world.id:
            return emit(db, world, 'blocked_action', 'Invalid proposal ID', agent)
        decision_vote = 'no' if content.strip().lower() == 'no' else 'yes'
        return _record_vote(db, world, agent, proposal, decision_vote)
    if action == 'request_external':
        # Only declarative outbound payload, never arbitrary URL or unrestricted network access.
        if world.scenario != 'workplace':
            return emit(db, world, 'blocked_action', 'External requests only allowed in workplace worlds', agent)
        if not content.strip():
            return emit(db, world, 'blocked_action', 'External requests need a summary', agent)
        action_type = target or 'publish_summary'
        if action_type not in {'publish_summary', 'create_ticket'}:
            return emit(db, world, 'blocked_action', 'Requested external capability is not allowlisted', agent)
        approval = Approval(world_id=world.id, agent_id=agent.id, action_type=action_type,
                            payload={'summary': content, 'agent': agent.name, 'world_id': world.id})
        db.add(approval)
        db.flush()
        return emit(db, world, 'approval_requested', f'{agent.name} submitted a human-reviewed publication request',
                    agent, {'approval_id': approval.id})
    # observe
    return emit(db, world, 'observe', f'{agent.name} observed current conditions', agent)

def _step_one(db: Session, world: World):
    agents = db.scalars(select(Agent).where(Agent.world_id == world.id).order_by(Agent.created_at, Agent.id)).all()
    if not agents:
        raise WorldConflict('World has no agents')
    agent = agents[world.turn % len(agents)]
    recent = db.scalars(select(Memory).where(Memory.agent_id == agent.id).order_by(Memory.created_at.desc()).limit(12)).all()
    feed = db.scalars(select(Event).where(Event.world_id == world.id, Event.kind == 'external_feed').order_by(Event.id.desc()).limit(3)).all()
    votes = _pending_for_agent(db, world.id, agent.id)
    decision = None
    if agent.provider == 'openai_compatible':
        try:
            decision = llm_decision(world, agent, agents, recent, feed, votes)
        except DecisionError as exc:
            emit(db, world, 'model_fallback', f'{agent.name}: {exc.__class__.__name__}', agent,
                 {'reason': str(exc)[:120]})
        finally:
            # Count attempts and errors, not just successful model responses.
            world.model_calls += 1
    if decision is None:
        decision = heuristic_decision(world, agent, agents, feed, votes)
    world.turn += 1
    world.updated_at = datetime.now(timezone.utc)
    event = apply_action(db, world, agent, agents, decision)
    agent.turns_taken += 1
    if event.kind not in {'blocked_action','model_fallback'} and agent.turns_taken % 3 == 0:
        memory(db, world, agent, event, event.message)
    return {'turn': world.turn, 'agent': agent.name, 'action': event.kind, 'event_id': event.id}

def step_world(world_id: str, count: int=1, idempotency_key: str|None=None):
    """A single DB transaction/row lock gives atomic turn ordering on PostgreSQL."""
    if not 1 <= count <= 20:
        raise ValueError('count must be between 1 and 20')
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= 128:
        raise ValueError('Invalid idempotency key')
    with SessionLocal.begin() as db:
        world = db.scalar(select(World).where(World.id == world_id).with_for_update())
        if world is None:
            raise WorldNotFound(world_id)
        request_fingerprint = hashlib.sha256(str(count).encode('ascii')).hexdigest()
        if idempotency_key:
            existing = db.scalar(select(Idempotency).where(Idempotency.world_id == world_id,
                                                          Idempotency.key == idempotency_key))
            if existing:
                if existing.request_fingerprint != request_fingerprint:
                    raise WorldConflict('Idempotency key already used for a different request')
                return existing.result
        turns = [_step_one(db, world) for _ in range(count)]
        result = {'world_id': world_id, 'turn': world.turn, 'steps': turns}
        if idempotency_key:
            db.add(Idempotency(world_id=world_id, key=idempotency_key, request_fingerprint=request_fingerprint, result=result))
        return result


def manual_action_world(world_id: str, agent_id: str, decision: dict):
    """Atomic operator action uses same policy engine and world row locking as agent turns."""
    with SessionLocal.begin() as db:
        world = db.scalar(select(World).where(World.id == world_id).with_for_update())
        if world is None:
            raise WorldNotFound(world_id)
        agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.world_id == world_id))
        if agent is None:
            raise WorldConflict('Agent not found in this world')
        agents = db.scalars(select(Agent).where(Agent.world_id == world_id)).all()
        world.turn += 1
        world.updated_at = datetime.now(timezone.utc)
        event = apply_action(db, world, agent, agents, decision)
        agent.turns_taken += 1
        return {'id': event.id, 'turn': event.turn, 'agent_id': event.agent_id, 'kind': event.kind,
                'message': event.message, 'detail': event.detail, 'created_at': event.created_at.isoformat()}
