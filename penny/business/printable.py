"""Deterministic offline printable checklist; content is always escaped."""
import base64
import logging
import struct
from html import escape
from zlib import crc32

from .brand import MAX_ARTWORK_BYTES

logger = logging.getLogger(__name__)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_envelope(artwork):
    """Bound image envelope/dimensions and chunk CRCs; not a full PNG decoder."""
    try:
        if type(artwork) is not bytes or not 45 <= len(artwork) <= MAX_ARTWORK_BYTES:
            return False
        if artwork[:8] != PNG_SIGNATURE:
            return False
        offset, seen_data, chunks = 8, False, 0
        while offset + 12 <= len(artwork) and chunks < 2048:
            size = struct.unpack_from(">I", artwork, offset)[0]
            end = offset + 12 + size
            if end > len(artwork):
                return False
            kind = artwork[offset+4:offset+8]
            payload = artwork[offset+8:end-4]
            if crc32(kind + payload) & 0xffffffff != struct.unpack_from(">I", artwork, end-4)[0]:
                return False
            if chunks == 0:
                if kind != b"IHDR" or size != 13:
                    return False
                w,h,depth,color,comp,filt,interlace = struct.unpack(">IIBBBBB",payload)
                if not (1 <= w <= 2048 and 1 <= h <= 2048 and comp == filt == 0
                        and interlace in (0,1) and depth in
                        {0:(1,2,4,8,16),2:(8,16),3:(1,2,4,8),4:(8,16),6:(8,16)}.get(color,())):
                    return False
            elif kind == b"IHDR":
                return False
            if kind == b"IDAT" and size:
                seen_data = True
            if kind == b"IEND":
                return seen_data and size == 0 and end == len(artwork)
            offset, chunks = end, chunks + 1
        return False
    except Exception as exc:
        logger.warning("Artwork envelope refused (%s)",type(exc).__name__)
        return False


def printable(content, artwork):
    """No remote resources, scripts, forms, links or model-selected HTML."""
    try:
        if not png_envelope(artwork) or type(content) is not str or len(content)>6000:
            return None
        lines = content.split("\n")
        if (len(lines)<8 or not lines[0] or lines[1]!="" or not lines[2]
                or lines[3]!="" or lines[-1]!="" or not 3<=len(lines[4:-1])<=12
                or any(not line.startswith("[ ] ") or not line[4:].strip() for line in lines[4:-1])):
            return None
        logo=base64.b64encode(artwork).decode("ascii")
        items="".join('<li><span aria-hidden="true">□</span> '+escape(line[4:])+'</li>\n'
                      for line in lines[4:-1])
        # Fixed print stylesheet; the only dynamic markup slots are escaped text
        # and a locally supplied approved PNG embedded as a data image.
        return ("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Penny's Workshop — Private review edition</title>
<style>
@page{margin:16mm}body{font:16px system-ui,sans-serif;color:#172c35;max-width:760px;margin:24px auto;padding:0 16px}
header{display:flex;gap:16px;align-items:center;border-bottom:2px solid #438779;padding-bottom:12px}
img{width:96px;height:96px;object-fit:contain}h1{font-size:1.65rem}li{list-style:none;margin:12px 0;break-inside:avoid;overflow-wrap:anywhere}ul{padding:0}
footer{margin-top:24px;border-top:1px solid #999;padding-top:10px;font-size:12px}
@media print{body{margin:0;padding:0}}
</style></head><body>
<header><img alt="Penny" src="data:image/png;base64,"""+logo+""""><div><strong>Penny's Workshop</strong><p>PRIVATE REVIEW EDITION — NOT FOR SALE</p></div></header>
<main><h1>"""+escape(lines[0])+"""</h1><p>"""+escape(lines[2])+"""</p><ul>"""+items+"""</ul></main>
<footer>Created by Penny · AI-assisted product, human-operated business.<br>Financially Underfunded. Sarcastically Overqualified.<br>Private proof; not a commercial release.</footer>
</body></html>
""").encode("utf-8")
    except Exception as exc:
        logger.error("Printable edition refused (%s)",type(exc).__name__)
        return None
