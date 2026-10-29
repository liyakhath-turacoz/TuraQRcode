import secrets
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import BusinessCard, Code, User
from .projects import default_project
from .qr import render, vcard
from .routes_codes import code_payload, html_page, owned
from .schemas import CardInput, Design, luminance, readable_ink
from .security import ready_user

router=APIRouter(tags=['Business cards'])


def public_url(card):
    return settings.public_base_url.rstrip('/')+'/c/'+card.slug


def qr_name(card):
    return card.name[:90]+' — Digital business card'


def card_qr_ink(card):
    for color in (card.color,card.accent_color,'#163b75'):
        if color and 1.05/(luminance(color)+.05)>=4.5:
            return color
    return '#163b75'


def ensure_card_qr(db,card,user_id):
    code=db.get(Code,card.qr_code_id) if card.qr_code_id else None
    if code and code.user_id==user_id:
        code.name=qr_name(card)
        code.content={'url':public_url(card)}
        return code
    code=Code(user_id=user_id,project_id=default_project(db,user_id).id,name=qr_name(card),kind='url',mode='dynamic',
              slug=secrets.token_urlsafe(7),content={'url':public_url(card)},design=Design(foreground=card_qr_ink(card)).model_dump())
    db.add(code)
    db.flush()
    card.qr_code_id=code.id
    return code


def card_json(card):
    return {
        **{key:getattr(card,key) for key in ('id','slug','name','title','company','email','phone','website','bio','address','links','sections','experience','social_links','profile_image','cover_image','company_logo','color','background_end','background_angle','text_color','accent_color','qr_code_id','created_at')},
        'public_url':public_url(card),
    }


@router.get('/api/cards')
def list_cards(user:User=Depends(ready_user),db:Session=Depends(get_db)):
    return [card_json(card) for card in db.scalars(select(BusinessCard).where(BusinessCard.user_id==user.id).order_by(BusinessCard.created_at.desc()))]


@router.post('/api/cards',status_code=201)
def create_card(data:CardInput,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=BusinessCard(user_id=user.id,slug=secrets.token_urlsafe(8),**data.model_dump())
    db.add(card)
    db.flush()
    ensure_card_qr(db,card,user.id)
    db.commit()
    return card_json(card)


@router.patch('/api/cards/{card_id}')
def edit_card(card_id:str,data:CardInput,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=owned(db,BusinessCard,card_id,user)
    for key,value in data.model_dump().items():
        setattr(card,key,value)
    ensure_card_qr(db,card,user.id)
    db.commit()
    return card_json(card)


@router.delete('/api/cards/{card_id}',status_code=204)
def delete_card(card_id:str,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=owned(db,BusinessCard,card_id,user)
    if card.qr_code_id:
        code=db.get(Code,card.qr_code_id)
        if code and code.user_id==user.id:
            db.delete(code)
    db.delete(card)
    db.commit()


@router.post('/api/cards/{card_id}/qr-code')
def create_card_qr(card_id:str,user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=owned(db,BusinessCard,card_id,user)
    code=ensure_card_qr(db,card,user.id)
    db.commit()
    return {'qr_code_id':code.id,'qr_code_url':'/app/codes/'+code.id}


@router.get('/api/cards/{card_id}/qr')
def card_qr(card_id:str,format:str=Query('png',pattern='^(png|svg|pdf)$'),size:int=Query(1024,ge=256,le=4096),print_width_cm:float|None=Query(None,ge=2,le=50),print_preset:str=Query('standard',pattern='^(compact|standard|social|business_card|print|a4|high_res)$'),user:User=Depends(ready_user),db:Session=Depends(get_db)):
    card=owned(db,BusinessCard,card_id,user)
    code=db.get(Code,card.qr_code_id) if card.qr_code_id else None
    if code and code.user_id==user.id:
        raw,mime=render(code_payload(code),code.design,format,size,print_width_cm,print_preset)
    else:
        raw,mime=render(public_url(card),{'foreground':'#163b75','background':'#ffffff'},format,size,print_width_cm,print_preset)
    return Response(raw,media_type=mime,headers={'Content-Disposition':f'attachment; filename="digital-business-card-qr.{format}"'})


def public_card(db,slug):
    card=db.scalar(select(BusinessCard).where(BusinessCard.slug==slug))
    owner=db.get(User,card.user_id) if card else None
    if not card or not owner or not owner.is_active:
        raise HTTPException(404,'This business card could not be found.')
    return card


@router.get('/c/{slug}',response_class=HTMLResponse)
def public_profile(slug:str,db:Session=Depends(get_db)):
    card=public_card(db,slug)
    e=lambda value:escape(value or '',quote=True)
    ink=card.text_color or readable_ink(card.color)
    accent=card.accent_color or '#2563eb'
    panel_accent=accent if 1.05/(luminance(accent)+.05)>=4.5 else card_qr_ink(card)
    card_background=f'linear-gradient({int(card.background_angle or 135)}deg, {card.color}, {card.background_end})' if card.background_end else card.color
    initials=''.join(part[0] for part in card.name.split()[:2]).upper()
    links=''.join(f'<a class="profile-link" href="{e(link["url"])}" target="_blank" rel="noopener noreferrer"><span>{e(link["label"])}</span><span aria-hidden="true">↗</span></a>' for link in card.links or [])
    sections=''.join(f'<section class="profile-panel"><h2>{e(section.get("title"))}</h2><p class="profile-bio">{e(section.get("body"))}</p></section>' for section in card.sections or [])
    platform_names={'linkedin':'LinkedIn','instagram':'Instagram','facebook':'Facebook','x':'X','youtube':'YouTube','tiktok':'TikTok','github':'GitHub','pinterest':'Pinterest','whatsapp':'WhatsApp','telegram':'Telegram'}
    social=''.join(f'<a class="profile-link" href="{e(item["url"])}" target="_blank" rel="noopener noreferrer">{e(platform_names.get(item["platform"],item["platform"]))}<span aria-hidden="true">↗</span></a>' for item in card.social_links or [])
    experience=''.join(f'<article class="profile-experience"><h3>{e(item["role"])}</h3><p>{e(item.get("organization"))}</p><small>{e(item.get("period"))}</small><p class="profile-bio">{e(item.get("description"))}</p></article>' for item in card.experience or [])
    avatar=f'<img src="{e(card.profile_image)}" alt="{e(card.name)}"/>' if card.profile_image else e(initials)
    cover=f'<img class="profile-cover" src="{e(card.cover_image)}" alt="Profile cover"/>' if card.cover_image else ''
    logo=f'<img class="profile-company-logo" src="{e(card.company_logo)}" alt="{e(card.company or "Company")} logo"/>' if card.company_logo else ''
    contacts=[]
    if card.email:
        contacts.append(f'<a class="contact-link" href="mailto:{e(card.email)}"><span class="contact-icon">✉</span><span><small>EMAIL</small>{e(card.email)}</span></a>')
    if card.phone:
        contacts.append(f'<a class="contact-link" href="tel:{e(card.phone)}"><span class="contact-icon">☎</span><span><small>PHONE</small>{e(card.phone)}</span></a>')
    if card.website:
        contacts.append(f'<a class="contact-link" href="{e(card.website)}" target="_blank" rel="noopener noreferrer"><span class="contact-icon">↗</span><span><small>WEBSITE</small>{e(card.website)}</span></a>')
    if card.address:
        contacts.append(f'<div class="contact-link"><span class="contact-icon">⌖</span><span><small>LOCATION</small>{e(card.address)}</span></div>')
    role=' · '.join(value for value in (card.title,card.company) if value)
    profile_css='''
      body{background:linear-gradient(155deg,#edf4ff 0%,#f7f9fd 45%,#eef2f8 100%);color:#152b49;padding:24px 16px}
      main{box-sizing:border-box;max-width:760px;margin:2vh auto;padding:0;background:transparent;border:0;border-radius:0;box-shadow:none}
      .profile-shell{display:grid;gap:14px}.profile-brand{display:flex;align-items:center;justify-content:space-between;padding:8px 6px 14px;color:#536780;font-size:11px;font-weight:700;letter-spacing:.12em}
      .profile-brand span:last-child{font-weight:500;letter-spacing:0}.profile-hero{--hero-accent:VAR_HERO_ACCENT;position:relative;overflow:hidden;padding:30px;border-radius:20px;background:VAR_BACKGROUND;color:VAR_INK;box-shadow:0 18px 45px #10294e1c}
      .profile-hero:after{content:"";position:absolute;width:250px;height:250px;right:-90px;top:-130px;border:1px solid currentColor;border-radius:50%;opacity:.11;box-shadow:0 0 0 25px #ffffff0b,0 0 0 55px #ffffff09}
      .profile-avatar{display:grid;width:64px;height:64px;place-items:center;border:1px solid var(--hero-accent);border-radius:20px;background:#ffffff24;font-size:20px;font-weight:800}
      .profile-kicker{margin:23px 0 8px;font-size:10px;font-weight:700;letter-spacing:.16em;opacity:1}.profile-hero h1{margin:0;font-size:clamp(28px,6vw,42px);line-height:1.1;letter-spacing:-.045em}.profile-role{margin:10px 0 0;font-size:15px;opacity:1}
      .profile-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:22px}.profile-action{display:inline-flex;min-height:42px;align-items:center;justify-content:center;gap:8px;padding:10px 15px;border:1px solid #ffffff50;border-radius:10px;background:#ffffff20;color:inherit;text-decoration:none;font-size:12px;font-weight:700}
      .profile-action.primary{border-color:#fff;background:#fff;color:#173c72}.profile-panels{display:grid;grid-template-columns:1fr 1fr;gap:14px}.profile-panel{min-width:0;padding:20px;border:1px solid #dfe7f1;border-radius:16px;background:#fff;box-shadow:0 7px 20px #16375c08}
      .profile-panel h2{margin:0 0 15px;color:#1a3455;font-size:17px;letter-spacing:-.02em}.profile-bio{margin:0;color:#52657d;font-size:14px;line-height:1.8;white-space:pre-line}
      .contact-list{display:grid;gap:9px}.contact-link{display:flex;min-width:0;align-items:center;gap:11px;padding:10px;border:1px solid #e6ecf4;border-radius:10px;color:#234367;text-decoration:none;overflow-wrap:anywhere;font-size:12px}
      .contact-link small{display:block;margin:0 0 3px;color:#536780;font-size:9px;letter-spacing:.1em}.contact-icon{display:grid;flex:0 0 auto;width:34px;height:34px;place-items:center;border-radius:10px;background:#eff5ff;color:VAR_ACCENT;font-size:17px}
      .profile-links{display:grid;gap:8px}.profile-link{display:flex;min-height:46px;align-items:center;justify-content:space-between;gap:12px;padding:11px 13px;border:1px solid #dfe7f1;border-radius:10px;background:#f9fbfe;color:VAR_ACCENT;text-decoration:none;font-size:12px;font-weight:650}.profile-link:hover{border-color:#adc7ec;background:#f1f6ff}
      .profile-footer{padding:10px;color:#465b76;text-align:center;font-size:11px}.profile-footer a{color:VAR_ACCENT}
      .profile-avatar{overflow:hidden;width:88px;height:88px}.profile-avatar img{width:100%;height:100%;object-fit:cover}.profile-identity{display:flex;align-items:center;justify-content:space-between;gap:20px;position:relative;z-index:1}.profile-cover{display:block;width:calc(100% + 60px);max-width:none;height:200px;object-fit:cover;margin:-30px -30px 24px}.profile-company-logo{max-width:110px;max-height:65px;object-fit:contain;padding:8px;border-radius:12px;background:white}.profile-experience{padding:0 0 16px 15px;margin-top:18px;border-left:2px solid #dbeafe}.profile-experience h3{font-size:15px;margin:0 0 5px}.profile-experience p{margin:5px 0;color:#52657d}.profile-experience small{color:#536780}.profile-wide{grid-column:1/-1}
      @media(max-width:620px){body{padding:12px}.profile-hero{padding:23px;border-radius:16px}.profile-panels{grid-template-columns:1fr}.profile-panel{padding:17px}.profile-brand{padding-inline:3px}}
    '''.replace('VAR_BACKGROUND',e(card_background)).replace('VAR_INK',e(ink)).replace('VAR_HERO_ACCENT',e(accent)).replace('VAR_ACCENT',e(panel_accent))
    body=f'''<style>{profile_css}</style><div class="profile-shell"><div class="profile-brand"><span>DIGITAL BUSINESS CARD</span><span>Turacoz · TuraQRcode</span></div>
      <header class="profile-hero">{cover}<div class="profile-identity"><div class="profile-avatar">{avatar}</div>{logo}</div><p class="profile-kicker">LET’S CONNECT</p><h1>{e(card.name)}</h1>{f'<p class="profile-role">{e(role)}</p>' if role else ''}
      <div class="profile-actions"><a class="profile-action primary" href="/c/{e(card.slug)}/contact.vcf">Save contact</a>{f'<a class="profile-action" href="mailto:{e(card.email)}">Send an email</a>' if card.email else ''}</div></header>
      <div class="profile-panels">{f'<section class="profile-panel"><h2>About</h2><p class="profile-bio">{e(card.bio)}</p></section>' if card.bio else ''}
      {f'<section class="profile-panel"><h2>Contact & location</h2><div class="contact-list">{"".join(contacts)}</div></section>' if contacts else ''}
       {f'<section class="profile-panel profile-wide"><h2>Professional experience</h2>{experience}</section>' if experience else ''}{sections}{f'<section class="profile-panel"><h2>Social profiles</h2><div class="profile-links">{social}</div></section>' if social else ''}{f'<section class="profile-panel"><h2>Showcase your work</h2><div class="profile-links">{links}</div></section>' if links else ''}</div>
      <div class="profile-footer">Shared with care · <a href="/c/{e(card.slug)}/contact.vcf">Save this contact</a></div></div>'''
    return html_page(card.name,body)


@router.get('/c/{slug}/contact.vcf')
def contact(slug:str,db:Session=Depends(get_db)):
    card=public_card(db,slug)
    return Response(vcard({key:getattr(card,key) for key in ('name','title','company','email','phone','website','address')}),media_type='text/vcard',headers={'Content-Disposition':'attachment; filename="contact.vcf"'})
