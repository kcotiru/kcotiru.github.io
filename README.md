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
