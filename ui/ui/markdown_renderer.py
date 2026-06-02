try:
    import markdown as _markdown_lib
    _MARKDOWN_AVAILABLE = True
except ImportError:
    _markdown_lib = None
    _MARKDOWN_AVAILABLE = False

import html as _html


class MarkdownRenderer:

    @staticmethod
    def render(text: str) -> str:
        """Render markdown to HTML. Falls back to escaped plain text if markdown package is unavailable."""
        if not text:
            return ""
        if _MARKDOWN_AVAILABLE:
            return _markdown_lib.markdown(
                text,
                extensions=["fenced_code", "tables", "nl2br"]
            )
        # Graceful plain-text fallback: escape HTML entities and preserve newlines
        return _html.escape(text).replace("\n", "<br>")
