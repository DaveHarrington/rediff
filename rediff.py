import click
from collections import OrderedDict

from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import HorizontalScroll

import db

class SingleFileAllCommits(HorizontalScroll):
    def __init__(self, file_history):
        super().__init__()
        self.file_history = file_history
        self.file_views = OrderedDict()

    def compose(self):
        for file_commit in self.file_history.file_commits.values():
            self.file_views[file_commit.sha] = FileDiffView(
                file_commit,
            )
        yield HorizontalScroll(*self.file_views.values())

class FileDiffView(TextArea):
    def __init__(self, file_commit):
        super().__init__()
        self.file_name = file_commit.file_name
        self.text = file_commit.get_file_contents()

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
