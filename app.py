from textual.app import App, ComposeResult
from textual.widgets import TextArea
from textual.containers import ScrollableContainer


TEXT = """\
def hello(name):
    print("hello" + name)

def goodbye(name):
    print("goodbye" + name)
"""

class Files(ScrollableContainer):
    pass

class FileDiffView(TextArea):
    pass

class Rediff(App):
    CSS_PATH = "app.tcss"
    def compose(self) -> ComposeResult:
        yield Files(FileDiffView(TEXT, language="python"), FileDiffView(TEXT, language="python"))

app = Rediff()
if __name__ == "__main__":
    app.run()

