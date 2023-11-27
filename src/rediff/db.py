from collections import OrderedDict
from typing import List, Optional, Union
from enum import Enum

from git import Repo, NULL_TREE
from git.objects.commit import Commit
from git.diff import Diff

class PatchType(str, Enum):
    ADD = "add"
    DELETE = "delete"

class PatchInfo:
    def __init__(self, patch_type: PatchType, line_start: int, line_end: int):
        self.type = patch_type
        self.line_start = line_start
        self.line_end = line_end

class CommitWrapper:
    def __init__(self, commit_obj: Commit):
        self.hexsha = commit_obj.hexsha
        self.short = _utf_decode(commit_obj.hexsha[:8])
        self.summary = _utf_decode(commit_obj.summary)
        self.message = commit_obj.message
        self.changed_files: List[Diff] = []
        self.commit_obj = commit_obj

    def __str__(self) -> str:
        return (f"commit: {self.hexsha}\n"
                f"summary: {self.summary}\n"
                f"num files: {len(self.changed_files)}")

class FileCommit:
    def __init__(self, file_name: str, commit: CommitWrapper):
        self.sha = commit.hexsha
        self.file_name = file_name
        self.commit = commit
        self.patches: List[PatchInfo] = []
        self.diff_text = self.load_file_content()

    def get_content(self, all_patches, total_length):
        skips = {}
        seen_our_commit = False

        for commit, patches in all_patches.items():
            if commit == self.sha:
                seen_our_commit = True
            elif not seen_our_commit:
                for patch in patches:
                    if patch['type'] == PatchType.DELETE:
                        skips[patch['line_start']] = (
                            patch['line_end'] - patch['line_start'])
                    else:
                        for patch in patches:
                            if patch['type'] == PatchType.ADD:
                                skips[patch['line_start']] = (
                                    patch['line_end'] - patch['line_start'])

        text = []
        diff_pointer = 0
        while len(text) < total_length:

            skip_len = skips.get(len(text))
            if skip_len is not None:
                for j in range(skip_len):
                    text.append('x')
                    continue

            text.append(self.diff_text[diff_pointer])
            diff_pointer += 1

        return '\n'.join(text)

    def load_file_content(self) -> List[str]:
        parent_commit = self.commit.commit_obj.parents[0]

        diffs = parent_commit.diff(
            self.commit.commit_obj,
            paths=self.file_name,
            create_patch=True,
            unified=999999,
        )

        if diffs:
            text = diffs[0].diff.decode('utf-8').splitlines()
        else:
            parent_blob = parent_commit.tree / self.file_name
            text = []
            for line in parent_blob.data_stream.read().decode('utf-8').splitlines():
                text.append(f' {line}')

        text = text[1:]

        patches: List[PatchInfo] = []
        patch_add = patch_del = None
        def finish_patch(patch_type, patch_start, line_no):
            if patch_start is not None:
                patches.append({
                    'type': patch_type,
                    'line_start': patch_start,
                    'line_end': line_no,
                })
                return None

        for line_no, line in enumerate(text):
            if line.startswith('+'):
                patch_del = self.finish_patch(PatchType.DELETE, patch_del, line_no)
                if patch_add is None:
                    patch_add = line_no
            elif line.startswith('-'):
                patch_add = self.finish_patch(PatchType.ADD, patch_add, line_no)
                if patch_del is None:
                    patch_del = line_no
            else:
                patch_add = self.finish_patch(PatchType.ADD, patch_add, line_no)
                patch_del = self.finish_patch(PatchType.DELETE, patch_del, line_no)

        self.finish_patch(PatchType.ADD, patch_add, line_no+1)
        self.finish_patch(PatchType.DELETE, patch_del, line_no+1)

        self.patches = patches

        return text

    def finish_patch(self, patch_type: PatchType, patch_start: Optional[int], line_no: int) -> Optional[int]:
        if patch_start is not None:
            self.patches.append(PatchInfo(patch_type, patch_start, line_no))
        return None

    def __str__(self) -> str:
        return f"FileCommit: {self.file_name} @sha: {self.sha}"

    def __repr__(self) -> str:
        return str(self)

class FileHistory:
    def __init__(self) -> None:
        self._orig_file_name: Optional[str] = None
        self._current_file_name: Optional[str] = None
        self.file_commits: OrderedDict[str, FileCommit] = OrderedDict()
        self.all_patches: OrderedDict[str, List[PatchInfo]] = OrderedDict()

    def fill(self, commit: CommitWrapper, file_name: Optional[str] = None) -> None:
        if not self._orig_file_name:
            self._orig_file_name = file_name
        self._current_file_name = file_name or self._current_file_name

        if not self._current_file_name:
            raise Exception("Missing file name")

        self.file_commits[commit.hexsha] = FileCommit(self._current_file_name, commit)

    def post_load(self):
        for i, (commit, fc) in enumerate(self.file_commits.items()):
            if i < len(self.file_commits):
                for p in fc.patches:
                    if p["type"] == "del":
                        for fc_ in list(self.file_commits.values())[i+1:]:
                            for p_ in fc_.patches:
                                if p_["line_start"] > p["line_start"]:
                                    p_len = p["line_end"] - p["line_start"]
                                    p_["line_start"] += p_len
                                    p_["line_end"] += p_len


            self.all_patches[commit] = fc.patches

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

    def __str__(self) -> str:
        return (f"File history: {self._orig_file_name}, "
                f"num commits: {len(self.file_commits)}")

    def __repr__(self) -> str:
        return str(self)

class GitData:
    def __init__(self, repo_path: str, base_ref: str = "main"):
        self.repo_path = repo_path
        self.base_ref = base_ref
        self.commits: List[CommitWrapper] = []
        self.file_histories: OrderedDict[str, FileHistory] = OrderedDict()
        self.load(repo_path, base_ref)

    def load(self, repo_path: str, base_ref: str) -> None:
        repo = Repo(repo_path)
        branch_commits = list(repo.iter_commits(f'{base_ref}..HEAD'))[::-1]

        commits = []

        for commit_ in branch_commits:
            commit = CommitWrapper(commit_)

            if len(commit_.parents) > 1:
                raise Exception(f"Merge commit found: {commit_}")
            diffs = commit_.parents[0].diff(commit_) if commit_.parents else commit_.diff(NULL_TREE)

            for file_diff in diffs:
                commit.changed_files.append(file_diff)

            commits.append(commit)

        self.commits = commits

        ## Load File Histories
        file_histories: OrderedDict[str, FileHistory] = OrderedDict()
        fh = None

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
                    fh.fill(commit, cfile.b_path)
                    assert isinstance(cfile.b_path, str)
                    file_histories[cfile.b_path] = fh

                elif cfile.change_type == "M":
                    # Modified
                    assert isinstance(cfile.b_path, str)
                    fh = file_histories.get(cfile.b_path)
                    if not fh:
                        fh = FileHistory()
                        # First time seeing this file. Populate earlier history.
                        for c_inner in commits:
                            if c_inner == commit:
                                break
                            fh.fill(c_inner, cfile.b_path)
                        fh.fill(commit, cfile.b_path)
                        file_histories[cfile.b_path] = fh
                    else:
                        fh.fill(commit, cfile.b_path)

                elif cfile.deleted_file:
                    assert isinstance(cfile.a_path, str)
                    fh = file_histories.get(cfile.a_path)
                    if not fh:
                        fh = FileHistory()
                        # First time seeing this file. Populate earlier history.
                        for c_inner in commits:
                            if c_inner == commit:
                                break
                            fh.fill(c_inner, cfile.a_path)
                        fh.fill(commit, cfile.b_path)
                        assert isinstance(cfile.b_path, str)
                        file_histories[cfile.b_path] = fh
                    else:
                        fh.fill(commit, cfile.a_path)

                elif cfile.renamed:
                    assert isinstance(cfile.a_path, str)
                    fh = file_histories.get(cfile.a_path)
                    if not fh:
                        fh = FileHistory()
                        # First time seeing this file. Populate earlier history.
                        for c_inner in commits:
                            if c_inner == commit:
                                break
                            fh.fill(c_inner, cfile.a_path)
                        fh.fill(commit, cfile.b_path)
                        assert isinstance(cfile.b_path, str)
                        file_histories[cfile.b_path] = fh
                    else:
                        fh.fill(commit, cfile.b_path)

                else:
                    raise Exception("Unhandled change type")

            # Populate file histories for files that weren't changed in this commit
            for fh in file_histories.values():
                if not fh.file_commits.get(commit.hexsha):
                    fh.fill(commit)

        for fh in file_histories.values():
            fh.post_load()

        for fh in file_histories.values():
            all_patches = fh.all_patches
            total_length = fh.total_length
            for fc in fh.file_commits.values():
                fc.get_content(all_patches, total_length) # exercise this code
        
        self.file_histories = file_histories

    def get_file_history(self, file_no: int) -> FileHistory:
        return self.file_histories[list(self.file_histories.keys())[file_no]]

def _utf_decode(text: Union[str, bytes]) -> str:
    if isinstance(text, bytes):
        return text.decode('utf-8')
    return text
