import secrets
from html import escape
from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import BusinessCard, User
from .schemas import CardInput, luminance, readable_ink
from .security import ready_user
from .routes_codes import owned, html_page
from .qr import render, vcard

router=APIRouter(tags=['Business cards'])


def card_json(card):
    return {**{key:getattr(card,key) for key in ('id','slug','name','title','company','email','phone','website','color','created_at')},'public_url':settings.public_base_url.rstrip('/')+'/c/'+card.slug}


@router.get('/api/cards')
def list_cards(user:User=Depends(ready_user),db:Session=Depends(get_db)):
    return [card_json(c) for c in db.scalars(select(BusinessCard).where(BusinessCard.user_id==user.id).order_by(BusinessCard.created_at.desc()))]


@router.post('/api/cards',status_code=201)
def create_card(data:CardInput,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=BusinessCard(user_id=user.id,slug=secrets.token_urlsafe(8),**data.model_dump())
    db.add(card); db.commit()
    return card_json(card)


@router.patch('/api/cards/{card_id}')
def edit_card(card_id:str,data:CardInput,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=owned(db,BusinessCard,card_id,user)
    for k,v in data.model_dump().items(): setattr(card,k,v)
    db.commit()
    return card_json(card)


@router.delete('/api/cards/{card_id}',status_code=204)
def delete_card(card_id:str,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    db.delete(owned(db,BusinessCard,card_id,user)); db.commit()


@router.get('/api/cards/{card_id}/qr')
def card_qr(card_id:str,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=owned(db,BusinessCard,card_id,user)
    ink=card.color if (1.05/(luminance(card.color)+.05))>=4.5 else '#163b75'
    raw,mime=render(settings.public_base_url.rstrip('/')+'/c/'+card.slug,{'foreground':ink,'background':'#ffffff'})
    return Response(raw,media_type=mime,headers={'Content-Disposition':'attachment; filename="business-card.png"'})


def public_card(db,slug):
    card=db.scalar(select(BusinessCard).where(BusinessCard.slug==slug))
    if not card or not db.get(User,card.user_id).is_active: raise HTTPException(404,'This business card could not be found.')
    return card


@router.get('/c/{slug}',response_class=HTMLResponse)
def public_profile(slug:str,db:Session=Depends(get_db)):
    c=public_card(db,slug)
    e=lambda v: escape(v,quote=True)
    body='<header style="background:'+c.color+';color:'+readable_ink(c.color)+';padding:24px;border-radius:12px"><p>LET’S CONNECT</p><h1>'+e(c.name)+'</h1><p>'+e(c.title)+'</p><p>'+e(c.company)+'</p></header>'
    if c.email: body+='<p><a href="mailto:'+e(c.email)+'">'+e(c.email)+'</a></p>'
    if c.phone: body+='<p><a href="tel:'+e(c.phone)+'">'+e(c.phone)+'</a></p>'
    if c.website: body+='<p><a rel="noopener noreferrer" href="'+e(c.website)+'">Visit website</a></p>'
    body+='<p><a href="/c/'+e(slug)+'/contact.vcf">Save contact</a></p>'
    return html_page(c.name,body)


@router.get('/c/{slug}/contact.vcf')
def contact(slug:str,db:Session=Depends(get_db)):
    c=public_card(db,slug)
    return Response(vcard({k:getattr(c,k) for k in ('name','title','company','email','phone','website')}),media_type='text/vcard',headers={'Content-Disposition':'attachment; filename="contact.vcf"'})
