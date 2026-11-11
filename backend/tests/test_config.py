import pytest
from pydantic import ValidationError
from app.core.config import Settings

def test_production_requires_strong_key_and_postgres():
    with pytest.raises(ValidationError):
        Settings(_env_file=None,app_env='production',database_url='sqlite:///bad.db',api_key='abc')
    cfg=Settings(_env_file=None,app_env='production',database_url='postgresql+psycopg://u:p@db:5432/x',api_key='a'*32)
    assert cfg.app_env=='production'

def test_production_blocks_insecure_webhook():
    with pytest.raises(ValidationError):
        Settings(_env_file=None,app_env='production',database_url='postgresql+psycopg://u:p@db:5432/x',api_key='a'*32,
                 webhook_url='http://example.com',webhook_signing_secret='x'*32)
