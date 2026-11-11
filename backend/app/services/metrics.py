"""Auditable system-level indicators, not a replication of third-party scores."""
from sqlalchemy import func, select
from app.domain.models import Agent, Event, World, Approval, Proposal, Memory

def gini(values):
    v = sorted(max(0, x) for x in values)
    if not v or sum(v) == 0: return 0.0
    n = len(v)
    return round((2 * sum((i + 1) * x for i, x in enumerate(v))) / (n * sum(v)) - (n+1)/n, 4)

def world_metrics(db, world: World):
    agents = db.scalars(select(Agent).where(Agent.world_id == world.id)).all()
    event_rows = db.execute(select(Event.kind, func.count(Event.id)).where(Event.world_id == world.id).group_by(Event.kind)).all()
    kinds = dict(event_rows)
    approvals = db.execute(select(Approval.status, func.count(Approval.id))
                           .where(Approval.world_id == world.id).group_by(Approval.status)).all()
    proposals = db.execute(select(Proposal.status, func.count(Proposal.id))
                           .where(Proposal.world_id == world.id).group_by(Proposal.status)).all()
    verified = db.scalar(select(func.count()).select_from(Memory).where(Memory.world_id == world.id, Memory.trust == 'verified')) or 0
    untrusted = db.scalar(select(func.count()).select_from(Memory).where(Memory.world_id == world.id, Memory.trust == 'untrusted')) or 0
    return {
        'world_id': world.id, 'turn': world.turn, 'agents': len(agents),
        'average_energy': round(sum(a.energy for a in agents)/max(1,len(agents)), 1),
        'total_credits': sum(a.credits for a in agents), 'credit_gini': gini([a.credits for a in agents]),
        'model_calls': world.model_calls,
        'safety_blocks': kinds.get('blocked_action', 0), 'actions': sum(kinds.values()),
        'conversations': kinds.get('talk', 0), 'work_completed': kinds.get('work', 0),
        'movement': kinds.get('move', 0), 'external_feed_events': kinds.get('external_feed', 0),
        'approved_actions': dict(approvals), 'governance': dict(proposals),
        'verified_memories': verified, 'untrusted_memories': untrusted,
        'event_breakdown': kinds,
    }
