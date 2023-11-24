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

        # Check if there's a diff for README.md
        if diffs:
            return diffs[0].diff.decode('utf-8')
        else:
            parent_blob = parent_commit.tree / self.file_name
            for line in parent_blob.data_stream.read().decode('utf-8').splitlines():
                print(f' {line}')  # Each line preceded by a space

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
        branch_commits = list(repo.iter_commits(f'{self.base_ref}..HEAD'))[::-1]  # replace 'master' with your branch name

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


        print('---')
        for commit in commits:
            print(commit)

            # Populate file histories for files that were changed in this commit
            for cfile in commit.changed_files:
                print(cfile)
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

        # from pprint import pprint
        # print(self.file_histories)
        #
        # print('---------')
        # for f_commit in self.file_histories['README.md'].file_commits.value():
        #     print(sha, f_commit)
        # raise Exception()

    # seen_files = {}
    # # Display the parsed commits
    # for commit in commits:
    #     for file in commit.files:
    #         if file.file_name == file.prev_file_name:
    #             if file.file_name in [n[-1] for n in seen_files.values()]:
    #                 continue
    #             else:
    #                 seen_files[file.file_name] = [file.file_name]
    #
    #         elif file.prev_file_name:
    #             for _, val in seen_files.items():
    #                 if val[-1] == file.prev_file_name:
    #                     val.append(file.file_name)
    #
    # curr_name_pointer = {key: (0, val[0]) for key, val in seen_files.items()}
    #
    # for commit in commits:
    #     for first_file_name in seen_files.items():
    #         i, curr_file_name = curr_name_pointer[first_file_name]
    #
    #         found_changed_file = False
    #         for f in commit.changed_files:
    #             if f.prev_file_name == curr_file_name:
    #                 commit.files.append(f)
    #                 found_changed_file = True
    #                 curr_name_pointer[first_file_name] = (i+1, f.file_name)
    #
    #         if not found_changed_file:
    #             commit.files.append(File(curr_file_name))

# def _arrange_by_file(commit_data):
#     file_history = {}
#     rename_map = {}
#
#     for commit in commit_data:
#         commit_hash = commit['commit']
#
#         for file in commit['files']:
#             file_name = file['name']
#             action = file['action']
#
#             # Check for renames and update the rename map
#             if action == 'moved':
#                 original_name = file_name
#                 new_name = file['updated_name']
#                 rename_map[original_name] = new_name
#                 file_name = new_name
#
#             # Find the original name if the file was renamed in the past
#             original_name = rename_map.get(file_name, file_name)
#
#             # Update or create the entry
#             if original_name not in file_history:
#                 file_history[original_name] = {}
#             file_history[original_name][commit_hash] = file_name
#
#     # Convert the history into the desired format
#     result = []
#     for end_file_name, history in file_history.items():
#         commit_info = {commit: {'file_name': fname} for commit, fname in history.items()}
#         result.append({'end_file_name': end_file_name, 'commit_hash': commit_info})
#
#     return result

def get_file_contents(commit, file_name):
    return git(["show", f"{commit}:{file_name}"])
