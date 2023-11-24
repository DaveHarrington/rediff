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
        print(self.file_history)
        for file_commit in self.file_history.file_commits.values():
            print(file_commit)
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

    def __init__(self):
        super().__init__()
        repo = "/Users/drh/Projects/ai-chatgpt"
        base_commit = "main"
        self.gitdata = db.GitData(repo, base_commit)

    def compose(self) -> ComposeResult:
        self.file_views = {}
        for file_history in [self.gitdata.get_file_history(0)]:
            file1 = SingleFileAllCommits(file_history)

        yield file1

app = Rediff()
if __name__ == "__main__":
    app.run()

