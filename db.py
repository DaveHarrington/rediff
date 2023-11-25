from collections import OrderedDict
from git import Repo

class FileHistory:
    def __init__(self):
        self._orig_file_name = None
        self._current_file_name = None
        self.file_commits = OrderedDict()
        self.all_patches = None
        self.total_length = None

    def fill(self, commit, file_name=None):
        if not self._orig_file_name:
            self._orig_file_name = file_name
        self._current_file_name = file_name or self._current_file_name

        self.file_commits[commit.sha] = FileCommit(file_name, commit)

    def post_load(self):
        self.all_patches = {commit: fc.patches for (commit, fc) in self.file_commits.items()}
        first_commit = list(self.file_commits.keys())[0]
        first_len = len(self.file_commits[first_commit].diff_text or "")
        extra = 0
        for i, patches in enumerate(self.all_patches.values()):
            if i == 0:
                continue
            for patch in patches:
                if patch['type'] == 'add':
                    extra += patch['line_end'] - patch['line_start']

        self.total_length = first_len + extra

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
        self.patches = []
        self.diff_text = self.load_file_content()

    def get_content(self, all_patches, total_length):
        skips = {}
        seen_our_commit = False
        for commit, patches in all_patches.items():
            if commit == self.sha:
                seen_our_commit = True
            elif not seen_our_commit:
                for patch in patches:
                    if patch['type'] == 'del':
                        skips[patch['line_start']] = patch['line_end'] - patch['line_start']
            else:
                for patch in patches:
                    if patch['type'] == 'add':
                        skips[patch['line_start']] = patch['line_end'] - patch['line_start']

        text = []
        total_pointer = diff_pointer = 0
        while total_pointer < total_length:
            skip_len = skips.get(total_pointer)
            if skip_len is not None:
                for j in range(skip_len):
                    text.append('x')
                total_pointer += skip_len
                continue

            text.append(self.diff_text[diff_pointer])
            diff_pointer += 1
            total_pointer += 1

        return '\n'.join(text)

    def load_file_content(self):
        parent_commit = self.commit.commit_obj.parents[0]

        diffs = parent_commit.diff(
            self.commit.commit_obj,
            paths=self.file_name,
            create_patch=True,
            unified=999999,
        )

        # Check if there's a diff for README.md
        if diffs:
            text = diffs[0].diff.decode('utf-8').splitlines()
        else:
            parent_blob = parent_commit.tree / self.file_name
            text = []
            for line in parent_blob.data_stream.read().decode('utf-8').splitlines():
                text.append(f' {line}')

        patches = []
        patch_add = patch_del = None
        def finish_patch(patch_type, patch_start, line_no):
            if patch_start is not None:
                patches.append({
                    'type': patch_type,
                    'line_start': patch_add,
                    'line_end': line_no,
                })
            return None

        for line_no, line in enumerate(text):
            if line.startswith('+'):
                patch_del = finish_patch('del', patch_del, line_no)
                if patch_add is None:
                    patch_add = line_no
            elif line.startswith('-'):
                patch_add = finish_patch('add', patch_add, line_no)
                if patch_del is None:
                    patch_del = line_no
            else:
                patch_add = finish_patch('add', patch_add, line_no)
                patch_del = finish_patch('del', patch_del, line_no)

        finish_patch('add', patch_add, line_no+1)
        finish_patch('del', patch_del, line_no+1)

        self.patches = patches

        return text

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

        for fh in file_histories.values():
            fh.post_load()

        for fh in file_histories.values():
            all_patches = fh.all_patches
            total_length = fh.total_length
            for fc in fh.file_commits.values():
                fc.get_content(all_patches, total_length)


        self.file_histories = file_histories

        # from pprint import pprint
        # print(self.file_histories)
        #
        # print('---------')
        # for f_commit in self.file_histories['README.md'].file_commits.value():
        #     print(sha, f_commit)
        #
        # raise Exception()
