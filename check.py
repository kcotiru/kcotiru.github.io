#!/usr/bin/env python3
"""Verify index.html: well-formed markup, no JavaScript, accessible headings
and images, resolvable internal links.

Run: python check.py
Exits 0 if the page is valid, 1 otherwise. Remaining REPLACE placeholders
are reported for information and never fail the check -- the site ships
with placeholders on purpose.
"""
import os
import pathlib
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# End tags HTML5 lets you omit. html.parser does no implied-end-tag handling,
# so without this the stack desynchronizes and errors cascade.
OPTIONAL_END = {"li", "p", "td", "tr", "option", "dt", "dd"}

HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.ids = set()
        self.links = []  # (attr_value, line)
        self.h1_count = 0
        self.last_level = 0

    def _element(self, tag, attrs):
        """Everything checked per element, however the tag was written."""
        line = self.getpos()[0]
        d = dict(attrs)

        if "id" in d:
            if d["id"] in self.ids:
                self.errors.append(f'line {line}: duplicate id "{d["id"]}"')
            self.ids.add(d["id"])

        for key in ("href", "src"):
            if d.get(key):
                self.links.append((d[key], line))

        # no JavaScript on the page -- non-negotiable
        if tag == "script":
            self.errors.append(f"line {line}: <script> found; the page must contain no JavaScript")
        for name in d:
            if name.startswith("on"):
                self.errors.append(
                    f"line {line}: inline handler {name}=; the page must contain no JavaScript"
                )

        # accessibility -- non-negotiable
        if tag == "img" and "alt" not in d:
            self.errors.append(f"line {line}: <img> has no alt attribute (alt=\"\" if decorative)")
        if tag in HEADINGS:
            level = int(tag[1])
            if level == 1:
                self.h1_count += 1
                if self.h1_count > 1:
                    self.errors.append(f"line {line}: extra <h1>; the page must have exactly one")
            if level > self.last_level + 1:
                seen = f"<h{self.last_level}>" if self.last_level else "no heading"
                self.errors.append(f"line {line}: <{tag}> skips a level (previous: {seen})")
            self.last_level = level

    def handle_starttag(self, tag, attrs):
        self._element(tag, attrs)
        if tag in VOID:
            return
        if tag in OPTIONAL_END and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()  # <li>a<li>b -- the first one implicitly closed
        self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # <br /> style self-closing tags: record attrs, never push on the stack
        self._element(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack and self.stack[-1][0] != tag and self.stack[-1][0] in OPTIONAL_END:
            self.stack.pop()  # </ul> implicitly closes the open <li>
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
    """Return errors for unbalanced tags, JavaScript, or accessibility faults."""
    return _parse(html)[1]


def _resolves(root, path):
    """True if path is a file whose on-disk name matches byte for byte.

    Path.exists() follows the filesystem's case rules: Windows and macOS are
    case-insensitive, the Linux host serving GitHub Pages is not. Compare each
    component against the real directory listing so a case mismatch is caught
    here rather than as a 404 after publishing.
    """
    cur = root
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            cur = cur.parent
            continue
        if not cur.is_dir() or part not in os.listdir(cur):
            return False
        cur = cur / part
    return cur.is_file()


def check_links(html, root):
    """Return errors for internal links that do not resolve."""
    parser, _ = _parse(html)
    errors = []
    for value, line in parser.links:
        if re.match(r"^(https?:|mailto:|tel:|data:|//)", value, re.IGNORECASE):
            continue
        if value.startswith("#"):
            if value[1:] and value[1:] not in parser.ids:
                errors.append(f"line {line}: {value} matches no id on the page")
            continue
        path = unquote(value.split("#")[0].split("?")[0])
        if not path:
            continue
        if path.startswith("/"):
            errors.append(f"line {line}: {path} is absolute; every path must be relative")
        elif not _resolves(root, path):
            errors.append(f"line {line}: {path} does not exist (or differs in case)")
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
        print(
            f"\n{len(placeholders)} placeholder(s) still to fill "
            f"-- DO NOT PUBLISH: this content is invented."
        )
        for line, desc in placeholders:
            print(f"  index.html:{line}  {desc}")

    if errors:
        print(f"\n{len(errors)} error(s)")
        return 1
    print("\nOK: markup well-formed, no JavaScript, headings and images sound, links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
