from pathlib import Path


def test_google_site_verification_is_permanent_and_targets_document_head():
    source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'GOOGLE_SITE_VERIFICATION = "jkMhTjEet0DjQX3KZN_IcPw0JfZ4yDgTycbVsBe099s"' in source
    assert '<meta name="google-site-verification" content="jkMhTjEet0DjQX3KZN_IcPw0JfZ4yDgTycbVsBe099s" />' in source
    assert 'document.head.querySelector(`meta[name="${{name}}"]`)' in source
    assert 'document.head.appendChild(tag)' in source
    assert 'tag.setAttribute("content", content)' in source
    assert "unsafe_allow_javascript=True" in source
