import click

from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import HorizontalScroll

import db

class SingleFileAllCommits(HorizontalScroll):
    def __init__(self, commits, file_data):
        super().__init__()
        self.commits = commits
        self.file_data = file_data
        self.file_views = {}

    def compose(self):
        for i, commit in enumerate(self.commits):
            file_name = self.file_data["end_filename"]
            if i == 0:
                contents = git.get_file_contents(commit, file_name)
            else:
                contents = git.get_file_diff_contents(commit, file_name)
            print(i)
            print(commit)
            print(contents)

            self.file_views[commit] = FileDiffView(
                self.file_data["end_filename"],
                contents,
            )
        yield HorizontalScroll(*self.file_views.values())

class FileDiffView(TextArea):
    def __init__(self, file_name, contents):
        super().__init__()
        self.file_name = file_name
        self.text = contents

class Rediff(App):
    CSS_PATH = "app.tcss"

    def __init__(self, base_ref, repo_path):
        super().__init__()
        self.commits = git.get_commit_history(base_ref)
        self.files_history = git.get_files_history(base_ref)

    def compose(self) -> ComposeResult:
        self.file_views = {}
        for file_data in [self.files_history[0]]:
            file1 = SingleFileAllCommits(self.commits, file_data)

        yield file1

@click.command()
@click.argument('base_ref', type=str)
@click.option('-C', '--repo_path', type=str, default='.', help='The repository path (optional)')
def main(base_ref, repo_path):
    app = Rediff(base_ref, repo_path)
    app.run()

if __name__ == "__main__":
    main()
