import unittest
import tempfile
import os

from git import Repo, GitCommandError

from rediff.db import GitData, PatchType

class TestGitOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_path = tempfile.mkdtemp()
        cls.repo = Repo.init(cls.repo_path)
        cls.repo.git.checkout("-b", "main")
        cls.file1 = "FILE1"
        cls.file1_path = os.path.join(cls.repo_path, cls.file1)
        with open(cls.file1_path, "w") as file:
            file.write("FILE1 line 1\n")
        cls.file2 = "FILE2"
        cls.file2_path = os.path.join(cls.repo_path, cls.file2)
        with open(cls.file2_path, "w") as file:
            file.write("FILE2 line 1\n")
        cls.repo.index.add([cls.file1_path, cls.file2_path])
        cls.repo.index.commit("initial commit")

    def setUp(self):
        self.repo.git.checkout("main")
        branch_name = f"test_branch_{self.id()}"
        self.repo.git.checkout('-b', branch_name)

    def test_one_modified_file(self):
        new_line = "new line"
        with open(self.file1_path, "a") as file:
            file.write(f"{new_line}\n")
        self.repo.index.add([self.file1_path])
        self.repo.index.commit("Append to File1")

        gd = GitData(self.repo_path, "main")
        self.assertEqual(len(gd.file_histories), 1)

        fh = gd.file_histories[list(gd.file_histories.keys())[0]]

        self.assertEqual(fh._orig_file_name, self.file1)
        self.assertEqual(fh._current_file_name, self.file1)

        self.assertEqual(len(fh.file_commits), 1)
        self.assertEqual(len(fh.get_all_patches()), 1)

        fc = fh.file_commits[list(fh.file_commits.keys())[0]]

        self.assertEqual(fc.file_name, self.file1)
        self.assertEqual(fc.diff_text, [" FILE1 line 1", f"+{new_line}"])

        patches = fc.get_patches()
        self.assertEqual(len(patches), 1)
        patch = patches[0]
        self.assertEqual(patch.type, PatchType.ADD)
        self.assertEqual(patch.line_start, 1)
        self.assertEqual(patch.line_end, 2)

    def test_one_renamed_file(self):
        moved_path = self.file1_path + ".new"
        self.repo.git.mv(self.file1_path, moved_path)
        self.repo.index.add([moved_path])
        self.repo.index.commit("rename FILE1")

        gd = GitData(self.repo_path, "main")
        self.assertEqual(len(gd.file_histories), 1)

        fh = gd.file_histories[list(gd.file_histories.keys())[0]]

        self.assertEqual(fh._orig_file_name, self.file1)
        self.assertEqual(fh._current_file_name, self.file1 + ".new")

        self.assertEqual(len(fh.file_commits), 1)
        self.assertEqual(len(fh.get_all_patches()), 1)

        fc = fh.file_commits[list(fh.file_commits.keys())[0]]

        self.assertEqual(fc.file_name, self.file1 + ".new")
        self.assertEqual(fc.diff_text, [" FILE1 line 1"])

        patches = fc.get_patches()
        self.assertEqual(len(patches), 0)

    def test_one_modified_and_renamed_file(self):
        new_line = "new line"
        with open(self.file1_path, "a") as file:
            file.write(f"{new_line}\n")

        moved_path = self.file1_path + ".new"
        self.repo.git.mv(self.file1_path, moved_path)
        self.repo.index.add([moved_path])
        self.repo.index.commit("rename FILE1")

        gd = GitData(self.repo_path, "main")
        self.assertEqual(len(gd.file_histories), 1)

        fh = gd.file_histories[list(gd.file_histories.keys())[0]]

        self.assertEqual(fh._orig_file_name, self.file1)
        self.assertEqual(fh._current_file_name, self.file1 + ".new")

        self.assertEqual(len(fh.file_commits), 1)
        self.assertEqual(len(fh.get_all_patches()), 1)

        fc = fh.file_commits[list(fh.file_commits.keys())[0]]

        self.assertEqual(fc.file_name, self.file1 + ".new")
        self.assertEqual(fc.diff_text, [" FILE1 line 1", f"+{new_line}"])

        patches = fc.get_patches()
        self.assertEqual(len(patches), 1)
        patch = patches[0]
        self.assertEqual(patch.type, PatchType.ADD)
        self.assertEqual(patch.line_start, 1)
        self.assertEqual(patch.line_end, 2)

if __name__ == '__main__':
    unittest.main()
