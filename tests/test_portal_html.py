from html.parser import HTMLParser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "web"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.lang = None; self.h1 = 0; self.images = []; self.canonical = None; self.title = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html": self.lang = attrs.get("lang")
        if tag == "h1": self.h1 += 1
        if tag == "img": self.images.append(attrs.get("alt"))
        if tag == "title": self.title += 1
        if tag == "link" and attrs.get("rel") == "canonical": self.canonical = attrs.get("href")


class PortalHtmlTests(unittest.TestCase):
    def test_each_page_has_language_title_heading_canonical_and_image_text(self):
        for path in sorted(ROOT.glob("*.html")):
            page = Page(); page.feed(path.read_text())
            with self.subTest(path=path.name):
                self.assertEqual(page.lang, "en")
                self.assertEqual(page.h1, 1)
                self.assertEqual(page.title, 1)
                if path.name != "404.html": self.assertTrue(page.canonical.startswith("https://recoverops.brutehack.com/"))
                self.assertTrue(all(alt and alt.strip() for alt in page.images))
    def test_svg_assets_are_well_formed_xml(self):
        ET.parse(ROOT / 'assets/architecture.svg')

    def test_project_identity_and_no_external_font_or_script_dependency(self):
        html = (ROOT / "index.html").read_text()
        css = (ROOT / "assets/site.css").read_text()
        self.assertIn('data-project="recoverops"', html)
        self.assertNotIn("fonts.googleapis.com", html + css)
        self.assertNotIn("<script", html.lower())
    def test_backup_and_platform_status_are_explicit(self):
        html = (ROOT / "index.html").read_text()
        readme = (ROOT.parent / "README.md").read_text()
        self.assertIn("DEFERRED", html)
        self.assertIn("DEFERRED / NOT IMPLEMENTED", readme)
        self.assertIn("REQUIRES DEDICATED VIRTUALIZATION HOST", readme)


if __name__ == "__main__": unittest.main()
