import click
from collections import OrderedDict

from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical
from textual.widget import Widget
from textual.widgets import Label, Markdown

import db
from filediffview import FileDiffView

class SingleFileAllCommits(HorizontalScroll):
    def __init__(self, file_history):
        super().__init__()
        self.file_history = file_history
        self.file_views = OrderedDict()
        self._curr_pane = 0

    def compose(self):
        for file_commit in self.file_history.file_commits.values():
            self.file_views[file_commit.sha] = CommitFilePane(
                file_commit,
                self.file_history,
            )

        yield HorizontalScroll(*self.file_views.values())

    def on_mount(self):
        self.focus_pane(self._curr_pane)

    def focus_pane(self, next_pane):
        num_panes = len(self.file_views.keys())
        next_pane = min(max(0, next_pane), num_panes-1)
        for i, commit_file_pane in enumerate(self.file_views.values()):
            if i == next_pane:
                commit_file_pane.fv.show_cursor = True
                commit_file_pane.fv.focus()
            else:
                commit_file_pane.fv.show_cursor = False
        self._curr_pane = next_pane

    def on_file_diff_view_parent_command(self, command):
        print(f"here 1: {command.cmd}")
        if command.cmd == "focus_pane_left":
            print("move left")
            self.focus_pane(self._curr_pane - 1)
        elif command.cmd == "focus_pane_right":
            print("move right")
            self.focus_pane(self._curr_pane + 1)
        elif command.cmd == "cursor_move":
            print("cursor down")
            for cp in self.file_views.values():
                cp.fv.move_cursor(command.data["location"])

class CommitFilePane(Vertical):
    def __init__(self, file_commit, file_history):
        super().__init__()
        self.file_commit = file_commit
        self.file_history = file_history

    def compose(self):
        yield Label(f"{self.file_commit.commit.short}\n"
                    f"{self.file_commit.commit.summary}")
        yield Label(f"{self.file_commit.file_name}")
        self.fv = FileDiffView(
                self.file_commit,
                self.file_history.all_patches,
                self.file_history.total_length,
            )
        yield self.fv

class Rediff(App):
    CSS_PATH = "app.tcss"

    def __init__(self, repo_path, base_ref):
        super().__init__()
        self.gitdata = db.GitData(repo_path, base_ref)
        self._curr_file = 0

    def compose(self) -> ComposeResult:
        file_history = self.gitdata.get_file_history(self._curr_file)
        self.file_view = SingleFileAllCommits(file_history)
        yield self.file_view

    def show_file(self, file_num_):
        num_files = len(self.gitdata.file_histories)
        file_num = min(num_files-1, max(0, file_num_))
        if file_num != file_num_:
            return
        self.file_view.remove()

        file_history = self.gitdata.get_file_history(self._curr_file)
        self.file_view = SingleFileAllCommits(file_history)
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

@click.command()
@click.argument('base_ref', type=str)
@click.option('-C', '--repo_path', type=str, default='.', help='The repository path (optional)')
def main(base_ref, repo_path):
    app = Rediff(repo_path, base_ref)
    app.run()

if __name__ == "__main__":
    main()
