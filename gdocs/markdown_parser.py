"""
Markdown to Google Docs Converter

This module provides the `MarkdownToDocsConverter` class that translates Markdown
syntax into Google Docs API `batchUpdate` requests. It enables proper headings,
lists, formatting (bold/italic), links, code blocks, and tables.

The converter follows the "Index Tracker" pattern
(`agent-docs/archive/legacy-root/IMPLEMENTATION_PLAN_MARKDOWN.md`:L136-168)
to track cursor position and generate requests with correct indices.

Example:
    >>> converter = MarkdownToDocsConverter()
    >>> requests = converter.convert("# Hello World\n\nThis is **bold** text.")
    >>> # requests contains insertText + updateParagraphStyle + updateTextStyle

See Also:
    - `gdocs/writing.py` for tool integration (`create_doc`, `insert_markdown`)
    - `gdocs/docs_tables.py` for existing table logic that can be reused
    - `specs/MARKDOWN_STEP_1_CORE.md` for feature specification
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

if TYPE_CHECKING:
    from markdown_it.token import Token

logger = logging.getLogger(__name__)

# Named style mappings for headings (h1 -> HEADING_1, etc.)
HEADING_STYLE_MAP: dict[str, str] = {
    "h1": "HEADING_1",
    "h2": "HEADING_2",
    "h3": "HEADING_3",
    "h4": "HEADING_4",
    "h5": "HEADING_5",
    "h6": "HEADING_6",
}

# Bullet list presets for the Google Docs API
BULLET_PRESET_UNORDERED = "BULLET_DISC_CIRCLE_SQUARE"
BULLET_PRESET_ORDERED = "NUMBERED_DECIMAL_ALPHA_ROMAN"
BULLET_PRESET_CHECKBOX = "BULLET_CHECKBOX"

# Code block styling constants
CODE_FONT_FAMILY = "Consolas"
CODE_BACKGROUND_COLOR = {"red": 0.96, "green": 0.96, "blue": 0.96}  # #f5f5f5
CODE_BORDER_COLOR = {"red": 0.85, "green": 0.85, "blue": 0.85}
CODE_BORDER_WIDTH_PT = 1.0
CODE_BORDER_PADDING_PT = 6.0
CODE_LABEL_COLOR = {"red": 0.45, "green": 0.45, "blue": 0.45}

# Blockquote styling constants (specs/FIX_BLOCKQUOTES.md)
BLOCKQUOTE_INDENT_PT = 36
BLOCKQUOTE_BORDER_WIDTH_PT = 3.0
BLOCKQUOTE_BORDER_PADDING_PT = 12.0
BLOCKQUOTE_BORDER_COLOR = {"red": 0.7, "green": 0.7, "blue": 0.7}

# Horizontal rule styling constants
# Since Google Docs doesn't have a native HR, we use a paragraph with bottom border
HR_BORDER_WIDTH_PT = 1.0
HR_BORDER_COLOR = {"red": 0.7, "green": 0.7, "blue": 0.7}  # #b3b3b3 light gray
HR_PADDING_BELOW_PT = 6

# Task list checkbox characters (Unicode ballot box symbols)
CHECKBOX_UNCHECKED = "☐"  # U+2610 BALLOT BOX
CHECKBOX_CHECKED = "☑"  # U+2611 BALLOT BOX WITH CHECK

# Inline image placeholder used during single-insert buffering. Each placeholder
# is later replaced with an insertInlineImage request at the same index.
IMAGE_PLACEHOLDER_CHAR = "\ufffc"
# Table placeholder used during single-insert buffering. Each placeholder
# is later replaced with a delete+insertTable request pair.
TABLE_PLACEHOLDER_CHAR = "\ufffd"

# Supported markdown conversion modes for Wave 8 extensions.
CHECKLIST_MODES = {"unicode", "native"}
MENTION_MODES = {"text", "person_chip"}

# @user@example.com mention token matcher used in person-chip mode.
PERSON_MENTION_PATTERN = re.compile(r"(?<![\w@])@([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w@])")

# Top-level block tokens whose source line maps are used to preserve explicit
# blank lines from markdown input (e.g. spacing around headings/hr blocks).
SOURCE_GAP_TRACKED_TOKEN_TYPES = {
    "heading_open",
    "paragraph_open",
    "bullet_list_open",
    "ordered_list_open",
    "blockquote_open",
    "table_open",
    "fence",
    "code_block",
    "hr",
}


class MarkdownToDocsConverter:
    """
    Converts Markdown text into Google Docs API batchUpdate requests.

    This class maintains state during conversion to track:
    - `cursor_index`: Current insertion point in the document
    - `requests`: Generated API requests
    - `active_styles`: Stack of active inline styles (bold, italic, etc.)

    The converter uses markdown-it-py with CommonMark preset for parsing.

    **Single-Insert Architecture (FIX_STYLE_BLEED.md v5)**:
    To prevent style bleeding, text is buffered during parsing and inserted
    in one operation. Styles are tracked as (start, end, style) tuples and
    applied after all text is inserted. This avoids the Google Docs API quirk
    where sequentially inserted text inherits styles from preceding text.

    Attributes:
        md: The markdown-it parser instance.
        requests: List of generated Google Docs API request dictionaries.
        cursor_index: Current cursor position (1-based, as per Google Docs API).
        active_styles: Stack of style dictionaries for handling nested formatting.

    Example:
        >>> converter = MarkdownToDocsConverter()
        >>> requests = converter.convert("# Title\n\n**Bold** text")
        >>> len(requests)  # insertText + updateParagraphStyle + updateTextStyle
        3
    """

    def __init__(self, checklist_mode: str = "unicode", mention_mode: str = "text") -> None:
        """Initialize the converter with CommonMark parser + table/strikethrough extensions."""
        if checklist_mode not in CHECKLIST_MODES:
            raise ValueError(
                f"Invalid checklist_mode '{checklist_mode}'. Supported values: {', '.join(sorted(CHECKLIST_MODES))}."
            )
        if mention_mode not in MENTION_MODES:
            raise ValueError(
                f"Invalid mention_mode '{mention_mode}'. Supported values: {', '.join(sorted(MENTION_MODES))}."
            )
        self.checklist_mode = checklist_mode
        self.mention_mode = mention_mode
        # CommonMark base with GFM-style extensions:
        # - table: GFM tables (MARKDOWN_STEP_3_TABLES.md)
        # - strikethrough: ~~text~~ syntax (Task 6.2)
        # - tasklists: [ ] and [x] checkboxes (Task 6.4)
        self.md = MarkdownIt("commonmark").enable("table").enable("strikethrough").use(tasklists_plugin)
        self.requests: list[dict] = []
        self.cursor_index: int = 1
        self.active_styles: list[dict] = []
        # Heading state tracking (Task 1.4)
        # When we enter a heading_open, we record the tag (h1-h6) and start index
        # On heading_close, we apply the paragraph style to the heading range
        self._current_heading_tag: str | None = None
        self._heading_start_index: int = 0
        # List state tracking (Task 1.7)
        # Stack of list types ("bullet" or "ordered") to track nesting
        # Each entry represents one level of list nesting
        self._list_type_stack: list[str] = []
        # Track the start index of the current list item's paragraph
        # Used to apply createParagraphBullets to the correct range
        self._list_item_start_index: int | None = None
        # Track whether we've already inserted leading TABs for the current list item
        # This prevents double-TAB insertion when a list item has multiple text segments
        self._list_item_tabs_inserted: bool = False
        # Track start index and type of the top-level list for whole-list bullet application
        # The API needs all paragraphs in a list processed together to interpret TAB nesting
        self._top_level_list_start_index: int | None = None
        self._top_level_list_type: str | None = None
        self._top_level_list_has_task_items: bool = False
        # Blockquote nesting level (> vs >> vs >>>)
        self._blockquote_nesting_level: int = 0
        self._blockquote_paragraph_start_index: int | None = None
        # General paragraph start tracking for list bleed prevention
        self._paragraph_start_index: int | None = None
        # List bleed prevention state (Task 5.3 - specs/FIX_LIST_BLEED.md)
        # Google Docs paragraphs inherit the style of the previous paragraph on newline.
        # When exiting a list, subsequent blocks (headings, paragraphs, code, blockquotes)
        # may inherit bullet formatting. We emit deleteParagraphBullets to reset this.
        self._in_list_block: bool = False  # True while inside any list
        self._just_exited_list: bool = False  # True after list_close until next block clears it
        # Table buffering state (Task 4.2)
        # When inside a table, we collect cell contents into a 2D array
        # before generating the insertTable request on table_close
        self._in_table: bool = False
        self._table_data: list[list[str]] = []  # 2D array: rows of cells
        self._current_row: list[str] = []  # Current row being built
        self._current_cell_content: str = ""  # Current cell text being collected
        self._in_table_cell: bool = False  # True when inside th/td
        # Single-Insert Architecture (FIX_STYLE_BLEED.md v5)
        # Instead of inserting text fragments sequentially (which causes style bleeding),
        # we buffer all text and track styles as ranges. At convert() end:
        # 1. One insertText with the entire buffer
        # 2. updateTextStyle for each tracked range
        self._text_buffer: str = ""  # All text accumulated during parsing
        self._deferred_styles: list[tuple[int, int, dict]] = []  # (start, end, style)
        # Track where each style started (for when style_open happens)
        self._style_start_positions: list[tuple[int, dict]] = []  # (buffer_position, style)
        # Table data for post-processing (populated during convert())
        # Each entry is (table_data_2d, bold_headers) for one table found in the markdown
        self.pending_tables: list[tuple[list[list[str]], bool]] = []
        # Pending person mentions captured from markdown text in person-chip mode as
        # (buffer-relative start, buffer-relative end, email).
        self.pending_person_mentions: list[tuple[int, int, str]] = []
        # Pending table placeholders captured during buffering as
        # (buffer-relative index, rows, cols).
        self._pending_table_insertions: list[tuple[int, int, int]] = []
        # Pending inline images captured during buffering as
        # (buffer-relative index, image_uri).
        self._pending_inline_images: list[tuple[int, str]] = []
        # In native checklist mode, the task-list plugin leaves a leading space
        # in the following text token after the checkbox html token. Strip one.
        self._strip_next_task_text_space: bool = False
        # Track top-level source block line boundaries to preserve explicit
        # blank lines in the original markdown.
        self._last_tracked_block_end_line: int | None = None

    def convert(self, markdown_text: str, start_index: int = 1) -> list[dict]:
        """
        Convert Markdown text to Google Docs API requests.

        Args:
            markdown_text: The Markdown string to convert.
            start_index: The starting index in the document (1-based).
                         Defaults to 1 (start of document body).

        Returns:
            A list of Google Docs API request dictionaries ready for batchUpdate.

        Note:
            This method resets the converter state before processing.
            The same converter instance can be reused for multiple conversions.
        """
        self.requests = []
        self.cursor_index = start_index
        self.active_styles = []
        self._current_heading_tag = None
        self._heading_start_index = 0
        self._list_type_stack = []
        self._list_item_start_index = None
        self._list_item_tabs_inserted = False
        self._top_level_list_start_index = None
        self._top_level_list_type = None
        self._top_level_list_has_task_items = False
        self._blockquote_nesting_level = 0
        self._blockquote_paragraph_start_index = None
        self._paragraph_start_index = None
        self._in_list_block = False
        self._just_exited_list = False
        self._in_table = False
        self._table_data = []
        self._current_row = []
        self._current_cell_content = ""
        self._in_table_cell = False
        self._text_buffer = ""
        self._deferred_styles = []
        self._style_start_positions = []
        self.pending_tables = []
        self.pending_person_mentions = []
        self._pending_table_insertions = []
        self._pending_inline_images = []
        self._strip_next_task_text_space = False
        self._last_tracked_block_end_line = None

        tokens: list[Token] = self.md.parse(markdown_text)

        for token in tokens:
            self._insert_source_blank_lines(token)
            self._handle_token(token)

        # Single-Insert Architecture (FIX_STYLE_BLEED.md v5):
        # Insert ALL text in one request, then apply styles separately.
        # This prevents Google Docs API from inheriting styles between fragments.
        insert_requests: list[dict] = []
        if self._text_buffer:
            insert_requests.append(
                {
                    "insertText": {
                        "text": self._text_buffer,
                        "location": {"index": start_index},
                    }
                }
            )

        # Merge overlapping style ranges (e.g., bold+italic on same range -> one request)
        merged_styles = self._merge_deferred_styles()

        deferred_style_requests: list[dict] = []
        for rel_start, rel_end, style in merged_styles:
            abs_start = start_index + rel_start
            abs_end = start_index + rel_end
            deferred_style_requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": abs_start, "endIndex": abs_end},
                        "textStyle": style,
                        "fields": self._get_style_fields(style),
                    }
                }
            )

        # Collect other request types from self.requests (non-inline styles)
        other_style_requests = [r for r in self.requests if "updateTextStyle" in r]
        para_requests = [r for r in self.requests if "updateParagraphStyle" in r]
        raw_bullet_requests = [
            r for r in self.requests if "createParagraphBullets" in r or "deleteParagraphBullets" in r
        ]
        # Adjust bullet indices to account for TAB removal by createParagraphBullets
        bullet_requests = self._adjust_bullet_indices_for_tab_removal(raw_bullet_requests, start_index)
        table_requests = self._build_table_replacement_requests(start_index, raw_bullet_requests)
        image_requests = self._build_inline_image_requests(start_index, raw_bullet_requests)
        mention_requests = self._build_person_mention_requests(start_index, raw_bullet_requests)
        # NOTE: Table cell insertText requests are no longer included in output.
        # Cell population requires inspecting the document after table creation
        # to get actual cell paragraph indices. See create_doc in writing.py.

        return (
            insert_requests
            + deferred_style_requests
            + other_style_requests
            + para_requests
            + bullet_requests
            + mention_requests
            + image_requests
            + table_requests
        )

    def _handle_token(self, token: Token) -> None:
        """
        Dispatch a token to the appropriate handler based on its type.

        Args:
            token: A markdown-it Token object.

        Note:
            Token handlers are implemented incrementally in Phase 1 tasks.
        """
        logger.debug(f"Token: type={token.type}, tag={token.tag}, nesting={token.nesting}")

        if token.type == "inline":
            self._handle_inline(token)
        elif token.type == "paragraph_close":
            self._handle_paragraph_close()
        elif token.type == "heading_open":
            self._handle_heading_open(token)
        elif token.type == "heading_close":
            self._handle_heading_close(token)
        elif token.type == "bullet_list_open":
            self._handle_list_open("bullet")
        elif token.type == "bullet_list_close":
            self._handle_list_close()
        elif token.type == "ordered_list_open":
            self._handle_list_open("ordered")
        elif token.type == "ordered_list_close":
            self._handle_list_close()
        elif token.type == "list_item_open":
            self._handle_list_item_open()
        elif token.type == "list_item_close":
            self._handle_list_item_close()
        elif token.type == "fence":
            self._handle_code_block(token)
        elif token.type == "code_block":
            self._handle_code_block(token)
        elif token.type == "blockquote_open":
            self._handle_blockquote_open()
        elif token.type == "blockquote_close":
            self._handle_blockquote_close()
        elif token.type == "paragraph_open":
            self._handle_paragraph_open()
        elif token.type == "table_open":
            self._handle_table_open()
        elif token.type == "table_close":
            self._handle_table_close()
        elif token.type == "tr_open":
            self._handle_tr_open()
        elif token.type == "tr_close":
            self._handle_tr_close()
        elif token.type in ("th_open", "td_open"):
            self._handle_cell_open()
        elif token.type in ("th_close", "td_close"):
            self._handle_cell_close()
        elif token.type == "hr":
            self._handle_horizontal_rule()

    def _insert_source_blank_lines(self, token: Token) -> None:
        """
        Preserve explicit blank lines from source markdown for top-level blocks.

        markdown-it token maps expose source line ranges (`token.map=[start,end)`).
        When there is a line gap between two top-level block starts, that gap
        represents explicit blank lines in the source. We materialize those gaps
        into the text buffer so Google Docs rendering keeps expected vertical
        spacing (notably around heading->paragraph and horizontal-rule regions).
        """
        token_map = token.map
        if (
            token_map is None
            or token.hidden
            or token.level != 0
            or token.nesting < 0
            or token.type not in SOURCE_GAP_TRACKED_TOKEN_TYPES
        ):
            return

        start_line, end_line = token_map
        if self._last_tracked_block_end_line is not None:
            blank_lines = max(0, start_line - self._last_tracked_block_end_line)
            for _ in range(blank_lines):
                self._insert_newline()

        self._last_tracked_block_end_line = end_line

    def _handle_inline(self, token: Token) -> None:
        """
        Process an inline token and its children.

        Inline tokens contain the actual text content and inline formatting
        (bold, italic, links, etc.) as children. This method iterates through
        children and dispatches to appropriate handlers.

        Args:
            token: An inline token with children to process.

        Implementation Notes:
            - Text tokens are inserted directly via _insert_text()
            - Style tokens (strong_open/close, em_open/close) are handled in Task 1.5
            - Link tokens are handled in Task 1.6
            - Follows the "Index Tracker" pattern from
              `agent-docs/archive/legacy-root/IMPLEMENTATION_PLAN_MARKDOWN.md`:L136-168
        """
        if not token.children:
            return

        for child in token.children:
            logger.debug(f"  Child: type={child.type}, content={child.content!r}")

            if child.type == "text":
                if self._in_table_cell:
                    self._current_cell_content += child.content
                else:
                    text_content = child.content
                    if self._strip_next_task_text_space:
                        text_content = text_content[1:] if text_content.startswith(" ") else text_content
                        self._strip_next_task_text_space = False
                    if self.mention_mode == "person_chip":
                        self._insert_text_with_person_mentions(text_content)
                    else:
                        self._insert_text(text_content)
            elif child.type == "softbreak":
                # Soft line breaks become spaces in Google Docs
                self._insert_text(" ")
            elif child.type == "hardbreak":
                self._insert_text("\n")
            elif child.type == "strong_open":
                self._push_style({"bold": True})
            elif child.type == "strong_close":
                self._pop_style({"bold": True})
            elif child.type == "em_open":
                self._push_style({"italic": True})
            elif child.type == "em_close":
                self._pop_style({"italic": True})
            elif child.type == "link_open":
                href = child.attrs.get("href", "") if isinstance(child.attrs, dict) else ""
                self._push_style({"link": {"url": href}})
            elif child.type == "link_close":
                self._pop_link_style()
            elif child.type == "code_inline":
                self._handle_code_inline(child)
            elif child.type == "s_open":
                self._push_style({"strikethrough": True})
            elif child.type == "s_close":
                self._pop_style({"strikethrough": True})
            elif child.type == "image":
                self._handle_image(child)
            elif child.type == "html_inline":
                self._handle_html_inline(child)

    def _insert_text(self, text: str) -> None:
        """
        Buffer text for single-insert and advance cursor.

        Text is accumulated in _text_buffer. Styles are tracked via _push_style/_pop_style
        and recorded as ranges in _deferred_styles. The actual insertText request is
        generated in convert() after all text is buffered.

        For list items, prepends TAB characters based on nesting level. The Google Docs API
        determines nesting from leading TABs (see
        `agent-docs/archive/legacy-root/IMPLEMENTATION_PLAN_MARKDOWN.md` §6.3).
        """
        if not text:
            return

        # List nesting via leading TABs (FIX_LIST_NESTING.md)
        # Only insert TABs once per list item, on first text segment
        if self._list_item_start_index is not None and not self._list_item_tabs_inserted:
            nesting_level = len(self._list_type_stack) - 1
            if nesting_level > 0:
                tabs = "\t" * nesting_level
                self._text_buffer += tabs
                self.cursor_index += len(tabs)
                logger.debug(f"Inserted {nesting_level} TAB(s) for list nesting")
            self._list_item_tabs_inserted = True

        self._text_buffer += text
        self.cursor_index += len(text)
        logger.debug(f"Buffered text: {text!r}, buffer_len={len(self._text_buffer)}, cursor={self.cursor_index}")

    def _insert_newline(self) -> None:
        """Insert a newline character at the current cursor position."""
        self._insert_text("\n")

    def _handle_paragraph_open(self) -> None:
        """Track paragraph start for blockquote styling and list bleed prevention."""
        self._paragraph_start_index = self.cursor_index
        if self._blockquote_nesting_level > 0:
            self._blockquote_paragraph_start_index = self.cursor_index
            logger.debug(f"Paragraph open in blockquote: start_index={self.cursor_index}")

    def _handle_paragraph_close(self) -> None:
        """
        Handle paragraph_close token.

        Applies styles based on context:
        - Blockquotes: indent margins + italic
        - Post-list paragraphs: clears bullet inheritance

        Note: List bullets are now applied at list_close, not per-paragraph.
        """
        if self._paragraph_start_index is not None and not self._list_type_stack:
            self._emit_delete_paragraph_bullets_if_needed(self._paragraph_start_index, self.cursor_index)
        if self._blockquote_paragraph_start_index is not None and self._blockquote_nesting_level > 0:
            self._apply_blockquote_style()
            self._blockquote_paragraph_start_index = None
        self._paragraph_start_index = None
        self._insert_newline()

    def _handle_list_open(self, list_type: str) -> None:
        """
        Handle bullet_list_open or ordered_list_open token.

        Pushes the list type onto the stack to track nesting level.
        Each stack entry represents one level of list nesting.
        """
        if not self._list_type_stack:
            self._top_level_list_start_index = self.cursor_index
            self._top_level_list_type = list_type
            self._top_level_list_has_task_items = False
        self._list_type_stack.append(list_type)
        self._in_list_block = True
        self._just_exited_list = False
        logger.debug(f"List open: type={list_type}, nesting_level={len(self._list_type_stack) - 1}")

    def _handle_list_close(self) -> None:
        """
        Handle bullet_list_close or ordered_list_close token.

        Pops the list type from the stack. When the stack becomes empty,
        applies bullets to the entire list range and marks _just_exited_list.
        """
        if self._list_type_stack:
            popped = self._list_type_stack.pop()
            if not self._list_type_stack:
                emitted_bullets = self._apply_top_level_list_bullets()
                self._in_list_block = False
                self._just_exited_list = emitted_bullets
            logger.debug(f"List close: type={popped}, nesting_level={len(self._list_type_stack)}")
        else:
            logger.warning("list_close without matching list_open")

    def _handle_list_item_open(self) -> None:
        """
        Handle list_item_open token.

        Records the start index for this list item's paragraph so we can
        apply the bullet style when the paragraph closes.
        """
        self._list_item_start_index = self.cursor_index
        self._list_item_tabs_inserted = False
        logger.debug(f"List item open: start_index={self._list_item_start_index}")

    def _handle_list_item_close(self) -> None:
        """
        Handle list_item_close token.

        Clears the list item start index.
        """
        self._list_item_start_index = None
        logger.debug("List item close")

    def _emit_delete_paragraph_bullets_if_needed(self, start_index: int, end_index: int) -> None:
        """
        Emit deleteParagraphBullets request if we just exited a list.

        This prevents list formatting from bleeding into subsequent non-list
        paragraphs due to Google Docs' paragraph style inheritance behavior.
        See specs/FIX_LIST_BLEED.md for details.
        """
        if self._just_exited_list:
            request = {
                "deleteParagraphBullets": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    }
                }
            }
            self.requests.append(request)
            self._just_exited_list = False
            logger.debug(f"Emitted deleteParagraphBullets for range [{start_index}, {end_index})")

    def _apply_top_level_list_bullets(self) -> bool:
        """
        Apply bullets to the entire top-level list range.

        The Google Docs API determines nesting by counting leading TAB characters
        in each paragraph. By applying bullets to the entire list at once,
        the API correctly interprets the TAB-based nesting hierarchy.
        """
        if self._top_level_list_start_index is None:
            logger.warning("_apply_top_level_list_bullets called without start index")
            return False

        bullet_preset = BULLET_PRESET_UNORDERED
        if self._top_level_list_has_task_items:
            if self.checklist_mode == "native":
                bullet_preset = BULLET_PRESET_CHECKBOX
            else:
                logger.debug("Skipping createParagraphBullets for task-list block (unicode checklist mode)")
                self._top_level_list_start_index = None
                self._top_level_list_type = None
                self._top_level_list_has_task_items = False
                return False

        if not self._top_level_list_has_task_items:
            if self._top_level_list_type == "bullet":
                bullet_preset = BULLET_PRESET_UNORDERED
            else:
                bullet_preset = BULLET_PRESET_ORDERED

        # Exclude the list-closing newline from the bullet range to avoid
        # rendering an extra empty bullet paragraph after task/list blocks.
        end_index = self.cursor_index
        if self._text_buffer.endswith("\n"):
            end_index = max(self._top_level_list_start_index + 1, self.cursor_index - 1)

        request = {
            "createParagraphBullets": {
                "range": {
                    "startIndex": self._top_level_list_start_index,
                    "endIndex": end_index,
                },
                "bulletPreset": bullet_preset,
            }
        }
        self.requests.append(request)

        logger.debug(
            f"Applied bullets to entire list: preset={bullet_preset}, "
            f"range=[{self._top_level_list_start_index}, {end_index})"
        )

        self._top_level_list_start_index = None
        self._top_level_list_type = None
        self._top_level_list_has_task_items = False
        return True

    def _handle_blockquote_open(self) -> None:
        """Increment blockquote nesting level."""
        self._blockquote_nesting_level += 1
        logger.debug(f"Blockquote open: nesting_level={self._blockquote_nesting_level}")

    def _handle_blockquote_close(self) -> None:
        """Decrement blockquote nesting level."""
        if self._blockquote_nesting_level > 0:
            self._blockquote_nesting_level -= 1
            logger.debug(f"Blockquote close: nesting_level={self._blockquote_nesting_level}")
        else:
            logger.warning("blockquote_close without matching blockquote_open")

    def _apply_blockquote_style(self) -> None:
        """
        Generate paragraph indent, border, and italic style requests for blockquote.

        Per specs/FIX_BLOCKQUOTES.md, blockquotes use:
        - indentStart margin (36 PT * nesting_level)
        - borderLeft: gray vertical bar (3 PT width, 12 PT padding)
        - Italic text style
        """
        if self._blockquote_paragraph_start_index is None:
            logger.warning("_apply_blockquote_style called without paragraph start index")
            return

        start_idx = self._blockquote_paragraph_start_index
        end_idx = self.cursor_index
        margin_pt = BLOCKQUOTE_INDENT_PT * self._blockquote_nesting_level

        self._emit_delete_paragraph_bullets_if_needed(start_idx, end_idx)

        paragraph_request = {
            "updateParagraphStyle": {
                "range": {"startIndex": start_idx, "endIndex": end_idx},
                "paragraphStyle": {
                    "indentStart": {"magnitude": margin_pt, "unit": "PT"},
                    "indentFirstLine": {"magnitude": margin_pt, "unit": "PT"},
                    "borderLeft": {
                        "color": {"color": {"rgbColor": BLOCKQUOTE_BORDER_COLOR}},
                        "width": {"magnitude": BLOCKQUOTE_BORDER_WIDTH_PT, "unit": "PT"},
                        "padding": {"magnitude": BLOCKQUOTE_BORDER_PADDING_PT, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                },
                "fields": "indentStart,indentFirstLine,borderLeft",
            }
        }
        self.requests.append(paragraph_request)

        text_style_request = {
            "updateTextStyle": {
                "range": {"startIndex": start_idx, "endIndex": end_idx},
                "textStyle": {"italic": True},
                "fields": "italic",
            }
        }
        self.requests.append(text_style_request)

        logger.debug(
            f"Applied blockquote style: margin={margin_pt}PT, borderLeft, italic=True, range=[{start_idx}, {end_idx})"
        )

    def _handle_table_open(self) -> None:
        """Begin table buffering mode - collect cells before generating requests."""
        self._in_table = True
        self._table_data = []
        self._current_row = []
        self._current_cell_content = ""
        self._in_table_cell = False
        logger.debug("Table open: started buffering")

    def _handle_table_close(self) -> None:
        """
        End table buffering and register a placeholder replacement.

        Instead of predicting post-table cursor indices (fragile and drift-prone),
        table blocks are represented by a one-character placeholder in the text
        buffer. Later, the caller replaces that placeholder with insertTable in a
        dedicated structural phase.
        """
        if not self._table_data:
            logger.warning("Table close with no buffered data")
            self._in_table = False
            return

        rows = len(self._table_data)
        cols = max(len(row) for row in self._table_data) if self._table_data else 0

        if rows == 0 or cols == 0:
            logger.warning(f"Invalid table dimensions: {rows}x{cols}")
            self._in_table = False
            return

        # Normalize rows to have consistent column count
        for row in self._table_data:
            while len(row) < cols:
                row.append("")

        placeholder_pos = len(self._text_buffer)
        self._insert_text(TABLE_PLACEHOLDER_CHAR)
        self._pending_table_insertions.append((placeholder_pos, rows, cols))
        logger.debug(
            "Table close: buffered placeholder at buffer_pos=%d for %dx%d table",
            placeholder_pos,
            rows,
            cols,
        )

        # Save table data for post-processing by the caller (e.g., create_doc).
        # Cell population requires inspecting the document after table creation
        # to get actual cell paragraph indices — the indices cannot be predicted
        # in advance within a single batchUpdate call.
        self.pending_tables.append((list(self._table_data), True))

        # Tables are block-level elements; terminate the placeholder paragraph so
        # following blocks do not render in the same paragraph context.
        self._insert_newline()

        self._in_table = False
        self._table_data = []
        self._current_row = []
        self._current_cell_content = ""
        self._in_table_cell = False

    def _handle_tr_open(self) -> None:
        """Start a new table row."""
        self._current_row = []
        logger.debug("Table row open")

    def _handle_tr_close(self) -> None:
        """Complete the current row and add to table data."""
        if self._current_row:
            self._table_data.append(self._current_row)
            logger.debug(f"Table row close: added row with {len(self._current_row)} cells")
        self._current_row = []

    def _handle_cell_open(self) -> None:
        """Start collecting content for a table cell."""
        self._in_table_cell = True
        self._current_cell_content = ""
        logger.debug("Table cell open")

    def _handle_cell_close(self) -> None:
        """Complete the current cell and add to current row."""
        self._current_row.append(self._current_cell_content)
        logger.debug(f"Table cell close: content={self._current_cell_content!r}")
        self._current_cell_content = ""
        self._in_table_cell = False

    def _apply_header_bold_style(self, table_start_index: int, cols: int) -> None:
        """Apply bold formatting to each cell in the first table row."""
        if not self._table_data or not any(self._table_data[0]):
            return

        header_offset = 0
        for c, cell_text in enumerate(self._table_data[0]):
            if not cell_text:
                continue

            base_cell_index = table_start_index + 3 + c * 2
            cell_start = base_cell_index + header_offset
            cell_end = cell_start + len(cell_text)

            bold_request = {
                "updateTextStyle": {
                    "range": {
                        "startIndex": cell_start,
                        "endIndex": cell_end,
                    },
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            }
            self.requests.append(bold_request)
            logger.debug(f"Applied bold to header cell (0,{c}): range [{cell_start}, {cell_end})")

            header_offset += len(cell_text)

    def _handle_heading_open(self, token: Token) -> None:
        """
        Start tracking a heading block.

        Records the heading tag (h1-h6) and the current cursor position
        so we can apply the paragraph style when the heading closes.
        Also clears any inherited list bullet formatting.
        """
        self._current_heading_tag = token.tag
        self._heading_start_index = self.cursor_index
        logger.debug(f"Heading open: tag={token.tag}, start_index={self.cursor_index}")

    def _handle_heading_close(self, token: Token) -> None:
        """
        Apply heading paragraph style to the completed heading range.

        Generates an updateParagraphStyle request with the appropriate
        HEADING_1-HEADING_6 named style based on the h1-h6 tag.
        """
        if self._current_heading_tag is None:
            logger.warning("heading_close without matching heading_open")
            return

        named_style = HEADING_STYLE_MAP.get(self._current_heading_tag)
        if named_style is None:
            logger.warning(f"Unknown heading tag: {self._current_heading_tag}")
            self._current_heading_tag = None
            return

        self._emit_delete_paragraph_bullets_if_needed(self._heading_start_index, self.cursor_index)

        request = {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": self._heading_start_index,
                    "endIndex": self.cursor_index,
                },
                "paragraphStyle": {"namedStyleType": named_style},
                "fields": "namedStyleType",
            }
        }
        self.requests.append(request)
        logger.debug(f"Applied heading style {named_style} to range [{self._heading_start_index}, {self.cursor_index})")

        self._insert_newline()
        self._current_heading_tag = None

    def _handle_horizontal_rule(self) -> None:
        """
        Handle horizontal rule (---) by inserting a paragraph with bottom border.

        Google Docs doesn't have a native horizontal rule element, so we simulate
        it with an empty paragraph styled with a bottom border. This creates a
        visual separator line that serves the same purpose as an HR in HTML.
        """
        start_index = self.cursor_index

        self._emit_delete_paragraph_bullets_if_needed(start_index, start_index + 1)

        # Insert the HR newline into the buffer (keeps cursor_index consistent)
        self._insert_text("\n")

        paragraph_style_request = {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": start_index,
                    "endIndex": self.cursor_index,
                },
                "paragraphStyle": {
                    "borderBottom": {
                        "color": {"color": {"rgbColor": HR_BORDER_COLOR}},
                        "width": {"magnitude": HR_BORDER_WIDTH_PT, "unit": "PT"},
                        "dashStyle": "SOLID",
                        "padding": {"magnitude": HR_PADDING_BELOW_PT, "unit": "PT"},
                    },
                },
                "fields": "borderBottom",
            }
        }
        self.requests.append(paragraph_style_request)

        logger.debug(f"Inserted horizontal rule at index {start_index}")

    def _handle_code_block(self, token: Token) -> None:
        """
        Handle fenced code blocks (```) and indented code blocks.

        Inserts optional fenced-language labels and code content into the text
        buffer, applies deferred monospace styling to code text, and applies
        paragraph-level background + border styling for code block visual parity.
        """
        content = token.content or ""
        language = self._extract_code_block_language(token)
        if not content and not language:
            return

        start_idx = self.cursor_index
        label_range: tuple[int, int] | None = None

        if language:
            label_start = len(self._text_buffer)
            self._insert_text(language)
            label_end = len(self._text_buffer)
            label_range = (label_start, label_end)
            self._insert_newline()

        code_buffer_start = len(self._text_buffer)
        if content:
            self._insert_text(content)
        code_buffer_end = len(self._text_buffer)

        self._emit_delete_paragraph_bullets_if_needed(start_idx, self.cursor_index)

        if label_range is not None:
            label_style = {
                "bold": True,
                "foregroundColor": {"color": {"rgbColor": CODE_LABEL_COLOR}},
            }
            self._deferred_styles.append((label_range[0], label_range[1], label_style))

        paragraph_style_request = {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": start_idx,
                    "endIndex": self.cursor_index,
                },
                "paragraphStyle": {
                    "shading": {"backgroundColor": {"color": {"rgbColor": CODE_BACKGROUND_COLOR}}},
                    "borderTop": {
                        "color": {"color": {"rgbColor": CODE_BORDER_COLOR}},
                        "width": {"magnitude": CODE_BORDER_WIDTH_PT, "unit": "PT"},
                        "padding": {"magnitude": CODE_BORDER_PADDING_PT, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                    "borderRight": {
                        "color": {"color": {"rgbColor": CODE_BORDER_COLOR}},
                        "width": {"magnitude": CODE_BORDER_WIDTH_PT, "unit": "PT"},
                        "padding": {"magnitude": CODE_BORDER_PADDING_PT, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                    "borderBottom": {
                        "color": {"color": {"rgbColor": CODE_BORDER_COLOR}},
                        "width": {"magnitude": CODE_BORDER_WIDTH_PT, "unit": "PT"},
                        "padding": {"magnitude": CODE_BORDER_PADDING_PT, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                    "borderLeft": {
                        "color": {"color": {"rgbColor": CODE_BORDER_COLOR}},
                        "width": {"magnitude": CODE_BORDER_WIDTH_PT, "unit": "PT"},
                        "padding": {"magnitude": CODE_BORDER_PADDING_PT, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                },
                "fields": "shading,borderTop,borderRight,borderBottom,borderLeft",
            }
        }
        self.requests.append(paragraph_style_request)

        code_style = {
            "weightedFontFamily": {
                "fontFamily": CODE_FONT_FAMILY,
                "weight": 400,
            },
            "backgroundColor": {"color": {"rgbColor": CODE_BACKGROUND_COLOR}},
        }
        if code_buffer_end > code_buffer_start:
            self._deferred_styles.append((code_buffer_start, code_buffer_end, code_style))

        logger.debug(
            "Buffered code block: language=%r, content_chars=%d, code_range=[%d, %d), abs_range=[%d, %d)",
            language,
            len(content),
            code_buffer_start,
            code_buffer_end,
            start_idx,
            self.cursor_index,
        )

        self._insert_newline()

    def _extract_code_block_language(self, token: Token) -> str:
        """
        Extract optional fenced code language from token metadata.

        markdown-it stores fenced info (e.g. "python", "js title=...") in
        token.info. We use the first segment as the display label.
        """
        info = (token.info or "").strip()
        if not info:
            return ""
        return info.split()[0]

    def _handle_code_inline(self, token: Token) -> None:
        """
        Handle inline code spans (`code`).

        Inserts the code content into the text buffer with deferred monospace
        font and background styling.
        """
        content = token.content
        if not content:
            return

        buffer_start = len(self._text_buffer)
        self._insert_text(content)
        buffer_end = len(self._text_buffer)

        code_style = {
            "weightedFontFamily": {
                "fontFamily": CODE_FONT_FAMILY,
                "weight": 400,
            },
            "backgroundColor": {"color": {"rgbColor": CODE_BACKGROUND_COLOR}},
        }
        self._deferred_styles.append((buffer_start, buffer_end, code_style))

        logger.debug(f"Buffered inline code: {content!r}, buffer range [{buffer_start}, {buffer_end})")

    def _handle_image(self, token: Token) -> None:
        """
        Handle image tokens from Markdown ![alt](src) syntax.

        Generates an insertInlineImage request for the Google Docs API.
        The image URI must be publicly accessible or a Google Drive URI
        that the authenticated user has access to.

        Note:
            Google Docs inline images consume 1 index position in the document.
            Alt text is not directly supported by insertInlineImage but could
            be added as a caption in future enhancements.

        Args:
            token: An image token containing src in attrs and alt text in children.
        """
        # Extract src from token.attrs (can be dict or list of tuples)
        src: str = ""
        if isinstance(token.attrs, dict):
            src_value = token.attrs.get("src", "")
            if isinstance(src_value, str):
                src = src_value
        elif token.attrs:
            # markdown-it-py sometimes uses list of [key, value] pairs
            attrs_dict = dict(token.attrs)
            src_value = attrs_dict.get("src", "")
            if isinstance(src_value, str):
                src = src_value

        if not src:
            logger.warning("Image token missing 'src' attribute, skipping")
            return

        # Buffer a placeholder char and register deferred image insertion.
        # This guarantees the target paragraph/index exists after the single
        # insertText request, then we replace placeholder -> image deterministically.
        placeholder_pos = len(self._text_buffer)
        self._insert_text(IMAGE_PLACEHOLDER_CHAR)
        self._pending_inline_images.append((placeholder_pos, src))
        logger.debug(
            "Buffered inline image placeholder at buffer_pos=%d for uri=%r",
            placeholder_pos,
            src,
        )

    def _handle_html_inline(self, token: Token) -> None:
        """
        Handle html_inline tokens, specifically for task list checkboxes.

        The tasklists plugin converts [ ] and [x] into html_inline tokens
        containing <input> elements. We detect these and insert Unicode
        checkbox characters instead:
        - Unchecked: ☐ (U+2610)
        - Checked: ☑ (U+2611)
        """
        content = token.content
        if not content:
            return

        # Detect task list checkbox HTML from mdit_py_plugins.tasklists
        # Format: <input class="task-list-item-checkbox" disabled="disabled" type="checkbox">
        # or with checked="checked" for checked items
        # Note: The following text token already has a leading space, so we don't add one
        if 'class="task-list-item-checkbox"' in content:
            if self.checklist_mode == "native":
                if self._list_type_stack:
                    self._top_level_list_has_task_items = True
                self._strip_next_task_text_space = True
                logger.debug("Detected task list checkbox in native checklist mode")
            else:
                checkbox_char = CHECKBOX_CHECKED if 'checked="checked"' in content else CHECKBOX_UNCHECKED
                self._insert_text(checkbox_char)
                if self._list_type_stack:
                    self._top_level_list_has_task_items = True
                logger.debug(f"Inserted task list checkbox: {checkbox_char!r}")
        else:
            # For other HTML inline elements, insert as plain text
            # This preserves any raw HTML the user may have included
            self._insert_text(content)
            logger.debug(f"Inserted raw HTML inline: {content!r}")

    def _push_style(self, style: dict) -> None:
        """Push a style dict onto the active_styles stack and record start position."""
        self.active_styles.append(style)
        self._style_start_positions.append((len(self._text_buffer), style))
        logger.debug(f"Pushed style: {style}, buffer_pos: {len(self._text_buffer)}")

    def _pop_style(self, expected_style: dict) -> None:
        """Pop style from stack and record the completed range for deferred application."""
        if not self.active_styles:
            logger.warning(f"Attempted to pop style {expected_style} from empty stack")
            return
        popped = self.active_styles.pop()
        if popped != expected_style:
            logger.warning(f"Style mismatch: expected {expected_style}, got {popped}")

        for i in range(len(self._style_start_positions) - 1, -1, -1):
            start_pos, start_style = self._style_start_positions[i]
            if start_style == popped:
                self._style_start_positions.pop(i)
                end_pos = len(self._text_buffer)
                if end_pos > start_pos:
                    self._deferred_styles.append((start_pos, end_pos, popped))
                    logger.debug(f"Deferred style: {popped}, range [{start_pos}, {end_pos})")
                break
        else:
            logger.warning(f"No start position found for style {popped}")

    def _pop_link_style(self) -> None:
        """Pop a link style from the stack and record deferred style range."""
        if not self.active_styles:
            logger.warning("Attempted to pop link style from empty stack")
            return
        for i in range(len(self.active_styles) - 1, -1, -1):
            if "link" in self.active_styles[i]:
                popped = self.active_styles.pop(i)
                for j in range(len(self._style_start_positions) - 1, -1, -1):
                    start_pos, start_style = self._style_start_positions[j]
                    if "link" in start_style:
                        self._style_start_positions.pop(j)
                        end_pos = len(self._text_buffer)
                        if end_pos > start_pos:
                            self._deferred_styles.append((start_pos, end_pos, popped))
                            logger.debug(f"Deferred link style: {popped}, range [{start_pos}, {end_pos})")
                        break
                logger.debug(f"Popped link style: {popped}, stack depth: {len(self.active_styles)}")
                return
        logger.warning("No link style found on stack to pop")

    def _get_merged_style(self) -> dict:
        """Merge all active styles into a single style dict."""
        merged: dict = {}
        for style in self.active_styles:
            merged.update(style)
        return merged

    def _get_style_fields(self, style: dict) -> str:
        """Generate the fields mask for updateTextStyle from style keys."""
        return ",".join(style.keys())

    def _merge_deferred_styles(self) -> list[tuple[int, int, dict]]:
        """Merge style ranges with identical start/end into single requests."""
        if not self._deferred_styles:
            return []

        range_to_style: dict[tuple[int, int], dict] = {}
        for start, end, style in self._deferred_styles:
            key = (start, end)
            if key in range_to_style:
                range_to_style[key].update(style)
            else:
                range_to_style[key] = dict(style)

        return [(start, end, style) for (start, end), style in range_to_style.items()]

    def _build_inline_image_requests(self, start_index: int, raw_bullet_requests: list[dict]) -> list[dict]:
        """
        Build deferred inline-image replacement requests.

        For each buffered image placeholder, emit:
        1) deleteContentRange for the placeholder character
        2) insertInlineImage at the same index

        This keeps index math stable under the single-insert architecture and
        avoids fragile direct image placement against non-materialized text.
        """
        requests: list[dict] = []
        for rel_index, uri in self._pending_inline_images:
            abs_index = start_index + rel_index
            abs_index -= self._tabs_removed_before_index(abs_index, start_index, raw_bullet_requests)
            requests.append(
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": abs_index,
                            "endIndex": abs_index + 1,
                        }
                    }
                }
            )
            requests.append(
                {
                    "insertInlineImage": {
                        "location": {"index": abs_index},
                        "uri": uri,
                    }
                }
            )
        return requests

    def _build_table_replacement_requests(self, start_index: int, raw_bullet_requests: list[dict]) -> list[dict]:
        """
        Build deferred table replacement requests.

        For each buffered table placeholder, emit:
        1) deleteContentRange for the placeholder character
        2) insertTable at the same index

        Requests are emitted in descending index order to prevent index-shift
        invalidation when multiple tables exist in a single markdown payload.
        """
        requests: list[dict] = []
        for rel_index, rows, cols in sorted(self._pending_table_insertions, key=lambda item: item[0], reverse=True):
            abs_index = start_index + rel_index
            abs_index -= self._tabs_removed_before_index(abs_index, start_index, raw_bullet_requests)
            requests.append(
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": abs_index,
                            "endIndex": abs_index + 1,
                        }
                    }
                }
            )
            requests.append(
                {
                    "insertTable": {
                        "location": {"index": abs_index},
                        "rows": rows,
                        "columns": cols,
                    }
                }
            )
        return requests

    def _build_person_mention_requests(self, start_index: int, raw_bullet_requests: list[dict]) -> list[dict]:
        """
        Build deferred person-mention replacement requests.

        In person-chip mode, mention tokens are inserted as literal text first
        so fallback is always safe. This method creates replacement pairs:
        1) deleteContentRange over the literal token range
        2) insertPerson at the same start index

        Requests are emitted in descending range order to avoid index drift when
        multiple mentions are replaced sequentially.
        """
        if self.mention_mode != "person_chip" or not self.pending_person_mentions:
            return []

        requests: list[dict] = []
        for rel_start, rel_end, email in sorted(self.pending_person_mentions, key=lambda item: item[0], reverse=True):
            abs_start = start_index + rel_start
            abs_end = start_index + rel_end
            abs_start -= self._tabs_removed_before_index(abs_start, start_index, raw_bullet_requests)
            abs_end -= self._tabs_removed_before_index(abs_end, start_index, raw_bullet_requests)
            requests.append(
                {
                    "deleteContentRange": {
                        "range": {
                            "startIndex": abs_start,
                            "endIndex": abs_end,
                        }
                    }
                }
            )
            requests.append(
                {
                    "insertPerson": {
                        "location": {"index": abs_start},
                        "personProperties": {"email": email},
                    }
                }
            )
        return requests

    def _insert_text_with_person_mentions(self, text: str) -> None:
        """
        Insert text and track @user@example.com tokens for person-chip replacement.

        Tokens are kept as literal text in the base insertion pass so failed
        mention replacement calls can gracefully fall back without data loss.
        """
        if not text:
            return

        cursor = 0
        for match in PERSON_MENTION_PATTERN.finditer(text):
            start, end = match.span()
            if start > cursor:
                self._insert_text(text[cursor:start])

            mention_literal = match.group(0)
            email = match.group(1)
            rel_start = len(self._text_buffer)
            self._insert_text(mention_literal)
            rel_end = len(self._text_buffer)
            self.pending_person_mentions.append((rel_start, rel_end, email))
            cursor = end

        if cursor < len(text):
            self._insert_text(text[cursor:])

    def _tabs_removed_before_index(self, abs_index: int, start_index: int, raw_bullet_requests: list[dict]) -> int:
        """
        Return the cumulative TAB count removed by createParagraphBullets before abs_index.

        Google Docs removes leading TAB characters when paragraph bullets are created.
        Placeholder-based structural requests (images/tables) must subtract this shift
        to target the correct post-bullet indices.
        """
        removed_tabs = 0
        for req in raw_bullet_requests:
            if "createParagraphBullets" not in req:
                continue

            bullet_range = req["createParagraphBullets"]["range"]
            range_start = bullet_range["startIndex"]
            range_end = bullet_range["endIndex"]

            if abs_index <= range_start:
                continue

            capped_end = min(abs_index, range_end)
            if capped_end <= range_start:
                continue

            buffer_start = max(0, range_start - start_index)
            buffer_end = max(buffer_start, capped_end - start_index)
            removed_tabs += self._text_buffer[buffer_start:buffer_end].count("\t")

        return removed_tabs

    def _adjust_bullet_indices_for_tab_removal(self, bullet_requests: list[dict], start_index: int) -> list[dict]:
        """
        Adjust createParagraphBullets indices to account for TAB removal.

        When createParagraphBullets processes a range, it removes leading TABs,
        which shifts all subsequent indices. This method adjusts later bullet
        requests to use post-shift indices.

        Args:
            bullet_requests: List of bullet-related requests (create and delete)
            start_index: The document start index for text insertion

        Returns:
            Adjusted list of requests with corrected indices
        """
        if not bullet_requests:
            return bullet_requests

        adjusted: list[dict] = []
        cumulative_tab_shift = 0

        for req in bullet_requests:
            if "createParagraphBullets" in req:
                r = req["createParagraphBullets"]["range"]
                original_start = r["startIndex"]
                original_end = r["endIndex"]

                adjusted_start = original_start - cumulative_tab_shift
                adjusted_end = original_end - cumulative_tab_shift

                buffer_start = original_start - start_index
                buffer_end = original_end - start_index
                text_in_range = self._text_buffer[buffer_start:buffer_end]
                tabs_in_range = text_in_range.count("\t")

                adjusted_req = {
                    "createParagraphBullets": {
                        "range": {
                            "startIndex": adjusted_start,
                            "endIndex": adjusted_end,
                        },
                        "bulletPreset": req["createParagraphBullets"]["bulletPreset"],
                    }
                }
                adjusted.append(adjusted_req)

                cumulative_tab_shift += tabs_in_range
                logger.debug(
                    f"Adjusted bullet range [{original_start}, {original_end}] -> "
                    f"[{adjusted_start}, {adjusted_end}] (removed {tabs_in_range} TABs, "
                    f"cumulative shift: {cumulative_tab_shift})"
                )
            elif "deleteParagraphBullets" in req:
                r = req["deleteParagraphBullets"]["range"]
                adjusted_req = {
                    "deleteParagraphBullets": {
                        "range": {
                            "startIndex": r["startIndex"] - cumulative_tab_shift,
                            "endIndex": r["endIndex"] - cumulative_tab_shift,
                        }
                    }
                }
                adjusted.append(adjusted_req)
            else:
                adjusted.append(req)

        return adjusted
