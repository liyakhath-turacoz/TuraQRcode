"""Standards-based linear barcodes, with consistent PNG/SVG/PDF exports."""
import io
import re
import sys
from importlib import import_module, util
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from urllib.parse import urlsplit


def _load_encoder():
    try:
        module = import_module('barcode')
        if callable(getattr(module, 'get_barcode_class', None)):
            return module
    except (ImportError, ModuleNotFoundError):
        pass
    try:
        package_dir = Path(distribution('python-barcode').locate_file('barcode'))
    except PackageNotFoundError as exc:
        raise ImportError('Install backend/requirements.txt to enable barcode generation.') from exc
    init_file = package_dir / '__init__.py'
    spec = util.spec_from_file_location('barcode', init_file, submodule_search_locations=[str(package_dir)])
    if not spec or not spec.loader:
        raise ImportError('The barcode generator could not be loaded. Reinstall the backend dependencies.')
    for name in tuple(sys.modules):
        if name == 'barcode' or name.startswith('barcode.'):
            del sys.modules[name]
    module = util.module_from_spec(spec)
    sys.modules['barcode'] = module
    spec.loader.exec_module(module)
    if not callable(getattr(module, 'get_barcode_class', None)):
        raise ImportError('The installed barcode package is incompatible. Reinstall backend/requirements.txt.')
    return module


barcode = _load_encoder()
from barcode.writer import ImageWriter, SVGWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

FORMATS={'code128':'code128','code39':'code39','ean13':'ean13','ean8':'ean8','upca':'upca'}


def symbol(content,writer=None):
    cls=barcode.get_barcode_class(FORMATS[content['format']])
    return cls(content['value'],writer=writer,**({'add_checksum':False} if content['format']=='code39' else {}))


def validate_barcode(content):
    if set(content)-{'format','value','show_text','tracked'}: raise ValueError('Unsupported barcode options.')
    fmt=content.get('format','code128'); value=content.get('value','')
    if fmt not in FORMATS or not isinstance(value,str): raise ValueError('Choose a supported barcode format and enter its value.')
    if not isinstance(content.get('show_text',True),bool): raise ValueError('Choose whether to display the barcode value.')
    if not isinstance(content.get('tracked',False),bool): raise ValueError('Choose whether barcode scan measurement is enabled.')
    tracked=content.get('tracked',False)
    if tracked:
        try: parsed=urlsplit(value)
        except ValueError: parsed=None
        if fmt!='code128' or not parsed or parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or len(value)>2048:
            raise ValueError('Tracked barcodes need a Code 128 format and a valid http:// or https:// destination.')
    if not value or len(value)>(2048 if tracked else 80):
        raise ValueError('The destination URL is too long.' if tracked else 'Enter a barcode value of 1–80 characters.')
    if fmt=='code128' and any(ord(c)<32 or ord(c)>126 for c in value):
        raise ValueError('Code 128 supports printable English letters, numbers, and punctuation.')
    if fmt=='code39' and not re.fullmatch(r'[A-Z0-9 .$/+%\-]+',value):
        raise ValueError('Code 39 supports uppercase letters, numbers, spaces, and - . $ / + %.')
    if fmt in ('ean13','ean8','upca'):
        length={'ean13':13,'ean8':8,'upca':12}[fmt]
        if not value.isascii() or not value.isdigit() or len(value) not in (length-1,length):
            raise ValueError(f'Enter {length-1} digits, or {length} digits including the check digit.')
        generated=symbol({'format':fmt,'value':value[:-1] if len(value)==length else value}).get_fullcode()
        if len(value)==length and value!=generated: raise ValueError('The barcode check digit is incorrect.')
        value=generated
    return {'format':fmt,'value':value,'show_text':content.get('show_text',True),'tracked':tracked}


def render_barcode(content,design,fmt='png',size=1024):
    options={'module_width':float(design.get('barcode_module_width',.3)),'module_height':float(design.get('barcode_height',22)),'quiet_zone':6.5,'font_size':int(design.get('barcode_font_size',11)),
             'write_text':content.get('show_text',True),'foreground':design.get('foreground','#163b75'),
             'background':design.get('background','#ffffff'),'dpi':300}
    out=io.BytesIO()
    from xml.etree import ElementTree as ET
    import resvg_py
    from .qr_render import font_files
    encoder=symbol(content,SVGWriter())
    encoder.write(out,options)
    document=ET.fromstring(out.getvalue())
    natural_width=float(document.get('width').removesuffix('mm'))
    natural_height=float(document.get('height').removesuffix('mm'))
    # Normalize all source lengths into the same millimetre viewBox before sizing.
    for element in document.iter():
        for key,value in list(element.attrib.items()):
            if value.endswith('mm'): element.set(key,value[:-2])
            elif key=='font-size' and value.endswith('pt'): element.set(key,str(float(value[:-2])*25.4/72))
            elif key=='style': element.set(key,re.sub(r'([\d.]+)pt',lambda match:str(float(match.group(1))*25.4/72),value))
        if element.tag.endswith('text'): element.set('font-family','Bitstream Vera Sans')
    bits=len(encoder.build()[0])
    width=max(size,round((bits+13/options['module_width'])*2))
    height=round(width*natural_height/natural_width)
    document.set('width',str(width));document.set('height',str(height))
    document.set('viewBox',f'0 0 {natural_width} {natural_height}')
    svg=ET.tostring(document,encoding='utf-8',xml_declaration=True)
    if fmt=='svg': return svg,'image/svg+xml'
    raw=resvg_py.svg_to_bytes(svg_string=svg.decode(),font_files=font_files(),skip_system_fonts=True)
    image=Image.open(io.BytesIO(raw)).convert('RGB')
    out=io.BytesIO()
    if fmt=='pdf':
        pdf=canvas.Canvas(out,pagesize=(width*72/300,height*72/300)); pdf.setTitle('TuraQRcode barcode')
        pdf.drawImage(ImageReader(image),0,0,width=width*72/300,height=height*72/300)
        pdf.showPage();pdf.save()
        return out.getvalue(),'application/pdf'
    image.save(out,'PNG',dpi=(300,300))
    return out.getvalue(),'image/png'
