from collections import OrderedDict
from git import Repo

class FileHistory:
    def __init__(self):
        self._orig_filename = None
        self._current_filename = None
        self.commits = OrderedDict()

    def fill(self, commit, filename=None):
        if not self._orig_filename:
            self._orig_filename = filename
        self._current_filename = filename or self._current_filename

        self.commits[commit] = {
            'filename': self._current_filename,
            # FIXME store file object here
        }

    def __str__(self):
        return (f"File history: {self._orig_filename}"
                f"num commits: {len(self.commits)}")
#         filename = file_diff.b_path
#         prev_filename = file_diff.a_path
#
#         content = self.commit.tree / filename
#         edited_file = File(filename, prev_filename, content.data_stream.read().decode('utf-8'), changed=True)
#         self.changed_files.append(edited_file)
#
# class File:
#     def __init__(self, filename, prev_filename=None, content=None, changed=False):
#         self.filename = filename
#         self.prev_filename = prev_filename
#         self.content = content
#         self.changed = False
#
#     def __str__(self):
#         return (f"file: {self.filename}\n"
#                 f"prev: {self.prev_filename}\n"
#                 f"changed: {self.changed}\n")

class Commit:
    def __init__(self, commit):
        self.commit = commit
        self.title = commit.summary
        self.changed_files = []

    def __str__(self):
        return (f"commit: {self.commit}\n"
               f"title: {self.title}\n"
               f"num files: {len(self.changed_files)}")

class GitData:
    def __init__(self,repo_path, base_ref="main"):
        self.repo_path = repo_path
        self.base_ref = base_ref
        self.load(repo_path, base_ref)

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
        file_histories = {}

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
                        fh.fill(commit, c_file.b_path)

                elif cfile.deleted_file:
                    pass

                elif cfile.renamed:
                    pass

                else:
                    raise Exception("Unhandled change type")

            # Populate file histories for files that weren't changed in this commit
            for fh in file_histories.values():
                if not fh.commits.get(commit):
                    fh.fill(commit)

        self.file_histories = file_histories

        print(self.file_histories)
        raise Exception()

    # seen_files = {}
    # # Display the parsed commits
    # for commit in commits:
    #     for file in commit.files:
    #         if file.filename == file.prev_filename:
    #             if file.filename in [n[-1] for n in seen_files.values()]:
    #                 continue
    #             else:
    #                 seen_files[file.filename] = [file.filename]
    #
    #         elif file.prev_filename:
    #             for _, val in seen_files.items():
    #                 if val[-1] == file.prev_filename:
    #                     val.append(file.filename)
    #
    # curr_name_pointer = {key: (0, val[0]) for key, val in seen_files.items()}
    #
    # for commit in commits:
    #     for first_filename in seen_files.items():
    #         i, curr_filename = curr_name_pointer[first_filename]
    #
    #         found_changed_file = False
    #         for f in commit.changed_files:
    #             if f.prev_filename == curr_filename:
    #                 commit.files.append(f)
    #                 found_changed_file = True
    #                 curr_name_pointer[first_filename] = (i+1, f.filename)
    #
    #         if not found_changed_file:
    #             commit.files.append(File(curr_filename))

def _arrange_by_file(commit_data):
    file_history = {}
    rename_map = {}

    for commit in commit_data:
        commit_hash = commit['commit']

        for file in commit['files']:
            file_name = file['name']
            action = file['action']

            # Check for renames and update the rename map
            if action == 'moved':
                original_name = file_name
                new_name = file['updated_name']
                rename_map[original_name] = new_name
                file_name = new_name

            # Find the original name if the file was renamed in the past
            original_name = rename_map.get(file_name, file_name)

            # Update or create the entry
            if original_name not in file_history:
                file_history[original_name] = {}
            file_history[original_name][commit_hash] = file_name

    # Convert the history into the desired format
    result = []
    for end_filename, history in file_history.items():
        commit_info = {commit: {'file_name': fname} for commit, fname in history.items()}
        result.append({'end_filename': end_filename, 'commit_hash': commit_info})

    return result

def get_file_contents(commit, file_name):
    return git(["show", f"{commit}:{file_name}"])
