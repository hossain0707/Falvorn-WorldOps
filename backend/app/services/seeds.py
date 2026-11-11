"""Original sample personas and neutral fictional landmarks, not third-party research assets."""
from app.domain.models import Agent

LANDMARKS = {
    'Commons': {'x': 48, 'y': 48, 'label': 'Community Square', 'type': 'social'},
    'Lab': {'x': 23, 'y': 23, 'label': 'Innovation Lab', 'type': 'work'},
    'Market': {'x': 75, 'y': 22, 'label': 'Trade Hall', 'type': 'economy'},
    'Hall': {'x': 76, 'y': 74, 'label': 'Assembly Hall', 'type': 'governance'},
    'Library': {'x': 23, 'y': 74, 'label': 'Knowledge Garden', 'type': 'learning'},
    'Station': {'x': 49, 'y': 87, 'label': 'Operations Hub', 'type': 'oversight'},
}
PERSONAS = [
    ('Nova', 'Systems Engineer', 'Tests new tools cautiously and records operational lessons.', 'Lab'),
    ('Orion', 'Community Coordinator', 'Fosters productive dialogue and de-escalates disputes.', 'Commons'),
    ('Sable', 'Security Analyst', 'Questions unverified claims and checks boundaries.', 'Station'),
    ('Lyra', 'Research Librarian', 'Balances exploration with strong source provenance.', 'Library'),
    ('Atlas', 'Resource Planner', 'Promotes sustainable allocation and fair exchange.', 'Market'),
    ('Cedar', 'Policy Facilitator', 'Creates transparent and inclusive rules.', 'Hall'),
    ('Pixel', 'Creative Builder', 'Develops new concepts in collaboration with peers.', 'Lab'),
    ('Sol', 'Community Observer', 'Monitors social dynamics and constructive trust.', 'Commons'),
]

def seed_agents(db, world_id, max_agents=50):
    agents = []
    for name, role, persona, location in PERSONAS[:max_agents]:
        item = Agent(world_id=world_id, name=name, role=role, persona=persona, location=location)
        db.add(item)
        agents.append(item)
    db.flush()
    return agents
