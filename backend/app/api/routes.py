"""Versioned REST API. Mutations are authenticated outside local development."""
import secrets
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.config import get_settings
from app.core.database import get_db
from app.domain.models import World, Agent, Event, Memory, Proposal, Vote, Approval
from app.domain.schemas import NewAgent, NewWorld, StepRequest, FeedRequest, ReviewRequest, ManualAction
from app.services.seeds import LANDMARKS, seed_agents
from app.services.metrics import world_metrics
from app.services.engine import WorldNotFound, WorldConflict, emit, step_world, manual_action_world
from app.services.gateway import GatewayError, dispatch_approved

router = APIRouter(prefix='/api/v1')

def auth(request: Request, x_api_key: str | None = Header(default=None)):
    """Server-owned operator identity; callers cannot forge approval reviewer fields."""
    cfg = get_settings()
    if cfg.app_env == 'development' and not cfg.api_key and not cfg.read_only_api_key:
        request.state.actor = 'local-development'
        return 'admin'
    if not x_api_key:
        raise HTTPException(401, 'Missing/invalid API key')
    if cfg.api_key and secrets.compare_digest(x_api_key, cfg.api_key):
        role = 'admin'
    elif cfg.read_only_api_key and secrets.compare_digest(x_api_key, cfg.read_only_api_key):
        role = 'reader'
    else:
        raise HTTPException(401, 'Missing/invalid API key')
    if role == 'reader' and request.method not in {'GET', 'HEAD'}:
        raise HTTPException(403, 'Read-only API key cannot change world state')
    # Stable pseudonymous identity derived from authenticated key, not request JSON.
    request.state.actor = role + '-' + hashlib.sha256(x_api_key.encode()).hexdigest()[:16]
    return role

@router.get('/live')
def live():
    return {'status': 'ok', 'service': 'falvorn-worldops'}

@router.get('/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(func.count()).select_from(World)).scalar()
    return {'status': 'ok', 'service': 'falvorn-worldops', 'version': '0.2.0'}

@router.get('/meta')
def meta(_: None=Depends(auth)):
    cfg = get_settings()
    return {'landmarks': LANDMARKS, 'provider_modes': ['heuristic', 'openai_compatible'],
            'live_model_enabled': bool(cfg.llm_api_key), 'simulation': 'safe-sandbox'}

def world_to_dict(w):
    return {'id': w.id, 'name': w.name, 'scenario': w.scenario, 'status': w.status,
            'turn': w.turn, 'seed': w.seed, 'model_calls': w.model_calls, 'policies': w.policies,
            'created_at': w.created_at.isoformat()}

def agent_to_dict(a):
    return {'id': a.id, 'world_id': a.world_id, 'name': a.name, 'role': a.role,
            'persona': a.persona, 'provider': a.provider, 'model': a.model,
            'location': a.location, 'credits': a.credits, 'energy': a.energy,
            'trust': a.trust, 'turns_taken': a.turns_taken}

def event_to_dict(e):
    return {'id': e.id, 'turn': e.turn, 'agent_id': e.agent_id, 'kind': e.kind,
            'message': e.message, 'detail': e.detail, 'created_at': e.created_at.isoformat()}

def approval_to_dict(a):
    return {'id': a.id, 'agent_id': a.agent_id, 'status': a.status,
            'action_type': a.action_type, 'payload': a.payload, 'reviewer': a.reviewer,
            'external_ref': a.external_ref, 'created_at': a.created_at.isoformat()}

def lookup_world(db, world_id):
    w = db.get(World, world_id)
    if not w:
        raise HTTPException(404, 'World not found')
    return w

@router.get('/worlds')
def list_worlds(db: Session=Depends(get_db), _: None=Depends(auth)):
    return [world_to_dict(w) for w in db.scalars(select(World).order_by(World.created_at.desc()).limit(100)).all()]

@router.post('/worlds', status_code=201)
def create_world(body: NewWorld, db: Session=Depends(get_db), _: None=Depends(auth)):
    w = World(name=body.name, scenario=body.scenario, seed=body.seed, policies=[])
    db.add(w)
    db.flush()
    if body.starter_agents:
        seed_agents(db, w.id)
    emit(db, w, 'world_created', f'{w.name} established in a {w.scenario} sandbox')
    db.commit()
    return world_to_dict(w)

@router.get('/worlds/{world_id}')
def get_world(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    return world_to_dict(lookup_world(db, world_id))

@router.post('/worlds/{world_id}/start')
def start(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    w=lookup_world(db,world_id)
    if not db.scalar(select(Agent).where(Agent.world_id == world_id)):
        raise HTTPException(409, 'Add an agent before starting')
    w.status = 'running'
    emit(db, w, 'world_started', 'World started by operator')
    db.commit()
    return world_to_dict(w)

@router.post('/worlds/{world_id}/pause')
def pause(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    w=lookup_world(db,world_id)
    w.status = 'paused'
    emit(db, w, 'world_paused', 'World paused by operator')
    db.commit()
    return world_to_dict(w)

@router.post('/worlds/{world_id}/steps')
def steps(world_id: str, body: StepRequest, idempotency_key: str | None=Header(default=None), _: None=Depends(auth)):
    try:
        return step_world(world_id, body.count, idempotency_key)
    except WorldNotFound:
        raise HTTPException(404, 'World not found')
    except WorldConflict as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))

@router.get('/worlds/{world_id}/agents')
def agents(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    lookup_world(db, world_id)
    return [agent_to_dict(a) for a in db.scalars(select(Agent).where(Agent.world_id == world_id)
            .order_by(Agent.created_at, Agent.id)).all()]

@router.post('/worlds/{world_id}/agents', status_code=201)
def create_agent(world_id: str, body: NewAgent, db: Session=Depends(get_db), _: None=Depends(auth)):
    w=lookup_world(db,world_id)
    cfg=get_settings()
    if db.scalar(select(func.count()).select_from(Agent).where(Agent.world_id==world_id)) >= cfg.max_agents_per_world:
        raise HTTPException(409, 'Maximum agents exceeded')
    if body.provider == 'openai_compatible' and body.model not in cfg.allowed_models:
        raise HTTPException(422, 'Model not in server allowlist')
    a=Agent(world_id=w.id, **body.model_dump())
    db.add(a)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Agent name already exists in this world')
    emit(db,w,'agent_joined',f'{a.name} joined as {a.role}',a)
    db.commit()
    return agent_to_dict(a)

@router.get('/worlds/{world_id}/agents/{agent_id}/memories')
def agent_memories(world_id: str, agent_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    a=db.get(Agent,agent_id)
    if not a or a.world_id != world_id:
        raise HTTPException(404, 'Agent not found')
    rows = db.scalars(select(Memory).where(Memory.agent_id == agent_id).order_by(Memory.created_at.desc()).limit(80)).all()
    return [{'id':m.id,'kind':m.kind,'trust':m.trust,'content':m.content,'source_event_id':m.source_event_id} for m in rows]

@router.get('/worlds/{world_id}/events')
def events(world_id: str, after: int=Query(default=0,ge=0), limit: int=Query(default=100,ge=1,le=250),
           db: Session=Depends(get_db), _: None=Depends(auth)):
    lookup_world(db,world_id)
    q = select(Event).where(Event.world_id == world_id)
    if after:
        q=q.where(Event.id > after).order_by(Event.id)
    else:
        q=q.order_by(Event.id.desc())
    rows=db.scalars(q.limit(limit)).all()
    return [event_to_dict(e) for e in rows]

@router.get('/worlds/{world_id}/metrics')
def metrics(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    return world_metrics(db, lookup_world(db,world_id))

@router.get('/worlds/{world_id}/proposals')
def proposals(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    lookup_world(db,world_id)
    rows=db.scalars(select(Proposal).where(Proposal.world_id == world_id).order_by(Proposal.created_at.desc())).all()
    return [{'id':p.id,'title':p.title,'text':p.text,'status':p.status,
             'votes_yes':db.scalar(select(func.count()).select_from(Vote).where(Vote.proposal_id == p.id,Vote.decision == 'yes')) or 0,
             'votes_no':db.scalar(select(func.count()).select_from(Vote).where(Vote.proposal_id == p.id,Vote.decision == 'no')) or 0} for p in rows]

@router.post('/worlds/{world_id}/feed', status_code=201)
def inject_feed(world_id: str, body: FeedRequest, db: Session=Depends(get_db), _: None=Depends(auth)):
    w=lookup_world(db,world_id)
    ev=emit(db,w,'external_feed',body.content,detail={'source':body.source, 'trust':'untrusted'})
    db.commit()
    return event_to_dict(ev)

@router.post('/worlds/{world_id}/agents/{agent_id}/action')
def manual_action(world_id: str, agent_id: str, body: ManualAction, db: Session=Depends(get_db), _: None=Depends(auth)):
    """Operator injection for sandbox testing; routes through identical policy as LLM actions."""
    try:
        return manual_action_world(world_id, agent_id, body.model_dump())
    except WorldNotFound:
        raise HTTPException(404, 'World not found')
    except WorldConflict:
        raise HTTPException(404, 'Agent not found')

@router.get('/worlds/{world_id}/approvals')
def approvals(world_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    lookup_world(db,world_id)
    rows=db.scalars(select(Approval).where(Approval.world_id==world_id)
                    .order_by(Approval.created_at.desc()).limit(100)).all()
    return [approval_to_dict(a) for a in rows]

@router.post('/worlds/{world_id}/approvals/{approval_id}/approve')
def approve(world_id: str, approval_id: str, body: ReviewRequest, request: Request,
            db: Session=Depends(get_db), _: None=Depends(auth)):
    w=lookup_world(db,world_id)
    a=db.scalar(select(Approval).where(Approval.id==approval_id, Approval.world_id==world_id).with_for_update())
    if not a: raise HTTPException(404,'Approval not found')
    if a.status != 'pending': raise HTTPException(409,'Already reviewed')
    reviewer = request.state.actor
    a.status = 'approved'; a.reviewer = reviewer; a.reviewed_at = datetime.now(timezone.utc)
    emit(db,w,'approval_granted',f'{reviewer} approved {a.action_type}',detail={'approval_id':a.id})
    db.commit()
    return approval_to_dict(a)

@router.post('/worlds/{world_id}/approvals/{approval_id}/reject')
def reject(world_id: str, approval_id: str, body: ReviewRequest, request: Request,
           db: Session=Depends(get_db), _: None=Depends(auth)):
    w=lookup_world(db,world_id)
    a=db.scalar(select(Approval).where(Approval.id==approval_id, Approval.world_id==world_id).with_for_update())
    if not a: raise HTTPException(404,'Approval not found')
    if a.status != 'pending': raise HTTPException(409,'Already reviewed')
    reviewer = request.state.actor
    a.status = 'rejected'; a.reviewer = reviewer; a.reviewed_at = datetime.now(timezone.utc)
    emit(db,w,'approval_rejected',f'{reviewer} rejected {a.action_type}',detail={'approval_id':a.id})
    db.commit()
    return approval_to_dict(a)

@router.post('/worlds/{world_id}/approvals/{approval_id}/dispatch')
def dispatch(world_id: str, approval_id: str, db: Session=Depends(get_db), _: None=Depends(auth)):
    """Claim approval before network call; no automatic retries or unknown duplicate side-effects."""
    w=lookup_world(db,world_id)
    a=db.scalar(select(Approval).where(Approval.id==approval_id, Approval.world_id==world_id).with_for_update())
    if not a: raise HTTPException(404,'Approval not found')
    if a.status != 'approved': raise HTTPException(409,'Only approved, undispatched requests can execute')
    if not get_settings().webhook_url: raise HTTPException(409,'Operator has not configured an outbound gateway')
    a.status = 'dispatching'
    db.commit()
    try:
        external_ref = dispatch_approved(a)
    except GatewayError as exc:
        a.status='failed'
        emit(db,w,'dispatch_failed',str(exc),detail={'approval_id':a.id})
        db.commit()
        raise HTTPException(502,str(exc))
    a.status='dispatched'; a.external_ref=external_ref
    emit(db,w,'external_dispatched',f'Approved external action dispatched ({external_ref})',
         detail={'approval_id':a.id})
    db.commit()
    return approval_to_dict(a)
