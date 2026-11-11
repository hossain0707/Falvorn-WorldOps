from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class NewWorld(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    scenario: Literal['town', 'workplace'] = 'town'
    seed: int = Field(default=42, ge=0, le=2147483647)
    starter_agents: bool = True

class NewAgent(BaseModel):
    name: str = Field(min_length=2, max_length=64, pattern=r'^[\w -]+$')
    role: str = Field(min_length=3, max_length=90)
    persona: str = Field(default='', max_length=500)
    provider: Literal['heuristic','openai_compatible'] = 'heuristic'
    model: str = Field(default='heuristic-v1', max_length=100)
    location: Literal['Commons', 'Lab', 'Market', 'Hall', 'Library', 'Station'] = 'Commons'

class StepRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=20)

class FeedRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    source: str = Field(default='operator', min_length=2, max_length=80)

class ReviewRequest(BaseModel):
    # The authenticated key principal is the source of truth, never this request body.
    model_config = ConfigDict(extra='forbid')

class ManualAction(BaseModel):
    action: Literal['move','talk','work','rest','reflect','propose','vote','request_external','observe']
    target: str | None = Field(default=None, max_length=120)
    content: str = Field(default='', max_length=300)

class WithORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)
