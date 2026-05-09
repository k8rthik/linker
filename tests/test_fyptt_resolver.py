"""Tests for the fyptt.to URL resolver."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from utils.fyptt_resolver import (
    is_fyptt_url,
    resolve_fyptt_stream_url,
)


_ARTICLE_HTML = """
<html><body>
<iframe data-src-no-ap="https://fyptt.to/fypttstr.php?fileid=ABC123&amp;mainurl=22224%2Ffoo"
        src="https://fyptt.to/fypttstr.php?fileid=ABC123&#038;mainurl=22224%2Ffoo">
</iframe>
</body></html>
"""

_IFRAME_HTML = """
<html><body>
<video controls>
  <source src="https://stream.fyptt.to/ABC123.mp4?token=tk&expires=1234567890"
          type="video/mp4" />
</video>
</body></html>
"""

# Variant used for longer videos: JWPlayer iframe at fypttjwstr.php with the
# stream URL embedded as `file:"..."` rather than a <source> tag.
_JW_ARTICLE_HTML = """
<html><body>
<iframe data-src-no-ap="https://fyptt.to/fypttjwstr.php?fileid=XYZ789&amp;mainurl=11362%2Ffoo"
        src="https://fyptt.to/fypttjwstr.php?fileid=XYZ789&#038;mainurl=11362%2Ffoo">
</iframe>
</body></html>
"""

_JW_IFRAME_HTML = """
<html><body><script>
jwplayer("player").setup({
  file:"https://stream.fyptt.to/XYZ789.mp4?token=jw&expires=9999999999",
  width:"100%"
});
</script></body></html>
"""


class TestIsFypttUrl:
    @pytest.mark.unit
    def test_fyptt_article_url(self) -> None:
        assert is_fyptt_url("https://fyptt.to/22224/foo/") is True

    @pytest.mark.unit
    def test_www_fyptt_url(self) -> None:
        assert is_fyptt_url("https://www.fyptt.to/22224/foo/") is True

    @pytest.mark.unit
    def test_other_domain(self) -> None:
        assert is_fyptt_url("https://example.com/22224/foo/") is False

    @pytest.mark.unit
    def test_malformed_url(self) -> None:
        assert is_fyptt_url("not-a-url") is False


def _mock_response(text: str, status: int = 200) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.text = text
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    return resp


class TestResolveFypttStreamUrl:
    @pytest.mark.unit
    def test_resolves_article_to_stream_url(self) -> None:
        article_resp = _mock_response(_ARTICLE_HTML)
        iframe_resp = _mock_response(_IFRAME_HTML)

        with patch("requests.get", side_effect=[article_resp, iframe_resp]):
            url = resolve_fyptt_stream_url("https://fyptt.to/22224/foo/")

        assert url == (
            "https://stream.fyptt.to/ABC123.mp4?token=tk&expires=1234567890"
        )

    @pytest.mark.unit
    def test_passes_through_already_direct_stream_url(self) -> None:
        direct = "https://stream.fyptt.to/X.mp4?token=t&expires=1"
        # Should not even fire a request
        with patch("requests.get") as mock_get:
            assert resolve_fyptt_stream_url(direct) == direct
            mock_get.assert_not_called()

    @pytest.mark.unit
    def test_returns_none_for_non_fyptt_url(self) -> None:
        with patch("requests.get") as mock_get:
            assert resolve_fyptt_stream_url("https://example.com/v") is None
            mock_get.assert_not_called()

    @pytest.mark.unit
    def test_returns_none_when_article_fetch_fails(self) -> None:
        with patch(
            "requests.get",
            side_effect=requests.RequestException("network error"),
        ):
            assert (
                resolve_fyptt_stream_url("https://fyptt.to/22224/foo/") is None
            )

    @pytest.mark.unit
    def test_returns_none_when_iframe_missing(self) -> None:
        article_resp = _mock_response("<html><body>no iframe here</body></html>")
        with patch("requests.get", return_value=article_resp):
            assert (
                resolve_fyptt_stream_url("https://fyptt.to/22224/foo/") is None
            )

    @pytest.mark.unit
    def test_returns_none_when_source_tag_missing(self) -> None:
        article_resp = _mock_response(_ARTICLE_HTML)
        iframe_resp = _mock_response("<html><body>no source tag</body></html>")
        with patch("requests.get", side_effect=[article_resp, iframe_resp]):
            assert (
                resolve_fyptt_stream_url("https://fyptt.to/22224/foo/") is None
            )

    @pytest.mark.unit
    def test_resolves_jwplayer_variant_with_file_attribute(self) -> None:
        """Longer videos use fypttjwstr.php iframe with file:"..." instead of
        a <source> tag. Resolver must handle both shapes."""
        article_resp = _mock_response(_JW_ARTICLE_HTML)
        iframe_resp = _mock_response(_JW_IFRAME_HTML)

        with patch("requests.get", side_effect=[article_resp, iframe_resp]):
            url = resolve_fyptt_stream_url("https://fyptt.to/11362/foo/")

        assert url == (
            "https://stream.fyptt.to/XYZ789.mp4?token=jw&expires=9999999999"
        )

    @pytest.mark.unit
    def test_decodes_html_entities_in_iframe_url(self) -> None:
        """The iframe URL contains &#038; (HTML entity for &); resolver must
        decode it before fetching, otherwise the request goes to a malformed URL."""
        article_resp = _mock_response(_ARTICLE_HTML)
        iframe_resp = _mock_response(_IFRAME_HTML)

        with patch("requests.get", side_effect=[article_resp, iframe_resp]) as mg:
            resolve_fyptt_stream_url("https://fyptt.to/22224/foo/")

        # Second call (iframe fetch) should use the decoded URL.
        iframe_call_url = mg.call_args_list[1].args[0]
        assert "&" in iframe_call_url
        assert "&#038;" not in iframe_call_url
        assert "&amp;" not in iframe_call_url
