import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator, ValidationInfo

POLICY_VERSION = '2026-10-29'


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

    @field_validator('*',mode='before')
    @classmethod
    def trim_text(cls,value,info:ValidationInfo):
        if isinstance(value,str) and info.field_name not in ('password','new_password','current_password','token'):
            return value.strip()
        return value


def valid_url(value: str):
    try:
        p = urlsplit(value)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or len(value) > 2048 or any(ord(c) < 32 for c in value):
            raise ValueError()
        _ = p.port
    except ValueError:
        raise ValueError('Enter a valid http:// or https:// address without login details.')
    return value


def strong_password(value: str):
    if not 12 <= len(value) <= 128 or not re.search(r'[A-Za-z]', value) or not re.search(r'\d', value):
        raise ValueError('Use 12–128 characters, including a letter and a number.')
    return value


class Register(Input):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str
    accept_terms: bool
    accept_privacy: bool
    _password = field_validator('password')(strong_password)

    @model_validator(mode='after')
    def acceptance(self):
        if not self.accept_terms or not self.accept_privacy:
            raise ValueError('Please accept the Terms & Conditions and Privacy Policy to create your account.')
        return self


class Login(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    admin: bool = False


class PasswordChange(Input):
    current_password: str = Field(max_length=128)
    new_password: str
    _password = field_validator('new_password')(strong_password)


class ForgotPassword(Input):
    email: EmailStr


class ResetPassword(Input):
    token: str = Field(min_length=30, max_length=200)
    new_password: str
    _password = field_validator('new_password')(strong_password)


class Profile(Input):
    name: str = Field(min_length=2, max_length=100)


def luminance(color):
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    return sum((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)*w for v,w in zip(rgb,(.2126,.7152,.0722)))


def readable_ink(color):
    return '#0f172a' if luminance(color)>.179 else '#ffffff'


class Design(Input):
    foreground: str = '#163b75'
    background: str = '#ffffff'
    pattern: Literal['square', 'rounded', 'dots', 'diamond', 'soft', 'horizontal', 'vertical'] = 'square'
    eye_style: Literal['square', 'rounded', 'circle'] = 'square'
    eye_color: str | None = None
    frame: Literal['none', 'scan', 'banner', 'border'] = 'none'
    frame_label: str = Field(default='SCAN ME',min_length=1,max_length=24)
    logo: str | None = Field(default=None, max_length=700000)

    @field_validator('foreground', 'background', 'eye_color')
    @classmethod
    def color(cls, value):
        if value is None: return value
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise ValueError('Choose a valid color.')
        return value.lower()

    @model_validator(mode='after')
    def contrast(self):
        fg, bg = luminance(self.foreground), luminance(self.background)
        if bg <= fg or (bg+.05)/(fg+.05) < 4.5:
            raise ValueError('Use a dark QR color and light background with stronger contrast.')
        eye=luminance(self.eye_color or self.foreground)
        if bg<=eye or (bg+.05)/(eye+.05)<4.5:
            raise ValueError('Choose a darker eye color for reliable scanning.')
        if not self.frame_label.isascii() or any(ord(c)<32 for c in self.frame_label):
            raise ValueError('Use printable English letters, numbers, or punctuation for the frame label.')
        if self.logo:
            from .qr import normalize_logo
            self.logo = normalize_logo(self.logo)
        return self


Kind = Literal['url', 'text', 'email', 'phone', 'sms', 'wifi', 'vcard', 'barcode']


def validate_content(kind, content):
    if kind=='barcode':
        from .barcodes import validate_barcode
        return validate_barcode(content)
    allowed = {
        'url': {'url'}, 'text': {'text'}, 'email': {'email','subject','body'},
        'phone': {'phone'}, 'sms': {'phone','message'},
        'wifi': {'ssid','password','security','hidden'},
        'vcard': {'name','company','title','email','phone','website','address'},
    }[kind]
    if set(content) - allowed:
        raise ValueError('Unsupported content fields.')
    if any(not isinstance(v, (str, bool)) for v in content.values()):
        raise ValueError('Enter text in each content field.')
    preserve = {'wifi': {'ssid','password'}, 'text': {'text'}, 'sms': {'message'}, 'email': {'body'}}.get(kind,set())
    content = {k: v.strip() if isinstance(v, str) and k not in preserve else v for k,v in content.items()}
    if any(isinstance(v, str) and len(v) > 2000 for v in content.values()):
        raise ValueError('Content fields must be 2,000 characters or fewer.')
    required = {'url':'url', 'text':'text', 'email':'email', 'phone':'phone', 'sms':'phone', 'wifi':'ssid', 'vcard':'name'}[kind]
    if not isinstance(content.get(required), str) or not content[required]:
        raise ValueError(f'Please complete the {required} field.')
    if kind == 'url':
        valid_url(content['url'])
    if kind == 'vcard' and content.get('website'):
        valid_url(content['website'])
    if kind in ('email','vcard') and content.get('email'):
        from pydantic import TypeAdapter
        TypeAdapter(EmailStr).validate_python(content['email'])
    if kind in ('phone','sms','vcard') and content.get('phone') and not re.fullmatch(r'\+?[0-9() .\-]{5,30}', content['phone']):
        raise ValueError('Enter a valid telephone number.')
    if kind == 'wifi':
        if len(content['ssid'].encode('utf-8')) > 32 or len(content.get('password', '')) > 63:
            raise ValueError('Network name or password is too long.')
        if 'hidden' in content and not isinstance(content['hidden'],bool):
            raise ValueError('The hidden network setting must be true or false.')
        if content.get('security', 'WPA') not in ('WPA', 'WEP', 'nopass'):
            raise ValueError('Choose a supported Wi-Fi security type.')
    if sum(len(str(v)) for v in content.values()) > 2200:
        raise ValueError('Please shorten the QR content.')
    return content


class CodeCreate(Input):
    name: str = Field(min_length=1, max_length=120)
    kind: Kind = 'url'
    mode: Literal['dynamic','static','short'] = 'dynamic'
    content: dict
    design: Design = Field(default_factory=Design)
    alias: str | None = Field(default=None, min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')
    project_id: str | None = Field(default=None, max_length=36)
    expires_at: datetime | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    mobile_url: str | None = None

    @model_validator(mode='after')
    def validate_code(self):
        self.content = validate_content(self.kind, self.content)
        if self.mode != 'static' and self.kind != 'url':
            raise ValueError('Editable codes and short links require a website address.')
        if self.mode == 'static' and (self.expires_at or self.password or self.mobile_url or self.alias):
            raise ValueError('Link controls are available for editable codes and short links.')
        if self.mode == 'static' and self.kind!='barcode':
            from .qr import payload, qr_matrix
            qr_matrix(payload(self.kind,self.content))
        if self.mobile_url:
            valid_url(self.mobile_url)
        if self.expires_at and self.expires_at.tzinfo is None:
            raise ValueError('Include a time zone with the expiry date.')
        return self


class CodeUpdate(Input):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    content: dict | None = None
    design: Design | None = None
    project_id: str | None = Field(default=None, max_length=36)
    is_active: bool | None = None
    expires_at: datetime | None = None
    password: str | None = Field(default=None, max_length=128)
    mobile_url: str | None = None


class Preview(Input):
    kind: Kind = 'url'
    content: dict
    design: Design = Field(default_factory=Design)

    @model_validator(mode='after')
    def validate_data(self):
        self.content = validate_content(self.kind, self.content)
        return self


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default='#2563eb', pattern=r'^#[0-9a-fA-F]{6}$')


class CardInput(Input):
    name: str = Field(min_length=2, max_length=100)
    title: str = Field(default='', max_length=120)
    company: str = Field(default='', max_length=120)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=30)
    website: str = Field(default='', max_length=2048)
    color: str = Field(default='#2563eb', pattern=r'^#[0-9a-fA-F]{6}$')

    @model_validator(mode='after')
    def card_data(self):
        validate_content('vcard', self.model_dump(exclude={'color'}))
        return self


class AdminUserUpdate(Input):
    is_active: bool
