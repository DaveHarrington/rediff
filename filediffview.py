from textual.widgets import TextArea, Static
from textual.strip import Strip
from textual.message import Message
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

class FileDiffView(TextArea):
    class ParentCommand(Message):
        def __init__(self, cmd, data=None):
            super().__init__()
            self.cmd = cmd
            self.data = data

    def __init__(self, file_commit, all_patches, total_length):
        super().__init__()
        self.file_name = file_commit.file_name
        self.show_line_numbers = False
        self.text = file_commit.get_content(all_patches, total_length)

    def _on_key(self, event):
        event.prevent_default()

        if event.character == "j":
            self.post_message(
                self.ParentCommand(
                    "cursor_move",
                    {"location": self.get_cursor_down_location()}
                ),
            )
        elif event.character == "k":
            self.post_message(
                self.ParentCommand(
                    "cursor_move",
                    {"location": self.get_cursor_up_location()}
                ),
            )
        elif event.character == "h":
            self.move_cursor_relative(columns=-1) # Move left
        elif event.character == "l":
            self.move_cursor_relative(columns=1) # Move right

        elif event.character == "H":
            self.post_message(self.ParentCommand("focus_pane_left"))
        elif event.character == "L":
            self.post_message(self.ParentCommand("focus_pane_right"))
        elif event.character == "K":
            self.post_message(self.ParentCommand("focus_file_prev"))
        elif event.character == "J":
            self.post_message(self.ParentCommand("focus_file_next"))

    def render_line(self, widget_y: int) -> Strip:
        """Render a single line of the TextArea. Called by Textual.

        Args:
            widget_y: Y Coordinate of line relative to the widget region.

        Returns:
            A rendered line.
        """
        document = self.document
        scroll_x, scroll_y = self.scroll_offset

        # Account for how much the TextArea is scrolled.
        line_index = widget_y + scroll_y

        # Render the lines beyond the valid line numbers
        out_of_bounds = line_index >= document.line_count
        if out_of_bounds:
            return Strip.blank(self.size.width)

        theme = self._theme

        # Get the line from the Document.
        line_string = document.get_line(line_index)
        line = Text(line_string, end="")

        if line_string.startswith("@"):
            return Strip.blank(self.size.width)
        elif line_string.startswith("x"):
            # Placeholder line for a later addition
            line.stylize("on blue")
        if line_string.startswith("+"):
            line.stylize("on green")
        elif line_string.startswith("-"):
            line.stylize("on red")
        elif line_string.startswith(" "):
            pass
        line_string = line_string[1:]

        line_character_count = len(line)
        line.tab_size = self.indent_width
        virtual_width, virtual_height = self.virtual_size
        expanded_length = max(virtual_width, self.size.width)
        line.set_length(expanded_length)

        selection = self.selection
        start, end = selection
        selection_top, selection_bottom = sorted(selection)
        selection_top_row, selection_top_column = selection_top
        selection_bottom_row, selection_bottom_column = selection_bottom

        highlights = self._highlights
        if highlights and theme:
            line_bytes = _utf8_encode(line_string)
            byte_to_codepoint = build_byte_to_codepoint_dict(line_bytes)
            get_highlight_from_theme = theme.syntax_styles.get
            line_highlights = highlights[line_index]
            for highlight_start, highlight_end, highlight_name in line_highlights:
                node_style = get_highlight_from_theme(highlight_name)
                if node_style is not None:
                    line.stylize(
                        node_style,
                        byte_to_codepoint.get(highlight_start, 0),
                        byte_to_codepoint.get(highlight_end) if highlight_end else None,
                    )

        cursor_row, cursor_column = end
        cursor_line_style = theme.cursor_line_style if theme else None
        if cursor_line_style and cursor_row == line_index:
            line.stylize(cursor_line_style)

        # Selection styling
        if start != end and selection_top_row <= line_index <= selection_bottom_row:
            # If this row intersects with the selection range
            selection_style = theme.selection_style if theme else None
            cursor_row, _ = end
            if selection_style:
                if line_character_count == 0 and line_index != cursor_row:
                    # A simple highlight to show empty lines are included in the selection
                    line = Text("▌", end="", style=Style(color=selection_style.bgcolor))
                    line.set_length(self.virtual_size.width)
                else:
                    if line_index == selection_top_row == selection_bottom_row:
                        # Selection within a single line
                        line.stylize(
                            selection_style,
                            start=selection_top_column,
                            end=selection_bottom_column,
                        )
                    else:
                        # Selection spanning multiple lines
                        if line_index == selection_top_row:
                            line.stylize(
                                selection_style,
                                start=selection_top_column,
                                end=line_character_count,
                            )
                        elif line_index == selection_bottom_row:
                            line.stylize(selection_style, end=selection_bottom_column)
                        else:
                            line.stylize(selection_style, end=line_character_count)

        # Highlight the cursor
        matching_bracket = self._matching_bracket_location
        match_cursor_bracket = self.match_cursor_bracket
        draw_matched_brackets = (
            match_cursor_bracket and matching_bracket is not None and start == end
        )

        if cursor_row == line_index:
            draw_cursor = not self.cursor_blink or (
                self.cursor_blink and self._cursor_blink_visible
            )
            if draw_matched_brackets:
                matching_bracket_style = theme.bracket_matching_style if theme else None
                if matching_bracket_style:
                    line.stylize(
                        matching_bracket_style,
                        cursor_column,
                        cursor_column + 1,
                    )

            if draw_cursor:
                cursor_style = theme.cursor_style if theme else None
                if cursor_style:
                    line.stylize(cursor_style, cursor_column, cursor_column + 1)

        # Highlight the partner opening/closing bracket.
        if draw_matched_brackets:
            # mypy doesn't know matching bracket is guaranteed to be non-None
            assert matching_bracket is not None
            bracket_match_row, bracket_match_column = matching_bracket
            if theme and bracket_match_row == line_index:
                matching_bracket_style = theme.bracket_matching_style
                if matching_bracket_style:
                    line.stylize(
                        matching_bracket_style,
                        bracket_match_column,
                        bracket_match_column + 1,
                    )

        # Build the gutter text for this line
        gutter_width = self.gutter_width
        if self.show_line_numbers:
            if cursor_row == line_index:
                gutter_style = theme.cursor_line_gutter_style if theme else None
            else:
                gutter_style = theme.gutter_style if theme else None

            gutter_width_no_margin = gutter_width - 2
            gutter = Text(
                f"{line_index + 1:>{gutter_width_no_margin}}  ",
                style=gutter_style or "",
                end="",
            )
        else:
            gutter = Text("", end="")

        # Render the gutter and the text of this line
        console = self.app.console
        gutter_segments = console.render(gutter)
        text_segments = console.render(
            line,
            console.options.update_width(expanded_length),
        )

        # Crop the line to show only the visible part (some may be scrolled out of view)
        gutter_strip = Strip(gutter_segments, cell_length=gutter_width)
        text_strip = Strip(text_segments).crop(
            scroll_x, scroll_x + virtual_width - gutter_width
        )

        # Stylize the line the cursor is currently on.
        if cursor_row == line_index:
            text_strip = text_strip.extend_cell_length(
                expanded_length, cursor_line_style
            )
        else:
            text_strip = text_strip.extend_cell_length(
                expanded_length, theme.base_style if theme else None
            )

        # Join and return the gutter and the visible portion of this line
        strip = Strip.join([gutter_strip, text_strip]).simplify()

        return strip.apply_style(
            theme.base_style
            if theme and theme.base_style is not None
            else self.rich_style
        )

