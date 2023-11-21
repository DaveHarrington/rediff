from textual.app import App, ComposeResult
from textual.widgets import TextArea, Static
from textual.containers import HorizontalScroll

from lib import git

TEXT = """\
def hello(name):
    print("hello" + name)

def goodbye(name):
    print("goodbye" + name)
"""


class SingleFileAllCommits(HorizontalScroll):
    def __init__(self, commits, file_data):
        super().__init__()
        self.commits = commits
        self.file_data = file_data
        self.file_views = {}

    def compose(self):
        for commit in self.commits:
            self.file_views[commit] = FileDiffView(
                self.file_data["end_filename"],
                commit,
            )
        yield HorizontalScroll(*self.file_views.values())

class FileDiffView(TextArea):
    def __init__(self, file_name, commit):
        super().__init__()
        self.file_name = file_name
        self.text = git.get_file_contents(commit, file_name)

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
            file1 = SingleFileAllCommits(self.commits, file_data)

        yield file1

app = Rediff()
if __name__ == "__main__":
    app.run()

