"""tests for internal content handlers."""

# pylint: disable=redefined-outer-name

import pytest

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.internals import (
    ModelEditableContextHandler,
    ReasoningRecapHandler,
    ThoughtsHandler,
    UserEditableContextHandler,
)


@pytest.fixture
def ctx() -> RenderContext:
    """creates render context with internals enabled."""
    return RenderContext(render_internals=True)


class TestThoughtsHandler:
    """tests for thoughts handler."""

    def test_renders_thoughts(self, ctx: RenderContext) -> None:
        """renders thoughts with summary."""
        handler = ThoughtsHandler()
        content = {
            "content_type": "thoughts",
            "thoughts": [{"summary": "Planning", "content": "Let me think..."}],
        }
        result = handler.render(content, None, ctx)
        assert "Planning" in result
        assert "Let me think" in result
        assert "<i>" in result

    def test_is_internal(self) -> None:
        """thoughts handler is marked as internal."""
        # pylint: disable=no-member
        assert ThoughtsHandler.internal is True  # type: ignore[attr-defined]

    def test_handles_empty_thoughts(self, ctx: RenderContext) -> None:
        """handles empty thoughts list."""
        handler = ThoughtsHandler()
        content = {"content_type": "thoughts", "thoughts": []}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_handles_missing_thoughts(self, ctx: RenderContext) -> None:
        """handles missing thoughts key."""
        handler = ThoughtsHandler()
        content = {"content_type": "thoughts"}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_handles_thought_without_content(self, ctx: RenderContext) -> None:
        """handles thought with summary but no content."""
        handler = ThoughtsHandler()
        content = {
            "content_type": "thoughts",
            "thoughts": [{"summary": "Brief thought"}],
        }
        result = handler.render(content, None, ctx)
        assert "Brief thought" in result

    def test_escapes_html_in_thoughts(self, ctx: RenderContext) -> None:
        """escapes HTML in thought content."""
        handler = ThoughtsHandler()
        content = {
            "content_type": "thoughts",
            "thoughts": [{"summary": "<b>bold</b>", "content": "<script>bad</script>"}],
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        assert "&lt;b&gt;" in result

    def test_renders_multiple_thoughts(self, ctx: RenderContext) -> None:
        """renders multiple thoughts."""
        handler = ThoughtsHandler()
        content = {
            "content_type": "thoughts",
            "thoughts": [
                {"summary": "First", "content": "First thought"},
                {"summary": "Second", "content": "Second thought"},
            ],
        }
        result = handler.render(content, None, ctx)
        assert "First" in result
        assert "Second" in result


class TestReasoningRecapHandler:
    """tests for reasoning recap handler."""

    def test_renders_recap(self, ctx: RenderContext) -> None:
        """renders reasoning recap as italic."""
        handler = ReasoningRecapHandler()
        content = {"content_type": "reasoning_recap", "content": "Thought for 30s"}
        result = handler.render(content, None, ctx)
        assert "Thought for 30s" in result
        assert "<i>" in result

    def test_is_internal(self) -> None:
        """reasoning recap handler is marked as internal."""
        # pylint: disable=no-member
        assert ReasoningRecapHandler.internal is True  # type: ignore[attr-defined]

    def test_handles_empty_content(self, ctx: RenderContext) -> None:
        """handles empty content."""
        handler = ReasoningRecapHandler()
        content = {"content_type": "reasoning_recap", "content": ""}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_handles_missing_content(self, ctx: RenderContext) -> None:
        """handles missing content key."""
        handler = ReasoningRecapHandler()
        content = {"content_type": "reasoning_recap"}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_escapes_html_in_recap(self, ctx: RenderContext) -> None:
        """escapes HTML in recap content."""
        handler = ReasoningRecapHandler()
        content = {
            "content_type": "reasoning_recap",
            "content": "Thought about <script>",
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestUserEditableContextHandler:
    """tests for user editable context handler."""

    def test_renders_profile(self, ctx: RenderContext) -> None:
        """renders user profile."""
        handler = UserEditableContextHandler()
        content = {
            "content_type": "user_editable_context",
            "user_profile": "Developer who uses Python",
        }
        result = handler.render(content, None, ctx)
        assert "User Profile" in result
        assert "Developer" in result

    def test_renders_instructions(self, ctx: RenderContext) -> None:
        """renders user instructions."""
        handler = UserEditableContextHandler()
        content = {
            "content_type": "user_editable_context",
            "user_instructions": "Be concise",
        }
        result = handler.render(content, None, ctx)
        assert "User Instructions" in result
        assert "concise" in result

    def test_renders_both(self, ctx: RenderContext) -> None:
        """renders both profile and instructions."""
        handler = UserEditableContextHandler()
        content = {
            "content_type": "user_editable_context",
            "user_profile": "Developer",
            "user_instructions": "Be concise",
        }
        result = handler.render(content, None, ctx)
        assert "User Profile" in result
        assert "User Instructions" in result

    def test_is_internal(self) -> None:
        """user editable context handler is marked as internal."""
        # pylint: disable=no-member
        assert UserEditableContextHandler.internal is True  # type: ignore[attr-defined]

    def test_handles_empty_fields(self, ctx: RenderContext) -> None:
        """handles empty profile and instructions."""
        handler = UserEditableContextHandler()
        content = {
            "content_type": "user_editable_context",
            "user_profile": "",
            "user_instructions": "",
        }
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_handles_missing_fields(self, ctx: RenderContext) -> None:
        """handles missing profile and instructions."""
        handler = UserEditableContextHandler()
        content = {"content_type": "user_editable_context"}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_truncates_long_profile(self, ctx: RenderContext) -> None:
        """truncates long profile text."""
        handler = UserEditableContextHandler()
        long_text = "A" * 250
        content = {
            "content_type": "user_editable_context",
            "user_profile": long_text,
        }
        result = handler.render(content, None, ctx)
        assert "..." in result
        # should be truncated to 200 chars + "..."
        assert "A" * 200 in result

    def test_escapes_html_in_context(self, ctx: RenderContext) -> None:
        """escapes HTML in profile and instructions."""
        handler = UserEditableContextHandler()
        content = {
            "content_type": "user_editable_context",
            "user_profile": "<script>bad</script>",
            "user_instructions": "<b>bold</b>",
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestModelEditableContextHandler:
    """tests for model editable context handler."""

    def test_renders_memory(self, ctx: RenderContext) -> None:
        """renders model memory."""
        handler = ModelEditableContextHandler()
        content = {
            "content_type": "model_editable_context",
            "model_set_context": "User prefers concise answers",
        }
        result = handler.render(content, None, ctx)
        assert "ChatGPT Memory" in result
        assert "concise" in result

    def test_is_internal(self) -> None:
        """model editable context handler is marked as internal."""
        # pylint: disable=no-member
        assert ModelEditableContextHandler.internal is True  # type: ignore[attr-defined]

    def test_handles_empty_context(self, ctx: RenderContext) -> None:
        """handles empty model context."""
        handler = ModelEditableContextHandler()
        content = {"content_type": "model_editable_context", "model_set_context": ""}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_handles_missing_context(self, ctx: RenderContext) -> None:
        """handles missing model_set_context key."""
        handler = ModelEditableContextHandler()
        content = {"content_type": "model_editable_context"}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_escapes_html_in_memory(self, ctx: RenderContext) -> None:
        """escapes HTML in memory content."""
        handler = ModelEditableContextHandler()
        content = {
            "content_type": "model_editable_context",
            "model_set_context": "<script>bad</script>",
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
