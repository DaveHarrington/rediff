from collections import OrderedDict
from git import Repo

class FileHistory:
    def __init__(self):
        self._orig_file_name = None
        self._current_file_name = None
        self.file_commits = OrderedDict()

    def fill(self, commit, file_name=None):
        if not self._orig_file_name:
            self._orig_file_name = file_name
        self._current_file_name = file_name or self._current_file_name

        self.file_commits[commit.sha] = FileCommit(file_name, commit)

    def __str__(self):
        return (f"File history: {self._orig_file_name}, "
                f"num commits: {len(self.file_commits)}")

    def __repr__(self):
        return str(self)

class FileCommit:
    def __init__(self, file_name, commit):
        self.sha = commit.sha
        self.file_name = file_name
        self.commit = commit

    def get_file_contents(self):
        parent_commit = self.commit.commit_obj.parents[0]

        diffs = self.commit.commit_obj.diff(
            parent_commit, paths=self.file_name, create_patch=True,
            unified=999999,
        )

        if diffs:
            return diffs[0].diff.decode('utf-8')
        else:
            # No diff for this file, get file contents from parent
            parent_blob = parent_commit.tree / self.file_name
            for line in parent_blob.data_stream.read().decode('utf-8').splitlines():
                # add space for patch format (no change)
                print(f' {line}')

    def __str__(self):
        return f"FileCommit: {self.file_name} @sha: {self.sha}"

    def __repr__(self):
        return str(self)

class Commit:
    def __init__(self, commit_obj):
        self.sha = commit_obj.hexsha
        self.title = commit_obj.summary
        self.changed_files = []
        self.commit_obj = commit_obj

    def __str__(self):
        return (f"commit: {self.sha}\n"
               f"title: {self.title}\n"
               f"num files: {len(self.changed_files)}")

class GitData:
    def __init__(self,repo_path, base_ref="main"):
        self.repo_path = repo_path
        self.base_ref = base_ref
        self.load(repo_path, base_ref)

    def get_file_history(self, file_no):
        return self.file_histories[list(self.file_histories.keys())[file_no]]


    def load(self, repo_path, base_ref):
        repo = Repo(repo_path)
        branch_commits = list(repo.iter_commits(f'{self.base_ref}..HEAD'))[::-1]

        commits = []

        for commit_ in branch_commits:
            commit = Commit(commit_)

            if len(commit_.parents) > 1:
                raise Exception(f"Merge commit found: {commit_}")
            diffs = commit_.parents[0].diff(commit_) if commit_.parents else commit_.diff(NULL_TREE)

            for file_diff in diffs:
                commit.changed_files.append(file_diff)

            commits.append(commit)

        self.commits = commits

        ## Load File Histories
        file_histories = OrderedDict()

        for commit in commits:

            # Populate file histories for files that were changed in this commit
            for cfile in commit.changed_files:
                if cfile.new_file:
                    fh = FileHistory()
                    # First time seeing this file. Populate earlier history.
                    for c_inner in commits:
                        if c_inner == commit:
                            break
                        fh.fill(c_inner, None)

                    fh.fill(commit, cfile)

                    file_histories[cfile.b_path] = fh

                elif cfile.change_type == "M":
                    # Modified
                    fh = file_histories.get(cfile.b_path)
                    if not fh:
                        fh = FileHistory()
                        # First time seeing this file. Populate earlier history.
                        for c_inner in commits:
                            if c_inner == commit:
                                break
                            fh.fill(c_inner, cfile.b_path)
                        file_histories[cfile.b_path] = fh
                    else:
                        fh.fill(commit, cfile.b_path)

                elif cfile.deleted_file:
                    fh = file_histories.get(cfile.a_path)
                    if not fh:
                        fh = FileHistory()
                        # First time seeing this file. Populate earlier history.
                        for c_inner in commits:
                            if c_inner == commit:
                                break
                            fh.fill(c_inner, cfile.a_path)
                    else:
                        fh.fill(commit, cfile.a_path)

                elif cfile.renamed:
                    fh = file_histories.get(cfile.a_path)
                    if not fh:
                        fh = FileHistory()
                        # First time seeing this file. Populate earlier history.
                        for c_inner in commits:
                            if c_inner == commit:
                                break
                            fh.fill(c_inner, cfile.a_path)
                    else:
                        fh.fill(commit, cfile.b_path)

                else:
                    raise Exception("Unhandled change type")

            # Populate file histories for files that weren't changed in this commit
            for fh in file_histories.values():
                if not fh.file_commits.get(commit.sha):
                    fh.fill(commit)

        self.file_histories = file_histories

