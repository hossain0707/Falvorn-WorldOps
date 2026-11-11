"""Security contract tests for operator identities and access segregation."""
import hashlib
import pytest
from app.core.config import get_settings

BASE='/api/v1'

@pytest.fixture
def keys(monkeypatch):
    admin='a' * 40
    reader='b' * 40
    monkeypatch.setenv('API_KEY',admin)
    monkeypatch.setenv('READ_ONLY_API_KEY',reader)
    get_settings.cache_clear()
    yield admin,reader
    get_settings.cache_clear()


def test_readonly_key_reads_but_does_not_mutate(client, keys):
    admin,reader=keys
    assert client.get(BASE+'/worlds').status_code == 401
    assert client.get(BASE+'/worlds', headers={'X-API-Key':reader}).status_code == 200
    assert client.post(BASE+'/worlds',json={'name':'Blocked creation'},headers={'X-API-Key':reader}).status_code == 403
    assert client.post(BASE+'/worlds',json={'name':'Permitted creation'},headers={'X-API-Key':admin}).status_code == 201
    assert client.get(BASE+'/worlds',headers={'X-API-Key':'invalid'}).status_code == 401
    assert client.get(BASE+'/live').status_code == 200


def test_approval_reviewer_identified_by_server_not_body(client, keys):
    admin,reader=keys
    header={'X-API-Key':admin}
    w=client.post(BASE+'/worlds',json={'name':'Workplace','scenario':'workplace'},headers=header).json()
    wid=w['id']
    agent=client.get(f'{BASE}/worlds/{wid}/agents',headers=header).json()[0]
    path=f'{BASE}/worlds/{wid}/agents/{agent["id"]}/action'
    assert client.post(path,json={'action':'request_external','content':'A summary'},headers=header).status_code == 200
    ap=client.get(f'{BASE}/worlds/{wid}/approvals',headers=header).json()[0]
    approval_path=f'{BASE}/worlds/{wid}/approvals/{ap["id"]}/approve'
    assert client.post(approval_path,json={'reviewer':'Forged CEO'},headers=header).status_code == 422
    assert client.post(approval_path,json={},headers={'X-API-Key':reader}).status_code == 403
    response=client.post(approval_path,json={},headers=header)
    assert response.status_code == 200
    assert response.json()['reviewer'] == 'admin-' + hashlib.sha256(admin.encode()).hexdigest()[:16]


def test_security_headers(client):
    r=client.get('/')
    assert r.status_code == 200
    assert r.headers['x-frame-options'] == 'DENY'
    assert "default-src 'none'" in r.headers['content-security-policy']
    assert r.headers['cache-control'] == 'no-store'
    assert client.get(BASE+'/health').headers['x-content-type-options'] == 'nosniff'
