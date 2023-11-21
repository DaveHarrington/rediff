from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import ScrollableContainer

from lib import git


class SingleFileAllCommits(Static):
    def __init__(self, commits, file_data):
        super().__init__()
        self.commits = commits
        self.file_data = file_data
        self.file_views = {}

    def compose(self) -> ComposeResult:
        print(self.file_data)
        for commit in self.commits:
            self.file_views[commit] = FileDiffView(
                self.file_data["end_filename"],
                commit,
            )
        yield ScrollableContainer(*self.file_views.values())

class FileDiffView(Static):
    def __init__(self, file_name, commit):
        super().__init__()
        self.file_name = file_name
        self.contents = git.get_file_contents(commit, file_name)

    def compose(self) -> ComposeResult:
        yield TextArea(self.contents)

class Rediff(App):
    CSS_PATH = "app.tcss"

    def __init__(self):
        super().__init__()
        base_commit = "main"
        self.commits = git.get_commit_history(base_commit)
        self.files_history = git.get_files_history(base_commit)

    def compose(self) -> ComposeResult:
        self.file_views = {}
        for file_data in [self.files_history[0]]:
            # self.file_views[file_data["end_filename"]] = SingleFileAllCommits(self.commits, file_data)
            x = SingleFileAllCommits(self.commits, file_data)

        yield x

app = Rediff()
if __name__ == "__main__":
    app.run()

