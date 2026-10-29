"""Turn handles into platform URLs without looking up private social accounts."""
import re
from urllib.parse import quote, urlsplit, urlunsplit

PLATFORMS = {
    'youtube': (('youtube.com', 'youtu.be'), 'https://www.youtube.com/@'),
    'instagram': (('instagram.com',), 'https://www.instagram.com/'),
    'facebook': (('facebook.com', 'fb.com'), 'https://www.facebook.com/'),
    'linkedin': (('linkedin.com',), 'https://www.linkedin.com/in/'),
    'x': (('x.com', 'twitter.com'), 'https://x.com/'),
    'tiktok': (('tiktok.com',), 'https://www.tiktok.com/@'),
    'github': (('github.com',), 'https://github.com/'),
    'pinterest': (('pinterest.com',), 'https://www.pinterest.com/'),
    'telegram': (('t.me', 'telegram.me'), 'https://t.me/'),
    'whatsapp': (('wa.me', 'whatsapp.com'), 'https://wa.me/'),
}


def social_url(platform: str, value: str) -> str:
    domains, prefix = PLATFORMS[platform]
    value = value.strip()
    if platform == 'whatsapp' and re.fullmatch(r'\+?[0-9() .-]{7,30}',value):
        value = re.sub(r'[() .-]','',value)
    error = f'Enter a valid {platform.title()} handle or profile URL.'
    if not value or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value) or '\\' in value:
        raise ValueError(error)
    # Treat only a known host as a URL without a scheme. A dot in a handle is valid.
    host = value.split('/', 1)[0].lower().rstrip('.')
    if any(host == d or host.endswith('.' + d) for d in domains):
        value = 'https://' + value
    if '://' in value:
        try:
            parsed = urlsplit(value)
            host = (parsed.hostname or '').lower().rstrip('.')
            if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
                raise ValueError(error)
            if not any(host == domain or host.endswith('.' + domain) for domain in domains):
                raise ValueError(error)
            # Encode international path characters; preserve video/post queries and fragments.
            return urlunsplit((parsed.scheme, parsed.netloc, quote(parsed.path, safe='/@%:._-~'), parsed.query, parsed.fragment))
        except ValueError:
            raise ValueError(error) from None
    handle = value.lstrip('@').strip('/')
    if platform == 'whatsapp':
        number = handle.lstrip('+')
        if not re.fullmatch(r'[0-9]{7,15}', number):
            raise ValueError('Enter a WhatsApp number with its country code, or a WhatsApp URL.')
        return prefix + number
    if platform == 'linkedin' and handle.startswith(('in/', 'company/', 'school/')):
        if not re.fullmatch(r'(in|company|school)/[\w.-]+/?', handle):
            raise ValueError(error)
        return 'https://www.linkedin.com/' + quote(handle, safe='/.-_')
    if platform == 'youtube' and handle.startswith(('channel/', 'c/', 'user/')):
        if not re.fullmatch(r'(channel|c|user)/[\w.-]+/?', handle):
            raise ValueError(error)
        return 'https://www.youtube.com/' + quote(handle, safe='/.-_')
    if not re.fullmatch(r'[\w.-]+', handle) or handle in ('.', '..'):
        raise ValueError(error + ' Use the account handle rather than its display name.')
    # A YouTube channel ID is distinct from a handle.
    if platform == 'youtube' and re.fullmatch(r'UC[A-Za-z0-9_-]{22}', handle):
        return 'https://www.youtube.com/channel/' + handle
    return prefix + quote(handle, safe='._-')
