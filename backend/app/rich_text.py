"""A small, shared allowlist for public profile formatting."""
from html import escape
from html.parser import HTMLParser

import nh3

TAGS = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'code', 'sup', 'sub',
        'ul', 'ol', 'li', 'blockquote'}


def clean_rich_text(value: str) -> str:
    return nh3.clean(value, tags=TAGS, attributes={},
                     clean_content_tags={'script', 'style', 'iframe', 'object', 'svg', 'math'},
                     link_rel=None).strip()


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('p', 'li', 'blockquote'):
            self.parts.append('\n')


def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return ''.join(parser.parts).strip()


def profile_text(text: str, html: str | None = None) -> str:
    # Reapply the allowlist on output, including records saved before this release.
    if html:
        return clean_rich_text(html)
    return '<p>' + escape(text or '').replace('\n', '<br>') + '</p>'


def normalize_text(text: str, html: str, limit: int) -> tuple[str, str]:
    if not html:
        return text, ''
    cleaned = clean_rich_text(html)
    content = plain_text(cleaned)
    if len(content) > limit:
        raise ValueError(f'Keep this text to {limit:,} characters or fewer.')
    return content, cleaned if content else ''
