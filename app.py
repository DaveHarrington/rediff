from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import HorizontalScroll

from db import git

class SingleFileAllCommits(HorizontalScroll):
    def __init__(self, commits, file_history):
        super().__init__()
        self.commits = commits
        self.file_history = file_history
        self.file_views = {}

    def compose(self):
        for i, commit in enumerate(self.commits):
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

    def __init__(self):
        super().__init__()
        repo = "/Users/daveharrington/dev/checkpoint-env-control"
        base_commit = "master"
        self.gitdata = db.GitData(repo, base_commit)

    def compose(self) -> ComposeResult:
        self.file_views = {}
        for file_data in [self.gitdata.file_history(0)]:
            file1 = SingleFileAllCommits(self.commits, file_data)

        yield file1

app = Rediff()
if __name__ == "__main__":
    app.run()

