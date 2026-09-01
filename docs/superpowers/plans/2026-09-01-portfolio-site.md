# Portfolio Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page static portfolio site at the repo root that GitHub Pages serves directly, with no build step.

**Architecture:** One `index.html` holding six sections, one `style.css` holding all styling, and a stdlib-only Python script that verifies the HTML is well-formed and every internal link resolves. There is no JavaScript on the page and no dependency to install. The page is authored dark-first and switches color scheme via `prefers-color-scheme`.

**Tech Stack:** HTML5, CSS3 (custom properties, grid, `prefers-color-scheme`, `prefers-reduced-motion`), Google Fonts via `<link>`, Python 3 stdlib for the verification script.

**Spec:** `docs/superpowers/specs/2026-09-01-portfolio-site-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **No build step.** Do not create `package.json`, a lockfile, `node_modules`, or a `.github/workflows/` file.
- **No JavaScript on the page.** `index.html` must contain no `<script>` tag. The page must render and function fully with JS disabled.
- **All paths relative.** Never write a leading-slash path (`/style.css`). Use `style.css`, `assets/resume.pdf`. This is what lets the site work both at `/kcotiruPortfolio/` and at the domain root after the repo rename.
- **Accessibility, non-negotiable:** semantic landmarks (`header`, `nav`, `main`, `section`, `footer`); exactly one `<h1>`; heading levels descend without skipping; visible focus indicator on every interactive element; WCAG AA contrast in both color schemes; meaningful `alt` on content images and `alt=""` on decorative ones; fully keyboard navigable.
- **Theming via `prefers-color-scheme` only.** No theme toggle, no persisted preference.
- **All motion guarded** by `@media (prefers-reduced-motion: no-preference)`.
- **Placeholders annotated** as `<!-- REPLACE: description -->` immediately above the element they describe.
- **`check.py` uses the Python standard library only.** No pip installs.
- **Commit at the end of every task**, using the message given in that task's final step.

---

### Task 1: Verification script and repo scaffolding

Builds the check that every later task runs. Written first so every subsequent task has a working gate.

**Files:**
- Create: `check.py`
- Create: `test_check.py`
- Create: `.nojekyll`
- Create: `index.html`
- Create: `style.css` (empty; filled in Task 2)
- Create: `assets/.gitkeep`

**Interfaces:**
- Consumes: nothing.
- Produces: `check.py`, runnable as `python check.py`, exiting `0` on success and `1` on failure. Three functions imported by `test_check.py`:
  - `check_markup(html: str) -> list[str]` — error strings for unbalanced or misnested tags. Empty list means valid.
  - `check_links(html: str, root: pathlib.Path) -> list[str]` — error strings for internal `href`/`src` values that do not resolve to an existing file, and for `#fragment` links with no matching `id` in the document.
  - `find_placeholders(html: str) -> list[tuple[int, str]]` — `(line_number, description)` for every `<!-- REPLACE: ... -->` comment.

- [ ] **Step 1: Write the failing test**

Create `test_check.py`:

```python
"""Run with: python test_check.py"""
import pathlib
import tempfile

from check import check_links, check_markup, find_placeholders

VALID = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>t</title>
<link rel="stylesheet" href="style.css"></head>
<body><main><section id="work"><h1>Hi</h1>
<p>See <a href="#work">work</a> and <a href="https://example.com">out</a>.</p>
<img src="assets/pic.png" alt="a picture">
<br>
</section></main></body></html>
"""


def test_valid_markup_has_no_errors():
    assert check_markup(VALID) == []


def test_unclosed_tag_is_reported():
    errors = check_markup("<body><div><p>hi</p></body>")
    assert errors, "expected an error for the unclosed <div>"
    assert any("div" in e for e in errors)


def test_mismatched_close_is_reported():
    errors = check_markup("<body><div>hi</span></div></body>")
    assert any("span" in e for e in errors)


def test_void_elements_need_no_close():
    assert check_markup("<body><br><img src='a.png' alt=''><hr></body>") == []


def test_missing_asset_is_reported():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "style.css").write_text("")
        errors = check_links(VALID, root)
        assert any("assets/pic.png" in e for e in errors)
        assert not any("style.css" in e for e in errors)


def test_present_asset_is_not_reported():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "style.css").write_text("")
        (root / "assets").mkdir()
        (root / "assets" / "pic.png").write_text("")
        assert check_links(VALID, root) == []


def test_external_and_mailto_links_are_skipped():
    html = '<body><a href="https://x.com">x</a><a href="mailto:a@b.c">m</a></body>'
    with tempfile.TemporaryDirectory() as d:
        assert check_links(html, pathlib.Path(d)) == []


def test_dangling_fragment_is_reported():
    html = '<body><a href="#nope">x</a><section id="yes"></section></body>'
    with tempfile.TemporaryDirectory() as d:
        errors = check_links(html, pathlib.Path(d))
        assert any("#nope" in e for e in errors)


def test_placeholders_are_found_with_line_numbers():
    html = "<body>\n<!-- REPLACE: your name -->\n<h1>x</h1>\n"
    assert find_placeholders(html) == [(2, "your name")]


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            passed += 1
            print(f"  ok  {name}")
    print(f"\n{passed} passed")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python test_check.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'check'`

- [ ] **Step 3: Write the implementation**

Create `check.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python test_check.py`
Expected: PASS — `9 passed`

- [ ] **Step 5: Create the scaffolding files**

`.nojekyll` tells GitHub Pages to serve the files as-is instead of running them through Jekyll. `style.css` is created empty here so the stylesheet link resolves; Task 2 fills it.

```bash
touch .nojekyll style.css
mkdir -p assets && touch assets/.gitkeep
```

Create `index.html` — skeleton only; sections arrive in later tasks:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>kcotiru</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
<h1>kcotiru</h1>
</main>
</body>
</html>
```

- [ ] **Step 6: Run the check against the real page**

Run: `python check.py`
Expected: exit 0, printing `OK: markup well-formed, all internal links resolve`. No placeholders are reported at this stage.

- [ ] **Step 7: Commit**

```bash
git add check.py test_check.py .nojekyll index.html style.css assets/.gitkeep
git commit -m "Add verification script and page scaffolding"
```

---

### Task 2: Design system in style.css

All visual tokens and base element styling. No section-specific rules yet.

**Files:**
- Modify: `style.css` (currently empty)
- Modify: `index.html` (add the font `<link>` tags to `<head>`)

**Interfaces:**
- Consumes: the `index.html` skeleton from Task 1.
- Produces: CSS custom properties and utility classes that every later task uses **by these exact names**:
  - Color: `--bg`, `--surface`, `--border`, `--text`, `--muted`, `--accent`, `--accent-ink` (readable text placed *on* the accent color).
  - Type: `--font-display`, `--font-body`, `--font-mono`.
  - Space: `--space-1` through `--space-6`, `--measure` (max line length for body copy), `--radius`.
  - Classes: `.wrap` (centered max-width container), `.section` (vertical rhythm), `.eyebrow` (small uppercase label above a heading), `.btn` and `.btn--ghost` (the two CTA styles), `.visually-hidden`, `.skip-link`.

- [ ] **Step 1: Add the font links to index.html**

Insert these two lines into `<head>`, immediately **above** the existing `<link rel="stylesheet" href="style.css">` so fonts load first:

```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap">
```

- [ ] **Step 2: Write style.css**

Replace the entire contents of `style.css`:

```css
/* ---- tokens ------------------------------------------------------ */
:root {
  --font-display: "Space Grotesk", "Segoe UI", system-ui, sans-serif;
  --font-body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "Cascadia Code", "SF Mono", Menlo, monospace;

  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 1rem;
  --space-4: 1.75rem;
  --space-5: 3rem;
  --space-6: 5.5rem;

  --measure: 62ch;
  --radius: 10px;

  /* dark is the default design */
  --bg: #0d0f12;
  --surface: #161a20;
  --border: #272d36;
  --text: #e9ecf1;
  --muted: #a3adbb;
  --accent: #ffb454;
  --accent-ink: #1a1206;
}

@media (prefers-color-scheme: light) {
  :root {
    --bg: #faf9f7;
    --surface: #ffffff;
    --border: #e2ded8;
    --text: #17191d;
    --muted: #555b68;
    --accent: #9a5400;
    --accent-ink: #ffffff;
  }
}

/* ---- base -------------------------------------------------------- */
*, *::before, *::after { box-sizing: border-box; }

html { color-scheme: dark light; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: clamp(1rem, 0.96rem + 0.2vw, 1.0625rem);
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3 {
  font-family: var(--font-display);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 var(--space-3);
  text-wrap: balance;
}

h1 { font-size: clamp(2.4rem, 1.6rem + 3.6vw, 4.25rem); }
h2 { font-size: clamp(1.6rem, 1.3rem + 1.3vw, 2.25rem); }
h3 { font-size: 1.15rem; }

p { margin: 0 0 var(--space-3); max-width: var(--measure); }

a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }

img { max-width: 100%; height: auto; display: block; }

ul { padding-left: 1.1em; }

:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 3px;
  border-radius: 2px;
}

/* ---- layout ------------------------------------------------------ */
.wrap {
  width: 100%;
  max-width: 68rem;
  margin-inline: auto;
  padding-inline: var(--space-4);
}

.section { padding-block: var(--space-6); }

.section + .section { border-top: 1px solid var(--border); }

/* ---- pieces ------------------------------------------------------ */
.eyebrow {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 var(--space-2);
}

.btn {
  display: inline-block;
  padding: 0.7em 1.4em;
  border: 1px solid var(--accent);
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--accent-ink);
  font-weight: 600;
  text-decoration: none;
}

.btn--ghost {
  background: transparent;
  color: var(--text);
  border-color: var(--border);
}

.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.skip-link {
  position: absolute;
  left: var(--space-3);
  top: -4rem;
  z-index: 10;
  padding: 0.6em 1.1em;
  background: var(--accent);
  color: var(--accent-ink);
  border-radius: var(--radius);
  font-weight: 600;
  text-decoration: none;
}

.skip-link:focus { top: var(--space-3); }

/* ---- motion ------------------------------------------------------ */
@media (prefers-reduced-motion: no-preference) {
  html { scroll-behavior: smooth; }
  .btn, a { transition: background-color 140ms ease, color 140ms ease, border-color 140ms ease; }
  .btn:hover { background: transparent; color: var(--accent); }
  .btn--ghost:hover { border-color: var(--accent); color: var(--accent); }
}
```

- [ ] **Step 3: Verify the check still passes**

Run: `python check.py`
Expected: exit 0. The Google Fonts URLs are external and are correctly skipped by `check_links`.

- [ ] **Step 4: Confirm both color schemes render**

Open `index.html` in a browser. Toggle the color scheme (Chrome DevTools → Rendering panel → "Emulate CSS media feature prefers-color-scheme"). Confirm background and text both flip and that text stays clearly readable in each.

- [ ] **Step 5: Commit**

```bash
git add style.css index.html
git commit -m "Add design tokens and base styles"
```

---

### Task 3: Header, hero, and about

The first screen, plus the navigation that reaches every later section.

**Files:**
- Modify: `index.html`
- Modify: `style.css` (append header and hero rules)

**Interfaces:**
- Consumes: tokens and utility classes from Task 2 — `.wrap`, `.section`, `.eyebrow`, `.btn`, `.btn--ghost`, `.skip-link`.
- Produces: the `id="main"` and `id="about"` anchors.
- **Expected intermediate failure:** the nav links to `#work`, `#experience`, `#services`, and `#contact`, and those sections do not exist until Tasks 4–6. `check.py` will report them as dangling fragments and exit 1. This is correct at this stage and is resolved by Task 6. Do not "fix" it by deleting nav links.

- [ ] **Step 1: Replace the `<body>` of index.html**

```html
<body>
<a class="skip-link" href="#main">Skip to content</a>

<header class="wrap site-head">
  <a class="site-mark" href="#main">kcotiru</a>
  <nav aria-label="Sections">
    <ul class="nav-list">
      <li><a href="#work">Work</a></li>
      <li><a href="#experience">Experience</a></li>
      <li><a href="#services">Hire me</a></li>
      <li><a href="#contact">Contact</a></li>
    </ul>
  </nav>
</header>

<main id="main">

  <section class="section wrap hero">
    <!-- REPLACE: your role headline, one line, what you build and for whom -->
    <p class="eyebrow">Software engineer &middot; AI/ML</p>
    <h1>I build software that puts machine learning to work.</h1>
    <!-- REPLACE: two sentences on what you do and the outcome people get -->
    <p class="hero-lede">
      I design and ship backend systems and the models behind them &mdash;
      from data pipeline to deployed endpoint. Currently open to engineering
      roles and to selected freelance work.
    </p>
    <p class="hero-actions">
      <a class="btn" href="#work">See the work</a>
      <a class="btn btn--ghost" href="#services">Hire me for a project</a>
    </p>
  </section>

  <section class="section wrap" id="about" aria-labelledby="about-h">
    <p class="eyebrow">About</p>
    <h2 id="about-h">Background</h2>
    <!-- REPLACE: 3-4 sentences. Where you came from, what you are good at, what you are looking for. -->
    <p>
      I work across the whole path a model takes into production: shaping the
      data, training and evaluating, then building the service that serves it
      under real load. Most of my time goes to Python and TypeScript.
    </p>
    <p>
      I care about systems that stay understandable a year after they ship,
      which usually means fewer moving parts than the first design suggested.
    </p>
  </section>

</main>
</body>
```

- [ ] **Step 2: Append the header and hero styles to style.css**

```css
/* ---- header ------------------------------------------------------ */
.site-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  justify-content: space-between;
  padding-block: var(--space-3);
}

.site-mark {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--text);
  text-decoration: none;
  letter-spacing: -0.01em;
}

.nav-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.9375rem;
}

.nav-list a { color: var(--muted); text-decoration: none; }
.nav-list a:hover { color: var(--text); }

/* ---- hero -------------------------------------------------------- */
.hero { padding-block: var(--space-6) var(--space-5); }

.hero-lede {
  font-size: 1.15rem;
  color: var(--muted);
  max-width: 54ch;
  margin-bottom: var(--space-4);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  max-width: none;
}
```

- [ ] **Step 3: Run the check**

Run: `python check.py`
Expected: exit 1, with dangling-fragment errors for `#work`, `#experience`, `#services`, and `#contact`, plus a report of 3 placeholders. This is the expected intermediate state described in the Interfaces block above.

- [ ] **Step 4: Confirm the skip link and keyboard order**

Open `index.html`, click the address bar, then press Tab. The first Tab must reveal the "Skip to content" link. Keep tabbing and confirm every nav link and both hero buttons show a clearly visible focus outline.

- [ ] **Step 5: Commit**

```bash
git add index.html style.css
git commit -m "Add header, hero, and about sections"
```

---

### Task 4: Work section

The shared proof both audiences read. Three placeholder project cards.

**Files:**
- Modify: `index.html`
- Modify: `style.css` (append card rules)

**Interfaces:**
- Consumes: tokens and `.wrap` / `.section` / `.eyebrow` from Task 2.
- Produces: the `id="work"` anchor, and the `.cards` / `.card` / `.card-title` / `.card-body` / `.tags` / `.tag` / `.card-links` / `.section-lede` classes that Task 5 reuses for its services grid.

- [ ] **Step 1: Insert the work section into index.html**

Place this immediately **after** the closing `</section>` of the `about` section and before `</main>`:

```html
  <section class="section wrap" id="work" aria-labelledby="work-h">
    <p class="eyebrow">Work</p>
    <h2 id="work-h">Selected projects</h2>
    <p class="section-lede">
      <!-- REPLACE: one line framing what these projects have in common -->
      Three things I built end to end, with the reasoning behind each.
    </p>

    <ul class="cards">
      <!-- REPLACE: project 1 - name, what it does, why it mattered, links -->
      <li class="card">
        <h3 class="card-title">Retrieval service for internal docs</h3>
        <p class="card-body">
          A search API over ten years of internal documentation. Cut median
          answer-finding time from minutes to seconds by pairing a vector index
          with a strict citation requirement, so answers stay checkable.
        </p>
        <p class="tags">
          <span class="tag">Python</span>
          <span class="tag">FastAPI</span>
          <span class="tag">pgvector</span>
        </p>
        <p class="card-links">
          <a href="https://github.com/kcotiru">Source</a>
        </p>
      </li>

      <!-- REPLACE: project 2 - name, what it does, why it mattered, links -->
      <li class="card">
        <h3 class="card-title">Forecasting pipeline for demand planning</h3>
        <p class="card-body">
          Nightly pipeline producing per-SKU demand forecasts, with backtests
          run on every model change. Replaced a spreadsheet process that took a
          day each week.
        </p>
        <p class="tags">
          <span class="tag">Python</span>
          <span class="tag">Airflow</span>
          <span class="tag">scikit-learn</span>
        </p>
        <p class="card-links">
          <a href="https://github.com/kcotiru">Source</a>
        </p>
      </li>

      <!-- REPLACE: project 3 - name, what it does, why it mattered, links -->
      <li class="card">
        <h3 class="card-title">Realtime dashboard for a small team</h3>
        <p class="card-body">
          A single-page operations view fed by a websocket stream. Built to be
          boring on purpose: no framework, no state library, and no pager calls
          in the eight months since.
        </p>
        <p class="tags">
          <span class="tag">TypeScript</span>
          <span class="tag">Postgres</span>
        </p>
        <p class="card-links">
          <a href="https://github.com/kcotiru">Source</a>
        </p>
      </li>
    </ul>
  </section>
```

- [ ] **Step 2: Append the card styles to style.css**

```css
/* ---- cards ------------------------------------------------------- */
.section-lede { color: var(--muted); margin-bottom: var(--space-4); }

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr));
  gap: var(--space-3);
  list-style: none;
  margin: 0;
  padding: 0;
}

.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.card-title { margin: 0; }

.card-body { color: var(--muted); margin: 0; max-width: none; }

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: auto 0 0;
  max-width: none;
}

.tag {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.25em 0.6em;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--muted);
}

.card-links { margin: 0; max-width: none; font-size: 0.9375rem; }
```

- [ ] **Step 3: Run the check**

Run: `python check.py`
Expected: exit 1, but the `#work` error is now gone. Remaining errors: `#experience`, `#services`, `#contact`. Placeholder count rises to 7.

- [ ] **Step 4: Confirm the grid collapses**

Open `index.html` and narrow the window below roughly 600px. The three cards must stack into one column with no horizontal scrollbar on the page.

- [ ] **Step 5: Commit**

```bash
git add index.html style.css
git commit -m "Add work section with project cards"
```

---

### Task 5: Experience and services

The two audience exits: a recruiter track and a client track, both sitting after the shared proof.

**Files:**
- Modify: `index.html`
- Modify: `style.css` (append role-list and services rules)
- Create: `assets/resume.pdf`

**Interfaces:**
- Consumes: tokens and `.btn` / `.btn--ghost` from Task 2; `.cards`, `.card`, `.card-title`, `.card-body`, `.section-lede` from Task 4.
- Produces: the `id="experience"` and `id="services"` anchors.

- [ ] **Step 1: Create a placeholder resume file**

`check.py` verifies that `assets/resume.pdf` exists, so a real file must be there. Write a minimal structurally valid one-page PDF:

```bash
python - <<'PY'
import pathlib
pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
trailer<</Root 1 0 R>>
%%EOF
"""
pathlib.Path("assets/resume.pdf").write_bytes(pdf)
print("placeholder resume.pdf written")
PY
```

- [ ] **Step 2: Insert both sections into index.html**

Place this immediately after the closing `</section>` of the `work` section:

```html
  <section class="section wrap" id="experience" aria-labelledby="experience-h">
    <p class="eyebrow">Experience</p>
    <h2 id="experience-h">Where I have worked</h2>

    <ol class="roles">
      <!-- REPLACE: role 1 - title, employer, dates, two lines on what you did -->
      <li class="role">
        <p class="role-when">2023 &ndash; present</p>
        <div class="role-what">
          <h3>Software Engineer &middot; Company Name</h3>
          <p>
            Own the services behind the recommendation surface. Took p99 latency
            from 800ms to 120ms by moving inference off the request path.
          </p>
        </div>
      </li>

      <!-- REPLACE: role 2 - title, employer, dates, two lines on what you did -->
      <li class="role">
        <p class="role-when">2021 &ndash; 2023</p>
        <div class="role-what">
          <h3>Backend Engineer &middot; Earlier Company</h3>
          <p>
            Built and maintained the data ingest for a customer-facing analytics
            product, and the on-call runbooks that kept it quiet.
          </p>
        </div>
      </li>
    </ol>

    <p><a class="btn btn--ghost" href="assets/resume.pdf">Download resume (PDF)</a></p>
  </section>

  <section class="section wrap" id="services" aria-labelledby="services-h">
    <p class="eyebrow">Freelance</p>
    <h2 id="services-h">Work I take on</h2>
    <p class="section-lede">
      <!-- REPLACE: one line on the kind of client engagement you want -->
      Short, scoped engagements where the goal is something running in
      production, not a slide deck.
    </p>

    <ul class="cards">
      <!-- REPLACE: service 1 - what you offer and what the client walks away with -->
      <li class="card">
        <h3 class="card-title">Ship an ML feature</h3>
        <p class="card-body">
          From a defined problem to a deployed, monitored endpoint your team can
          maintain after I leave. Typically four to eight weeks.
        </p>
      </li>

      <!-- REPLACE: service 2 - what you offer and what the client walks away with -->
      <li class="card">
        <h3 class="card-title">Untangle an existing system</h3>
        <p class="card-body">
          A read of what you have, a written plan for what to cut, and the first
          slice of that plan actually implemented.
        </p>
      </li>

      <!-- REPLACE: service 3 - what you offer and what the client walks away with -->
      <li class="card">
        <h3 class="card-title">Build the thing</h3>
        <p class="card-body">
          Backend and data work for teams without the headcount for it yet.
          Scoped up front, priced per project.
        </p>
      </li>
    </ul>

    <p class="services-cta">
      <!-- REPLACE: your real email address -->
      <a class="btn" href="mailto:kcotiru@gmail.com?subject=Freelance%20enquiry">Start a project</a>
    </p>
  </section>
```

- [ ] **Step 3: Append the styles to style.css**

```css
/* ---- roles ------------------------------------------------------- */
.roles {
  list-style: none;
  margin: 0 0 var(--space-4);
  padding: 0;
  display: grid;
  gap: var(--space-4);
}

.role {
  display: grid;
  grid-template-columns: 10rem 1fr;
  gap: var(--space-3);
  align-items: start;
}

.role-when {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--muted);
  margin: 0.35rem 0 0;
  letter-spacing: 0.03em;
}

.role-what h3 { margin-bottom: var(--space-1); }
.role-what p { color: var(--muted); margin: 0; }

@media (max-width: 44rem) {
  .role { grid-template-columns: 1fr; gap: var(--space-1); }
  .role-when { margin-top: 0; }
}

.services-cta { margin-top: var(--space-4); }
```

- [ ] **Step 4: Run the check**

Run: `python check.py`
Expected: exit 1, with only `#contact` remaining as a dangling fragment. `assets/resume.pdf` resolves. Placeholder count rises to 14.

- [ ] **Step 5: Commit**

```bash
git add index.html style.css assets/resume.pdf
git commit -m "Add experience and services sections"
```

---

### Task 6: Contact, footer, README, and the final pass

Closes the last anchor, documents the repo, and takes the whole page green.

**Files:**
- Modify: `index.html`
- Modify: `style.css` (append contact and footer rules)
- Create: `README.md`

**Interfaces:**
- Consumes: everything from Tasks 2–5.
- Produces: the `id="contact"` anchor, which makes `check.py` exit 0 for the first time.

- [ ] **Step 1: Insert the contact section and footer into index.html**

The contact `<section>` goes immediately after the `services` section's closing `</section>`, still inside `<main>`. The `<footer>` goes **after** `</main>`, before `</body>`. The `</main>` line below already exists in the file — do not duplicate it.

```html
  <section class="section wrap" id="contact" aria-labelledby="contact-h">
    <p class="eyebrow">Contact</p>
    <h2 id="contact-h">Get in touch</h2>
    <p class="section-lede">
      Best by email &mdash; I answer within a day or two.
    </p>
    <ul class="contact-list">
      <!-- REPLACE: your real email address -->
      <li><a href="mailto:kcotiru@gmail.com">kcotiru@gmail.com</a></li>
      <!-- REPLACE: your GitHub profile URL -->
      <li><a href="https://github.com/kcotiru">github.com/kcotiru</a></li>
      <!-- REPLACE: your LinkedIn profile URL, or delete this line -->
      <li><a href="https://www.linkedin.com/in/kcotiru">linkedin.com/in/kcotiru</a></li>
    </ul>
  </section>

</main>

<footer class="wrap site-foot">
  <p>Built as plain HTML and CSS. <a href="https://github.com/kcotiru">Source</a>.</p>
</footer>
```

- [ ] **Step 2: Append the contact and footer styles to style.css**

```css
/* ---- contact & footer -------------------------------------------- */
.contact-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-2);
  font-size: 1.05rem;
}

.site-foot {
  padding-block: var(--space-4);
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.875rem;
}

.site-foot p { margin: 0; max-width: none; }
```

- [ ] **Step 3: Run the check — this is the first fully green run**

Run: `python check.py`
Expected: exit 0, `OK: markup well-formed, all internal links resolve`, followed by a list of 17 placeholders with their line numbers.

- [ ] **Step 4: Run the unit tests once more**

Run: `python test_check.py`
Expected: PASS — `9 passed`.

- [ ] **Step 5: Write README.md**

````markdown
# kcotiru.github.io

My portfolio. Plain HTML and CSS, no build step. GitHub Pages serves
`index.html` from the root of `main` — pushing to `main` publishes.

## Editing

Everything lives in two files: `index.html` for content, `style.css` for
looks. There is nothing to install and nothing to compile.

## Checking your work

```
python check.py       # markup is well-formed, every internal link resolves
python test_check.py  # tests for check.py itself
```

`check.py` also lists every remaining placeholder with its line number.
Placeholders never fail the check — they are a to-do list, not an error.

## Placeholders to replace

Run `python check.py` for the current list. Each one is marked in
`index.html` with a `<!-- REPLACE: ... -->` comment describing what belongs
there. Search for `REPLACE` to find them all.

## Setup notes

- Repo must be named `kcotiru.github.io` to serve at the domain root.
- Settings → Pages → deploy from `main`, `/` (root).
- `.nojekyll` stops GitHub Pages from running the files through Jekyll.
- All paths are relative, so the site works at a subpath too.
````

- [ ] **Step 6: Accessibility pass**

Confirm each of these by hand and fix anything that fails before committing:

1. **Heading order** — view the page outline. Exactly one `<h1>` (the hero), and every `<h2>`/`<h3>` descends without skipping a level.
2. **Keyboard** — Tab from the address bar through the entire page. The skip link appears first; every link and button shows a visible focus ring; nothing is reachable but invisible.
3. **Contrast** — in Chrome DevTools, inspect `.card-body` text and `.eyebrow` text against their backgrounds in **both** color schemes. Each must report at least 4.5:1. If `--muted` fails in either scheme, darken it in light mode or lighten it in dark mode until it passes.
4. **Zoom** — set browser zoom to 200%. No horizontal scrollbar on the page, no clipped text.
5. **No JavaScript** — disable JS in DevTools (Settings → Debugger → Disable JavaScript) and reload. The page must be unchanged.

- [ ] **Step 7: Commit**

```bash
git add index.html style.css README.md
git commit -m "Add contact section, footer, and README"
```

---

### Task 7: Publish

**Files:** none — this task is repository configuration.

- [ ] **Step 1: Push**

```bash
git push origin main
```

- [ ] **Step 2: Rename the repository (user action)**

Performed by the repository owner in the GitHub web UI, not by an agent:
GitHub → the repo → **Settings** → **Repository name** → change `kcotiruPortfolio` to `kcotiru.github.io` → **Rename**.

- [ ] **Step 3: Update the local remote to match**

```bash
git remote set-url origin https://github.com/kcotiru/kcotiru.github.io.git
git remote -v
```

- [ ] **Step 4: Enable Pages**

GitHub → the repo → **Settings** → **Pages** → Source: **Deploy from a branch** → Branch: `main`, folder `/ (root)` → **Save**.

- [ ] **Step 5: Verify the published site**

Wait about a minute, then open `https://kcotiru.github.io`. Confirm the page renders with styling (if it is unstyled, `style.css` returned a 404 — check that the path in `index.html` has no leading slash), and that every nav link scrolls to its section.
