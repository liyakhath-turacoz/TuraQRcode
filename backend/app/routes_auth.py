import secrets
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from fastapi import APIRouter, Depends, Request, Response, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .projects import default_project
from .db import get_db
from .models import User, ResetToken, AuthSession, now
from .schemas import Register, Login, PasswordChange, ForgotPassword, ResetPassword, Profile, POLICY_VERSION
from .security import passwords, verify, DUMMY_HASH, COOKIE, throttle, public_user, create_session, current_user, ready_user, digest, revoke_sessions, audit

router = APIRouter(prefix='/api/auth',tags=['Accounts'])


def new_reset(db, user):
    from sqlalchemy import delete
    db.execute(delete(ResetToken).where(ResetToken.user_id==user.id))
    token = secrets.token_urlsafe(40)
    db.add(ResetToken(token_hash=digest(token),user_id=user.id,expires_at=now()+timedelta(minutes=30)))
    return settings.frontend_url.rstrip('/') + '/reset-password?token=' + token


def send_reset(email, url):
    message = EmailMessage()
    message['Subject'] = 'Reset your TuraQRcode password'
    message['From'] = settings.smtp_from
    message['To'] = email
    message.set_content(f'Use this link within 30 minutes to reset your TuraQRcode password:\n\n{url}\n\nIf you did not request this, you can ignore this email.\n\nTuracoz')
    try:
        with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=15) as server:
            if settings.smtp_starttls:
                import ssl
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_user: server.login(settings.smtp_user,settings.smtp_password)
            server.send_message(message)
    except (OSError,smtplib.SMTPException):
        # Never log a reset link or credentials.
        import logging
        logging.getLogger(__name__).warning('Password recovery email delivery failed.')


@router.post('/register',status_code=201)
def register(data:Register,request:Request,response:Response,db:Session=Depends(get_db)):
    throttle(request,'registration',10,3600)
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email==email)):
        raise HTTPException(409,'An account with this email already exists. Please sign in.')
    user = User(name=data.name,email=email,password_hash=passwords.hash(data.password),accepted_terms_at=now(),policy_version=POLICY_VERSION)
    db.add(user)
    try: db.flush()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,'An account with this email already exists. Please sign in.')
    default_project(db,user.id)
    audit(db,user,'account.registered',email)
    create_session(db,user,response)
    return public_user(user)


@router.post('/login')
def login(data:Login,request:Request,response:Response,db:Session=Depends(get_db)):
    throttle(request,'login',15,300)
    user = db.scalar(select(User).where(User.email==str(data.email).lower()))
    correct = verify(data.password,user.password_hash if user else DUMMY_HASH)
    if not user or not correct or not user.is_active or (data.admin and not user.is_admin):
        raise HTTPException(401,'The email or password is incorrect.')
    audit(db,user,'account.signed_in')
    create_session(db,user,response)
    return public_user(user)


@router.get('/me')
def me(user:User=Depends(current_user)):
    return public_user(user)


@router.post('/logout',status_code=204)
def logout(request:Request,response:Response,db:Session=Depends(get_db)):
    token=request.cookies.get(COOKIE)
    if token:
        session=db.get(AuthSession,digest(token))
        if session: db.delete(session); db.commit()
    response.delete_cookie(COOKIE,path='/',secure=settings.cookie_secure,httponly=True,samesite='lax')


@router.post('/password')
def change_password(data:PasswordChange,request:Request,response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
    throttle(request,'password',10,300)
    if not verify(data.current_password,user.password_hash): raise HTTPException(400,'Your current password is incorrect.')
    if verify(data.new_password,user.password_hash): raise HTTPException(400,'Choose a password different from your current password.')
    user.password_hash=passwords.hash(data.new_password)
    user.must_change_password=False
    revoke_sessions(db,user.id)
    audit(db,user,'account.password_changed')
    create_session(db,user,response)
    return public_user(user)


@router.patch('/profile')
def profile(data:Profile,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    user.name=data.name
    db.commit()
    return public_user(user)


@router.post('/forgot-password')
def forgot(data:ForgotPassword,request:Request,tasks:BackgroundTasks,db:Session=Depends(get_db)):
    throttle(request,'recovery',5,900)
    user=db.scalar(select(User).where(User.email==str(data.email).lower(),User.is_active.is_(True)))
    if user and settings.smtp_host and settings.smtp_from:
        url=new_reset(db,user)
        db.commit()
        tasks.add_task(send_reset,user.email,url)
    return {'message':'If an eligible account exists, password recovery instructions will be sent. If you do not receive an email, contact your account administrator.'}


@router.post('/reset-password')
def reset(data:ResetPassword,request:Request,response:Response,db:Session=Depends(get_db)):
    throttle(request,'reset',10,900)
    # Lock makes each token single-use even with concurrent requests.
    token=db.scalar(select(ResetToken).where(ResetToken.token_hash==digest(data.token)).with_for_update())
    if not token or token.used or token.expires_at <= now(): raise HTTPException(400,'This recovery link is invalid or has expired. Please request a new one.')
    user=db.get(User,token.user_id)
    if not user or not user.is_active: raise HTTPException(400,'This recovery link is unavailable.')
    token.used=True
    user.password_hash=passwords.hash(data.new_password)
    user.must_change_password=False
    revoke_sessions(db,user.id)
    audit(db,user,'account.password_reset')
    db.commit()
    response.delete_cookie(COOKIE,path='/')
    return {'message':'Your password has been updated. You can now sign in.'}
