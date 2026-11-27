"""Synthetic image fixtures only; never approve production brand assets."""
import struct
import unittest
from zlib import crc32,compress
from penny.business.printable import png_envelope,printable


def png_fixture():
    def chunk(kind,payload):
        return (struct.pack(">I",len(payload))+kind+payload+
                struct.pack(">I",crc32(kind+payload)&0xffffffff))
    return (b"\x89PNG\r\n\x1a\n"+
            chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,2,0,0,0))+
            chunk(b"IDAT",compress(b"\x00\xff\xff\xff"))+chunk(b"IEND",b""))


class PrintableTests(unittest.TestCase):
    def test_bounded_local_png_and_escaped_checklist(self):
        png=png_fixture()
        self.assertTrue(png_envelope(png))
        for bad in (b"<svg/>",png[:-1],png+b"extra",png[:20]+b"X"+png[21:]):
            self.assertFalse(png_envelope(bad))
        text="<script>alert(1)</script>\n\nUse & check\n\n[ ] One\n[ ] Two\n[ ] Three\n"
        output=printable(text,png)
        self.assertEqual(output,printable(text,png))
        self.assertIn(b"&lt;script&gt;",output)
        self.assertNotIn(b"<script>",output)
        self.assertIn(b"data:image/png;base64,",output)
        self.assertIn(b"NOT FOR SALE",output)
        self.assertIsNone(printable("invalid",png))
        self.assertIsNone(printable(text,b"<svg/>"))
