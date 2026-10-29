"""Non-destructive live checks; only this run's temporary account is removed."""
import sys
from pathlib import Path
from uuid import uuid4
from datetime import timedelta
from sqlalchemy import select,text,delete
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import settings
from app.db import engine
from app.models import User,Audit,Code,Event
from app.main import app
from app.security import passwords

def run():
    email='smoke-'+uuid4().hex+'@example.com';user_id=None
    try:
        with engine().connect() as db:
            assert db.scalar(text('SELECT 1'))==1
            print('PASS Supabase PostgreSQL connection')
            if engine().url.host not in ('127.0.0.1','localhost'):
                # pg_stat_ssl describes the pooler-to-server hop; libpq reports
                # the actual encrypted connection from this client to Supabase.
                assert db.connection.driver_connection.pgconn.ssl_in_use
                print('PASS encrypted PostgreSQL connection')
            assert db.scalar(text("SELECT version_num FROM tura.alembic_version"))=='8904875a8d26'
            print('PASS migrations at head')
        with Session(engine()) as db:
            admin=db.scalar(select(User).where(User.email==settings.initial_admin_email.lower()))
            assert admin and admin.is_admin and admin.must_change_password
            assert passwords.verify(settings.initial_admin_password,admin.password_hash)
            assert admin.password_hash.startswith('$argon2id$')
            print('PASS initial administrator hash, role, and mandatory password change')
            for role in ('anon','authenticated'):
                if db.scalar(text('SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=:role)'),{'role':role}):
                    assert not db.scalar(text("SELECT has_schema_privilege(:role,'tura','USAGE')"),{'role':role})
            print('PASS Supabase API roles cannot access private application schema')
        with TestClient(app,headers={'Origin':settings.origins[0]}) as client:
            assert client.get('/api/ready').status_code==200
            response=client.post('/api/auth/register',json={'name':'Temporary Smoke Check','email':email,'password':'SmokeCheckPassword123!','accept_terms':True,'accept_privacy':True})
            assert response.status_code==201
            user_id=response.json()['id']
            print('PASS live registration and session persistence')
            response=client.post('/api/codes',json={'name':'Temporary connection check','content':{'url':'https://example.com/smoke-check'}})
            assert response.status_code==201
            code=response.json()
            assert client.get('/api/codes/'+code['id']).json()['name']=='Temporary connection check'
            print('PASS live QR creation and database read-back')
            response=client.get('/r/'+code['slug']+'?via=qr',follow_redirects=False)
            assert response.status_code==302 and response.headers['location']=='https://example.com/smoke-check'
            assert client.get('/api/analytics?code_id='+code['id']).json()['scans']==1
            print('PASS live redirect and scan analytics persistence')
            for fmt in ('png','svg','pdf'):
                assert client.get('/api/codes/'+code['id']+'/download?format='+fmt).status_code==200
            print('PASS live PNG, SVG, and PDF exports')
            assert client.get('/api/admin/overview').status_code==403
            print('PASS live administrator access restrictions')
            assert client.delete('/api/codes/'+code['id']).status_code==204
            assert client.get('/r/'+code['slug'],follow_redirects=False).status_code==404
            print('PASS live deletion and invalidated redirect')
    finally:
        with Session(engine()) as db:
            user=db.scalar(select(User).where(User.email==email))
            if user:
                db.execute(delete(Audit).where(Audit.actor_id==user.id))
                db.delete(user);db.commit()
                print('PASS temporary smoke-check data removed')

if __name__=='__main__':
    try: run()
    except Exception as exc:
        print('FAIL live smoke check ('+type(exc).__name__+'). Credentials were not logged.')
        sys.exit(1)
