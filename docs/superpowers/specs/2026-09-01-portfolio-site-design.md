# Portfolio Site — Design

**Date:** 2026-09-01
**Status:** Approved
**Repo:** kcotiruPortfolio (to be renamed `kcotiru.github.io`)

## Purpose

A personal portfolio site hosted on GitHub Pages, serving two audiences at once:

1. **Recruiters and hiring managers** evaluating kcotiru for employment.
2. **Prospective freelance clients** evaluating kcotiru for contract work.

The work shown is software engineering with an AI/ML component.

## Success criteria

- A visitor of either audience can, within one screen of scrolling, tell what
  kcotiru does and see a path to act on it.
- The site loads and renders correctly with JavaScript disabled.
- Publishing an update requires editing one HTML file and pushing. No build
  step, no CI, no dependency updates.
- Every piece of placeholder content is findable with a single grep.

## Approach

Plain static HTML and CSS, served directly from the repository root by GitHub
Pages. No static site generator, no framework, no build pipeline.

**Why not a generator (Astro, Eleventy, Next):** the content volume is
undecided and there is no blog today. A generator buys a markdown pipeline and
component reuse for content that does not exist yet. The migration cost from a
single hand-written page to a generator is small precisely because the content
is small — so the option stays open at near-zero carrying cost. Adopt one when
a blog is actually being written, not in anticipation of one.

**Why not a data-driven card array (`projects.js`):** three project cards do
not justify a rendering layer, and it would break the no-JS requirement. This
is the designated first upgrade: introduce it when copy-pasting a card becomes
annoying, which is somewhere past the fourth project.

## Information architecture

One page, one column, sections in this order:

| Section | Content | Serves |
|---|---|---|
| Hero | Name, one-line role statement, two CTAs: "See work" and "Hire me" | Both |
| About | 3–4 sentences framing software engineering + AI/ML | Both |
| Work | Project cards — descriptions, tech tags, links to repo/demo | Both |
| Experience | Reverse-chronological roles, link to resume PDF | Recruiters |
| Services | Freelance engagements offered, contact CTA | Clients |
| Contact | Email (`mailto:`), GitHub, LinkedIn | Both |

The dual audience is handled by **splitting the call to action, not the
evidence**. Both audiences want proof of building ability, so a single Work
section serves both. They diverge only in what they do next, so Experience and
Services sit after Work as two distinct exits.

Rejected alternative: separate "for recruiters" and "for clients" pages. That
duplicates the project content into two places that then drift apart.

## Files

```
index.html      The entire page
style.css       All styling
assets/         resume.pdf, project images, favicon
README.md       What this is, and how to edit it
.nojekyll       Prevents GitHub Pages from running the content through Jekyll
```

No `package.json`, no lockfile, no workflow file.

## Visual direction

- Dark-first palette with a single accent color used sparingly, for CTAs and
  links.
- Light and dark handled with `prefers-color-scheme`. No theme toggle — a
  toggle requires JavaScript and persisted state to serve a preference the
  operating system already reports.
- One display typeface for headings, one clean sans for body text, loaded via
  `<link>` from Google Fonts. Both declare a real system fallback stack so the
  page is legible before and without webfonts.
- Generous whitespace; measured line length on body copy.
- Project cards in a CSS grid that collapses to a single column on narrow
  viewports.
- Interaction limited to CSS transitions on hover and focus. All motion is
  wrapped in a `prefers-reduced-motion: no-preference` guard.

## Accessibility requirements

These are not optional and are not to be simplified away:

- Semantic landmarks: `header`, `nav`, `main`, `section`, `footer`.
- One `h1`; heading levels descend without skipping.
- Visible focus indicators on every interactive element.
- Text and interactive elements meet WCAG AA contrast in both color schemes.
- All images carry meaningful `alt` text; decorative images use `alt=""`.
- The page is fully navigable by keyboard.

## Placeholder content

The site ships with realistic placeholder copy — a plausible role headline,
three plausible projects, two plausible roles — rather than `Lorem ipsum`.
Real-shaped prose reveals whether the layout actually holds content; lorem
does not.

Every placeholder is annotated with an HTML comment in the form:

```html
<!-- REPLACE: short description of what goes here -->
```

so that `grep -rn REPLACE .` enumerates everything still fake. `README.md`
lists the replacement checklist.

## Deployment

GitHub Pages, deploying from the `main` branch, root directory. A push to
`main` publishes. No GitHub Actions workflow.

**Manual step required by the user:** rename the repository from
`kcotiruPortfolio` to `kcotiru.github.io` in GitHub repository settings, which
makes it a user site at `https://kcotiru.github.io`. Once renamed, the local
git remote URL is updated to match.

All asset and link paths are written **relative** regardless, so the site
works correctly both at the subpath (`/kcotiruPortfolio/`) before the rename
and at the root after it. The rename cannot break the site.

## Verification

One runnable check, no test framework, that asserts:

1. `index.html` parses as well-formed HTML.
2. Every internal `href` and `src` resolves to a file that exists on disk.

It also **reports** the count and location of remaining `REPLACE` markers.
That report is informational and does not fail the check — the site ships
with placeholders on purpose, so a leftover marker is a status, not an error.

Run with a single command. It exits non-zero on 1 or 2.

## Explicitly out of scope

| Excluded | Reason | Add when |
|---|---|---|
| Contact form | Requires a backend or a third-party service | `mailto:` proves insufficient |
| Blog | No posts written | Two posts exist in draft |
| Analytics | Not a stated goal; adds a tracker and a privacy surface | Traffic decisions actually depend on it |
| Theme toggle | `prefers-color-scheme` covers it without JS | Never, most likely |
| JS framework | The page has no state | The page acquires state |
| Custom domain | Not owned | A domain is purchased |
