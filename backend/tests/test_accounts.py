from uuid import uuid4
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import app
from app.models import User,AuthSession,ResetToken,now
from app.db import engine
from app.security import passwords,digest

def registration(email=None,**changes):
    return {'name':'Test User','email':email or uuid4().hex+'@example.com','password':'StrongPassword123!','accept_terms':True,'accept_privacy':True,**changes}

def test_registration_requires_both_policy_acceptances(client):
    for terms,privacy in [(False,False),(False,True),(True,False)]:
        r=client.post('/api/auth/register',json=registration(accept_terms=terms,accept_privacy=privacy))
        assert r.status_code==422

def test_registration_hashes_password_and_records_acceptance(client,member):
    with Session(engine()) as db:
        user=db.get(User,member['id'])
        assert user.password_hash.startswith('$argon2id$')
        assert passwords.verify('StrongPassword123!',user.password_hash)
        assert user.accepted_terms_at and user.policy_version=='2026-10-29'
        assert not user.is_admin
        assert db.scalar(select(AuthSession).where(AuthSession.user_id==user.id)).token_hash!=client.cookies.get('tura_session')
    assert 'password_hash' not in member
    assert client.get('/api/auth/me').status_code==200
    cookies=client.cookies.get('tura_session');assert len(cookies)>30

def test_cookie_is_http_only(client):
    r=client.post('/api/auth/register',json=registration())
    cookie=r.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=lax' in cookie

def test_email_case_and_duplicate_handling(client):
    data=registration(email='Member'+uuid4().hex[:8]+'@Example.com')
    assert client.post('/api/auth/register',json=data).status_code==201
    assert client.post('/api/auth/register',json={**data,'email':data['email'].lower()}).status_code==409
    assert client.post('/api/auth/login',json={'email':data['email'].upper(),'password':data['password']}).status_code==200

def test_password_strength_validation_never_echoes_password(client):
    password='secret1'
    r=client.post('/api/auth/register',json=registration(password=password))
    assert r.status_code==422 and password not in r.text

def test_admin_role_cannot_be_injected(client):
    r=client.post('/api/auth/register',json=registration(is_admin=True))
    assert r.status_code==422

def test_admin_bootstrap_and_forced_password_change(client):
    r=client.post('/api/auth/login',json={'email':'Admin@turacoz.com','password':'Admin','admin':True})
    assert r.status_code==200 and r.json()['must_change_password']
    assert client.get('/api/admin/overview').status_code==403
    assert client.get('/api/codes').status_code==403
    assert client.patch('/api/auth/profile',json={'name':'Other'}).status_code==403
    r=client.post('/api/auth/password',json={'current_password':'Admin','new_password':'AdminStrongPassword456!'})
    assert r.status_code==200 and not r.json()['must_change_password']
    assert client.get('/api/admin/overview').status_code==200
    assert client.post('/api/auth/login',json={'email':'Admin@turacoz.com','password':'Admin'}).status_code==401

def test_members_cannot_use_admin_endpoints(client,member):
    for path in ('overview','users','codes','audit'):
        assert client.get('/api/admin/'+path).status_code==403
    assert client.post('/api/auth/login',json={'email':member['email'],'password':'StrongPassword123!','admin':True}).status_code==401

def test_invalid_login_and_logout(client,member):
    assert client.post('/api/auth/login',json={'email':member['email'],'password':'Wrong'}).status_code==401
    assert client.post('/api/auth/logout',json={}).status_code==204
    assert client.get('/api/auth/me').status_code==401

def test_password_change_revokes_other_sessions(client,member):
    second=TestClient(app,headers={'Origin':'http://127.0.0.1:5173'})
    second.post('/api/auth/login',json={'email':member['email'],'password':'StrongPassword123!'})
    assert second.get('/api/auth/me').status_code==200
    assert client.post('/api/auth/password',json={'current_password':'StrongPassword123!','new_password':'AnotherStrongPassword123!'}).status_code==200
    assert second.get('/api/auth/me').status_code==401
    assert client.get('/api/auth/me').status_code==200

def test_expired_session_rejected(client,member):
    with Session(engine()) as db:
        session=db.get(AuthSession,digest(client.cookies.get('tura_session')))
        session.expires_at=now()-timedelta(seconds=1);db.commit()
    assert client.get('/api/auth/me').status_code==401

def test_cross_origin_mutations_rejected(client,member):
    assert client.patch('/api/auth/profile',json={'name':'Tampered'},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.patch('/api/auth/profile',json={'name':'Updated Name'}).status_code==200
    assert client.post('/api/auth/login',json={'email':member['email'],'password':'StrongPassword123!'},headers={'Origin':'https://evil.example'}).status_code==403

def test_reset_is_expiring_and_single_use(client,member):
    from app.routes_auth import new_reset
    with Session(engine()) as db:
        token=new_reset(db,db.get(User,member['id'])).split('token=')[1];db.commit()
    r=client.post('/api/auth/reset-password',json={'token':token,'new_password':'RecoveredPassword123!'})
    assert r.status_code==200
    assert client.post('/api/auth/reset-password',json={'token':token,'new_password':'OtherPassword123!'}).status_code==400
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':member['email'],'password':'RecoveredPassword123!'}).status_code==200

def test_expired_recovery_link_and_generic_recovery_response(client,member):
    with Session(engine()) as db:
        token='x'*50
        db.add(ResetToken(token_hash=digest(token),user_id=member['id'],expires_at=now()-timedelta(minutes=1)));db.commit()
    assert client.post('/api/auth/reset-password',json={'token':token,'new_password':'RecoveredPassword123!'}).status_code==400
    r=client.post('/api/auth/forgot-password',json={'email':member['email']})
    missing=client.post('/api/auth/forgot-password',json={'email':'nonexistent@example.com'})
    assert r.status_code==200 and r.json()==missing.json() and 'token' not in r.text

def test_login_rate_limit(client):
    statuses=[client.post('/api/auth/login',json={'email':'missing@example.com','password':'Wrong'}).status_code for _ in range(16)]
    assert statuses[-1]==429
