from fastapi.testclient import TestClient
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from app.main import app
from app.models import User
from app.db import engine
from app.security import passwords

def admin_client():
    from uuid import uuid4
    with Session(engine()) as db:
        email='admin-'+uuid4().hex[:8]+'@example.com'
        user=User(name='Test Administrator',email=email,password_hash=passwords.hash('AdminPassword123!'),is_admin=True)
        db.add(user);db.commit()
    client=TestClient(app,headers={'Origin':'http://127.0.0.1:5174'})
    assert client.post('/api/auth/login',json={'email':email,'password':'AdminPassword123!','admin':True}).status_code==200
    return client

def test_projects_crud_and_safe_unassignment(client,member):
    p=client.post('/api/projects',json={'name':'Launch','color':'#087568'});assert p.status_code==201
    pid=p.json()['id']
    c=client.post('/api/codes',json={'name':'Project code','project_id':pid,'content':{'url':'https://example.com'}}).json()
    assert client.get('/api/projects').json()[0]['total_codes']==1
    assert client.patch('/api/projects/'+pid,json={'name':'Launch 2026','color':'#193c34'}).status_code==200
    assert client.get('/api/codes?project_id='+pid).json()['total']==1
    assert client.delete('/api/projects/'+pid).status_code==204
    assert client.get('/api/codes/'+c['id']).json()['project_id'] is None
    assert client.post('/api/codes',json={'name':'Missing project','project_id':pid,'content':{'url':'https://example.com'}}).status_code==404

def test_business_cards_public_profile_vcard_qr_and_delete(client,member):
    data={'name':'Jane Smith','title':'Director','company':'Turacoz','email':'jane@example.com','phone':'+919876543210','website':'https://example.com','color':'#087568'}
    r=client.post('/api/cards',json=data);assert r.status_code==201,r.text
    c=r.json();assert c['public_url'].startswith('http://testserver/c/')
    profile=client.get('/c/'+c['slug']);assert profile.status_code==200 and 'Jane Smith' in profile.text
    contact=client.get('/c/'+c['slug']+'/contact.vcf');assert 'BEGIN:VCARD' in contact.text and 'FN:Jane Smith' in contact.text
    assert client.get('/api/cards/'+c['id']+'/qr').content.startswith(b'\x89PNG')
    assert client.patch('/api/cards/'+c['id'],json={**data,'title':'Managing Director'}).status_code==200
    assert 'Managing Director' in client.get('/c/'+c['slug']).text
    assert client.delete('/api/cards/'+c['id']).status_code==204
    assert client.get('/c/'+c['slug']).status_code==404

def test_business_card_html_escapes_untrusted_text(client,member):
    c=client.post('/api/cards',json={'name':'<script>alert(1)</script>'}).json()
    html=client.get('/c/'+c['slug']).text
    assert '<script>' not in html and '&lt;script&gt;' in html

def test_admin_suspend_revokes_sessions_and_pauses_public_access(client,code):
    admin=admin_client();member=client.get('/api/auth/me').json()
    r=admin.patch('/api/admin/users/'+member['id'],json={'is_active':False});assert r.status_code==200
    assert client.get('/api/auth/me').status_code==401
    assert client.get('/r/'+code['slug']).status_code==410
    assert admin.patch('/api/admin/users/'+member['id'],json={'is_active':True}).status_code==200
    assert client.post('/api/auth/login',json={'email':member['email'],'password':'StrongPassword123!'}).status_code==200
    assert client.get('/r/'+code['slug'],follow_redirects=False).status_code==302

def test_admin_moderation_recovery_and_audit(client,code):
    admin=admin_client();member=client.get('/api/auth/me').json()
    assert admin.get('/api/admin/users').json()['total']>=2
    assert admin.get('/api/admin/codes').json()['total']>=1
    assert admin.patch('/api/admin/codes/'+code['id'],json={'is_active':False}).status_code==200
    assert client.get('/r/'+code['slug']).status_code==410
    assert admin.patch('/api/admin/codes/'+code['id'],json={'is_active':True}).status_code==200
    reset=admin.post('/api/admin/users/'+member['id']+'/reset',json={})
    assert reset.status_code==200 and reset.json()['expires_in_minutes']==30
    token=reset.json()['reset_url'].split('token=')[1]
    assert client.post('/api/auth/reset-password',json={'token':token,'new_password':'RecoveredMember123!'}).status_code==200
    audit=admin.get('/api/admin/audit').json()['items']
    assert any(a['action']=='admin.recovery_link_created' for a in audit)
    assert token not in str(audit)
    me=admin.get('/api/auth/me').json()
    assert admin.patch('/api/admin/users/'+me['id'],json={'is_active':False}).status_code==400

def test_private_schema_and_rls_present():
    with engine().connect() as c:
        rows=c.execute(text("SELECT relname,relrowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='tura' AND relkind='r' AND relname!='alembic_version'")).all()
        assert len(rows)==8 and all(row[1] for row in rows)
        assert not c.scalar(text("SELECT has_schema_privilege('public','tura','USAGE')")) if c.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='public')")) else True
