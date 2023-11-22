from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import HorizontalScroll, Vertical
from textual.message import Message
from textual.widgets import Footer, Label



from db import git

class SingleFileAllCommits(HorizontalScroll):
    def __init__(self, commits, file_data):
        super().__init__()
        self.commits = commits
        self.file_data = file_data
        self.file_views = {}
        self._curr_pane = 0
        self._num_panes = len(commits.values())
        print(f"HERE {self._num_panes}")

    def compose(self):
        for i, commit in enumerate(self.commits):
            file_name = self.file_data["end_filename"]
            if i == 0:
                contents = git.get_file_contents(commit, file_name)
            else:
                contents = git.get_file_diff_contents(commit, file_name)
            self.file_views[commit] = CommitFileContainer(
                commit,
                self.file_data["end_filename"],
                contents,
            )
        yield HorizontalScroll(*self.file_views.values())

    def on_mount(self):
        self.focus_pane(self._curr_pane)

    def focus_pane(self, next_pane):
        next_pane = min(max(0, next_pane), self._num_panes-1)
        list(self.file_views.values())[next_pane].focus()
        self._curr_pane = next_pane

    def on_file_diff_view_parent_command(self, command):
        print(f"here 1: {command.cmd}")
        if command.cmd == "focus_pane_left":
            print("move left")
            self.focus_pane(self._curr_pane - 1)
        if command.cmd == "focus_pane_right":
            print("move right")
            self.focus_pane(self._curr_pane + 1)

class CommitFileContainer(Vertical):
    def __init__(self, commit, file_name, contents):
        super().__init__()
        self.commit = commit
        self.file_name = file_name
        self.contents = contents

    def compose(self):
        print("HERE")
        print(self.commit)
        yield Label(self.commit["title"])

class FileDiffView(TextArea):
    class ParentCommand(Message):
        def __init__(self, cmd):
            super().__init__()
            self.cmd = cmd

    def __init__(self, contents):
        super().__init__()
        self.text = contents
        self.edit_mode = False

    def _on_key(self, event):
        if not self.edit_mode:
            event.prevent_default()

            if event.character == "j":
                self.move_cursor_relative(rows=1) # Move down
            elif event.character == "k":
                self.move_cursor_relative(rows=-1) # Move up
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

class Rediff(App):
    CSS_PATH = "app.tcss"

    def __init__(self):
        super().__init__()
        base_commit = "main"
        self.commits = git.get_commit_history(base_commit)
        self.files_history = git.get_files_history(base_commit)
        self.file_views = None
        self._curr_file = 0
        self._num_files = len(self.files_history)

    def compose(self) -> ComposeResult:
        file_data = self.files_history[self._curr_file]
        self.file_view = SingleFileAllCommits(self.commits, file_data)

        yield self.file_view

    def show_file(self, file_num):
        self.file_view.remove()

        file_data = self.files_history[min(max(0, file_num-1), self._num_files)]
        self.file_view = SingleFileAllCommits(self.commits, file_data)
        self.file_view.mount()
        self._curr_file = file_num
        self.mount(self.file_view)

    def on_file_diff_view_parent_command(self, command):
        print("here 2")
        if command.cmd == "focus_file_prev":
            print("prev file")
            self.show_file(self._curr_file - 1)
        if command.cmd == "focus_file_next":
            print("next file")
            self.show_file(self._curr_file + 1)

app = Rediff()
if __name__ == "__main__":
    app.run()

