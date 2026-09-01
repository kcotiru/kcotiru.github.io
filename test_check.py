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
