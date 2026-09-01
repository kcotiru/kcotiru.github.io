#!/usr/bin/env python3
"""Verify index.html: well-formed markup, resolvable internal links.

Run: python check.py
Exits 0 if the page is valid, 1 otherwise. Remaining REPLACE placeholders
are reported for information and never fail the check -- the site ships
with placeholders on purpose.
"""
import pathlib
import re
import sys
from html.parser import HTMLParser

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.ids = set()
        self.links = []  # (attr_value, line)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        for key in ("href", "src"):
            if d.get(key):
                self.links.append((d[key], self.getpos()[0]))
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # <br /> style self-closing tags: record attrs, never push on the stack
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        for key in ("href", "src"):
            if d.get(key):
                self.links.append((d[key], self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: stray </{tag}>")
            return
        open_tag, open_line = self.stack.pop()
        if open_tag != tag:
            self.errors.append(
                f"line {self.getpos()[0]}: </{tag}> closes <{open_tag}> "
                f"opened on line {open_line}"
            )


def _parse(html):
    p = _Markup()
    p.feed(html)
    p.close()
    errors = list(p.errors)
    for tag, line in p.stack:
        errors.append(f"line {line}: <{tag}> is never closed")
    return p, errors


def check_markup(html):
    """Return a list of error strings for unbalanced or misnested tags."""
    return _parse(html)[1]


def check_links(html, root):
    """Return errors for internal links that do not resolve."""
    parser, _ = _parse(html)
    errors = []
    for value, line in parser.links:
        if re.match(r"^(https?:|mailto:|tel:|data:|//)", value):
            continue
        if value.startswith("#"):
            if value[1:] and value[1:] not in parser.ids:
                errors.append(f"line {line}: {value} matches no id on the page")
            continue
        path = value.split("#")[0].split("?")[0]
        if path and not (root / path).exists():
            errors.append(f"line {line}: {path} does not exist")
    return errors


def find_placeholders(html):
    """Return (line_number, description) for each REPLACE comment."""
    out = []
    for i, line in enumerate(html.splitlines(), start=1):
        for m in re.finditer(r"<!--\s*REPLACE:\s*(.*?)\s*-->", line):
            out.append((i, m.group(1)))
    return out


def main():
    root = pathlib.Path(__file__).parent
    page = root / "index.html"
    if not page.exists():
        print("FAIL: index.html not found")
        return 1
    html = page.read_text(encoding="utf-8")

    errors = check_markup(html) + check_links(html, root)
    for e in errors:
        print(f"FAIL: {e}")

    placeholders = find_placeholders(html)
    if placeholders:
        print(f"\n{len(placeholders)} placeholder(s) still to fill:")
        for line, desc in placeholders:
            print(f"  index.html:{line}  {desc}")

    if errors:
        print(f"\n{len(errors)} error(s)")
        return 1
    print("\nOK: markup well-formed, all internal links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
