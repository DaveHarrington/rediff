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
            # self.file_views[file_commit.sha] = FileDiffView(
            #     file_commit,
            #     self.file_history.all_patches,
            #     self.file_history.total_length,
            # )

        yield HorizontalScroll(*self.file_views.values())

    def on_mount(self):
        # self.focus_pane(self._curr_pane)
        pass

    def focus_pane(self, next_pane):
        num_panes = len(self.file_views.keys())
        next_pane = min(max(0, next_pane), num_panes-1)
        list(self.file_views.values())[next_pane].focus()
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

    def compose(self) -> ComposeResult:
        self.file_views = {}
        for file_history in [self.gitdata.get_file_history(0)]:
            file1 = SingleFileAllCommits(file_history)

        yield file1

@click.command()
@click.argument('base_ref', type=str)
@click.option('-C', '--repo_path', type=str, default='.', help='The repository path (optional)')
def main(base_ref, repo_path):
    app = Rediff(repo_path, base_ref)
    app.run()

if __name__ == "__main__":
    main()
