import unittest
import subprocess
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from release_notes_generator import GitCommit, ReleaseNotesGenerator


class TestGitCommit(unittest.TestCase):
    """Test cases for the GitCommit class."""

    def test_parse_commit_message_conventional_format(self):
        """Test parsing of conventional commit format."""
        commit = GitCommit("abc123", "feat(auth): add login functionality", "John Doe", "2023-01-01")
        
        self.assertEqual(commit.type, "feat")
        self.assertEqual(commit.scope, "auth")
        self.assertEqual(commit.description, "add login functionality")

    def test_parse_commit_message_without_scope(self):
        """Test parsing of commit without scope."""
        commit = GitCommit("abc123", "fix: resolve issue with authentication", "Jane Doe", "2023-01-01")
        
        self.assertEqual(commit.type, "fix")
        self.assertEqual(commit.scope, "")
        self.assertEqual(commit.description, "resolve issue with authentication")

    def test_parse_commit_message_other_type(self):
        """Test parsing of non-conventional commit message."""
        commit = GitCommit("abc123", "Update README file", "John Doe", "2023-01-01")
        
        self.assertEqual(commit.type, "other")
        self.assertEqual(commit.scope, "")
        self.assertEqual(commit.description, "Update README file")

    def test_parse_commit_message_with_complex_description(self):
        """Test parsing of commit with complex description."""
        commit = GitCommit("abc123", "refactor(api): improve error handling and logging", "Dev Team", "2023-01-01")
        
        self.assertEqual(commit.type, "refactor")
        self.assertEqual(commit.scope, "api")
        self.assertEqual(commit.description, "improve error handling and logging")

    def test_init_sets_properties_correctly(self):
        """Test that GitCommit initialization sets all properties correctly."""
        commit = GitCommit("abc12345", "Initial commit", "Author Name", "2023-01-01")
        
        self.assertEqual(commit.hash, "abc12345")
        self.assertEqual(commit.subject, "Initial commit")
        self.assertEqual(commit.author, "Author Name")
        self.assertEqual(commit.date, "2023-01-01")


class TestReleaseNotesGenerator(unittest.TestCase):
    """Test cases for the ReleaseNotesGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = ReleaseNotesGenerator()

    @patch('subprocess.run')
    def test_run_git_command_success(self, mock_subprocess):
        """Test successful execution of git command."""
        mock_result = Mock()
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = self.generator.run_git_command(["status"])
        
        self.assertEqual(result, "output")
        mock_subprocess.assert_called_once()

    @patch('subprocess.run')
    def test_run_git_command_failure_no_allow_failure(self, mock_subprocess):
        """Test git command failure without allowing failure."""
        mock_subprocess.side_effect = Exception("Command failed")
        
        with self.assertRaises(Exception):
            self.generator.run_git_command(["invalid-command"])

    @patch('subprocess.run')
    def test_run_git_command_failure_with_allow_failure(self, mock_subprocess):
        """Test git command failure with allow_failure enabled."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(returncode=1, cmd=['git', 'invalid-command'])
        
        result = self.generator.run_git_command(["invalid-command"], allow_failure=True)
        
        self.assertIsNone(result)

    @patch.object(ReleaseNotesGenerator, 'run_git_command')
    def test_is_git_repo_true(self, mock_run_git_command):
        """Test is_git_repo returns True when valid git repo."""
        mock_run_git_command.return_value = ".git"
        
        result = self.generator.is_git_repo()
        
        self.assertTrue(result)

    @patch.object(ReleaseNotesGenerator, 'run_git_command')
    def test_is_git_repo_false(self, mock_run_git_command):
        """Test is_git_repo returns False when not a git repo."""
        mock_run_git_command.return_value = None
        
        result = self.generator.is_git_repo()
        
        self.assertFalse(result)

    def test_categorize_commits_basic(self):
        """Test basic commit categorization."""
        commits = [
            GitCommit("abc123", "feat: add new feature", "Author", "2023-01-01"),
            GitCommit("def456", "fix: resolve bug", "Author", "2023-01-01"),
            GitCommit("ghi789", "chore: update config", "Author", "2023-01-01")
        ]
        
        categorized = self.generator.categorize_commits(commits)
        
        self.assertIn('feat', categorized)
        self.assertIn('fix', categorized)
        self.assertIn('chore', categorized)
        self.assertEqual(len(categorized['feat']), 1)
        self.assertEqual(len(categorized['fix']), 1)
        self.assertEqual(len(categorized['chore']), 1)

    def test_categorize_commits_unrecognized_type(self):
        """Test categorization of commits with unrecognized types."""
        commits = [
            GitCommit("abc123", "unknown: some commit", "Author", "2023-01-01")
        ]
        
        categorized = self.generator.categorize_commits(commits)
        
        # Unrecognized types should go to 'other' category
        self.assertIn('other', categorized)
        self.assertEqual(len(categorized['other']), 1)

    def test_categorize_commits_empty_list(self):
        """Test categorization with empty commit list."""
        categorized = self.generator.categorize_commits([])
        
        # Should return an empty dict since all categories are empty
        self.assertEqual(categorized, {})

    def test_generate_markdown_basic(self):
        """Test basic markdown generation."""
        commits = [
            GitCommit("abc123", "feat: add login", "Author", "2023-01-01"),
            GitCommit("def456", "fix: resolve issue", "Author2", "2023-01-01")
        ]
        
        markdown = self.generator.generate_markdown("v1.0.0", "v1.1.0", commits)
        
        self.assertIn("# Release v1.1.0", markdown)
        self.assertIn("**Tags:** `v1.0.0` ... `v1.1.0`", markdown)
        self.assertIn("## Features", markdown)
        self.assertIn("## Bug Fixes", markdown)
        self.assertIn("add login", markdown)
        self.assertIn("resolve issue", markdown)

    def test_generate_markdown_custom_title(self):
        """Test markdown generation with custom title."""
        commits = [
            GitCommit("abc123", "feat: add login", "Author", "2023-01-01")
        ]
        
        markdown = self.generator.generate_markdown(
            "v1.0.0", "v1.1.0", commits, version_title="My Custom Release"
        )
        
        self.assertIn("# My Custom Release", markdown)

    def test_generate_markdown_no_commits(self):
        """Test markdown generation with no commits."""
        markdown = self.generator.generate_markdown("v1.0.0", "v1.1.0", [])
        
        self.assertIn("# Release v1.1.0", markdown)
        self.assertIn("No significant changes.", markdown)

    def test_generate_markdown_with_scope(self):
        """Test markdown generation with commit scopes."""
        commits = [
            GitCommit("abc123", "feat(auth): add login", "Author", "2023-01-01")
        ]
        
        markdown = self.generator.generate_markdown("v1.0.0", "v1.1.0", commits)
        
        self.assertIn("add login **(auth)**", markdown)

    @patch.object(ReleaseNotesGenerator, 'get_latest_tags')
    @patch.object(ReleaseNotesGenerator, 'get_commits_between_tags')
    @patch.object(ReleaseNotesGenerator, 'generate_markdown')
    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    def test_generate_release_notes_defaults(self, mock_is_git_repo, mock_generate_md, 
                                           mock_get_commits, mock_get_tags):
        """Test generate_release_notes with default parameters."""
        mock_is_git_repo.return_value = True
        mock_get_tags.return_value = ["v1.1.0", "v1.0.0"]
        mock_get_commits.return_value = []
        mock_generate_md.return_value = "# Release Notes"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            temp_filename = tmp_file.name
        
        try:
            result = self.generator.generate_release_notes(output_file=temp_filename)
            
            self.assertEqual(result, "# Release Notes")
            mock_get_tags.assert_called_once()
            mock_get_commits.assert_called_once_with("v1.0.0", "v1.1.0")
        finally:
            os.unlink(temp_filename)

    @patch.object(ReleaseNotesGenerator, 'get_latest_tags')
    @patch.object(ReleaseNotesGenerator, 'get_commits_between_tags')
    @patch.object(ReleaseNotesGenerator, 'generate_markdown')
    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    def test_generate_release_notes_custom_tags(self, mock_is_git_repo, mock_generate_md, 
                                              mock_get_commits, mock_get_tags):
        """Test generate_release_notes with custom tags."""
        mock_is_git_repo.return_value = True
        mock_get_tags.return_value = ["v2.0.0", "v1.5.0", "v1.0.0"]
        mock_get_commits.return_value = []
        mock_generate_md.return_value = "# Release Notes"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            temp_filename = tmp_file.name
        
        try:
            result = self.generator.generate_release_notes(
                start_tag="v1.0.0", 
                end_tag="v2.0.0", 
                output_file=temp_filename
            )
            
            self.assertEqual(result, "# Release Notes")
            mock_get_commits.assert_called_once_with("v1.0.0", "v2.0.0")
        finally:
            os.unlink(temp_filename)

    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    def test_generate_release_notes_not_git_repo(self, mock_is_git_repo):
        """Test generate_release_notes raises exception when not in git repo."""
        mock_is_git_repo.return_value = False
        
        with self.assertRaises(Exception) as context:
            self.generator.generate_release_notes()
        
        self.assertIn("not a Git repository", str(context.exception))

    @patch.object(ReleaseNotesGenerator, 'get_latest_tags')
    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    def test_generate_release_notes_no_tags(self, mock_is_git_repo, mock_get_tags):
        """Test generate_release_notes raises exception when no tags exist."""
        mock_is_git_repo.return_value = True
        mock_get_tags.return_value = []
        
        with self.assertRaises(Exception) as context:
            self.generator.generate_release_notes()
        
        self.assertIn("No tags found", str(context.exception))

    @patch.object(ReleaseNotesGenerator, 'get_latest_tags')
    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    def test_generate_release_notes_single_tag(self, mock_is_git_repo, mock_get_tags):
        """Test generate_release_notes raises exception when only one tag exists."""
        mock_is_git_repo.return_value = True
        mock_get_tags.return_value = ["v1.0.0"]
        
        with self.assertRaises(Exception) as context:
            self.generator.generate_release_notes()
        
        self.assertIn("Need at least 2 tags", str(context.exception))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_commit_message_edge_cases(self):
        """Test parsing of edge case commit messages."""
        # Test commit with multiple colons
        commit = GitCommit("abc123", "feat(scope): fix: important issue", "Author", "2023-01-01")
        self.assertEqual(commit.type, "feat")
        self.assertEqual(commit.scope, "scope")
        self.assertEqual(commit.description, "fix: important issue")

        # Test commit with special characters in scope
        commit = GitCommit("def456", "fix(api-v2): handle special chars", "Author", "2023-01-01")
        self.assertEqual(commit.type, "fix")
        self.assertEqual(commit.scope, "api-v2")
        self.assertEqual(commit.description, "handle special chars")

        # Test commit with empty description - this will be treated as 'other' because () is not a valid scope
        commit = GitCommit("ghi789", "chore(): ", "Author", "2023-01-01")
        self.assertEqual(commit.type, "other")  # Because "chore()" doesn't match the pattern properly
        self.assertEqual(commit.scope, "")
        self.assertEqual(commit.description, "chore(): ")

        # Test commit with no conventional format
        commit = GitCommit("jkl012", "Just a plain commit message", "Author", "2023-01-01")
        self.assertEqual(commit.type, "other")
        self.assertEqual(commit.scope, "")
        self.assertEqual(commit.description, "Just a plain commit message")

    @patch.object(ReleaseNotesGenerator, 'run_git_command')
    def test_get_latest_tags_date_sorting(self, mock_run_git_command):
        """Test that get_latest_tags sorts tags by date correctly."""
        mock_run_git_command.return_value = (
            "v1.2.0|2023-03-01 10:00:00 +0000\n"
            "v1.0.0|2023-01-01 10:00:00 +0000\n"
            "v1.1.0|2023-02-01 10:00:00 +0000"
        )
        
        generator = ReleaseNotesGenerator()
        tags = generator.get_latest_tags()
        
        # Should be ordered from newest to oldest
        self.assertEqual(tags, ["v1.2.0", "v1.1.0", "v1.0.0"])

    @patch.object(ReleaseNotesGenerator, 'run_git_command')
    def test_get_latest_tags_fallback(self, mock_run_git_command):
        """Test fallback when date parsing fails."""
        # First call (with date) fails, second call (simple tags) succeeds
        # Need to make is_git_repo return True first
        def side_effect_func(command, allow_failure=False):
            if command == ["rev-parse", "--git-dir"]:
                return ".git"  # Simulate git repo exists
            elif "for-each-ref" in command:
                raise Exception("Date command failed")  # Fail the date command
            elif "tag" in command and "-l" in command:
                return "v1.1.0\nv1.0.0\nv0.9.0"  # Succeed with simple tag listing
            return "default"
        
        mock_run_git_command.side_effect = side_effect_func
        
        generator = ReleaseNotesGenerator()
        tags = generator.get_latest_tags()
        
        # Should fall back to simple tag listing
        self.assertIn("v1.1.0", tags)
        self.assertIn("v1.0.0", tags)

    def test_categorize_commits_case_insensitive(self):
        """Test that commit type categorization is case insensitive."""
        commits = [
            GitCommit("abc123", "Feat: new feature", "Author", "2023-01-01"),
            GitCommit("def456", "FIX: bug fix", "Author", "2023-01-01"),
            GitCommit("ghi789", "REFACTOR: code cleanup", "Author", "2023-01-01")
        ]
        
        generator = ReleaseNotesGenerator()
        categorized = generator.categorize_commits(commits)
        
        # Should match regardless of case
        self.assertIn('feat', categorized)
        self.assertIn('fix', categorized)
        self.assertIn('refactor', categorized)

    def test_categorize_commits_synonyms(self):
        """Test that synonyms are handled correctly."""
        commits = [
            GitCommit("abc123", "feature: new feature", "Author", "2023-01-01"),
            GitCommit("def456", "bugfix: critical bug fix", "Author", "2023-01-01"),
            GitCommit("ghi789", "docs: update docs", "Author", "2023-01-01"),
            GitCommit("jkl012", "test: add tests", "Author", "2023-01-01")
        ]
        
        generator = ReleaseNotesGenerator()
        categorized = generator.categorize_commits(commits)
        
        # Synonyms should map to the same categories
        self.assertIn('feature', categorized)  # Maps to 'Features' section
        self.assertIn('bugfix', categorized)  # Maps to 'Bug Fixes' section
        self.assertIn('docs', categorized)    # Maps to 'Documentation' section
        self.assertIn('test', categorized)    # Maps to 'Tests' section

    def test_generate_markdown_special_characters(self):
        """Test markdown generation with special characters."""
        commits = [
            GitCommit("abc123", "feat: add support for C++", "Author", "2023-01-01"),
            GitCommit("def456", "fix: handle \"quotes\" and 'apostrophes'", "Author", "2023-01-01")
        ]
        
        generator = ReleaseNotesGenerator()
        markdown = generator.generate_markdown("v1.0.0", "v1.1.0", commits)
        
        self.assertIn("C++", markdown)
        self.assertIn("quotes", markdown)
        self.assertIn("apostrophes", markdown)

    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    @patch.object(ReleaseNotesGenerator, 'get_latest_tags')
    def test_generate_release_notes_empty_tags_list(self, mock_get_tags, mock_is_git_repo):
        """Test handling of empty tags list."""
        mock_is_git_repo.return_value = True
        mock_get_tags.return_value = []
        
        generator = ReleaseNotesGenerator()
        
        with self.assertRaises(Exception) as context:
            generator.generate_release_notes()
        
        self.assertIn("No tags found", str(context.exception))

    @patch.object(ReleaseNotesGenerator, 'is_git_repo')
    @patch.object(ReleaseNotesGenerator, 'get_latest_tags')
    def test_generate_release_notes_single_tag(self, mock_get_tags, mock_is_git_repo):
        """Test handling of single tag in repository."""
        mock_is_git_repo.return_value = True
        mock_get_tags.return_value = ["v1.0.0"]
        
        generator = ReleaseNotesGenerator()
        
        with self.assertRaises(Exception) as context:
            generator.generate_release_notes()
        
        self.assertIn("Need at least 2 tags", str(context.exception))


class TestIntegration(unittest.TestCase):
    """Integration tests for the release notes generator."""

    def test_commit_parsing_integration(self):
        """Test the full commit parsing workflow."""
        commit_msg = "feat(user-api): implement user registration endpoint"
        commit = GitCommit("abc12345", commit_msg, "Test Author", "2023-01-01")
        
        # Verify parsing worked correctly
        self.assertEqual(commit.type, "feat")
        self.assertEqual(commit.scope, "user-api")
        self.assertEqual(commit.description, "implement user registration endpoint")
        
        # Verify it gets categorized properly
        generator = ReleaseNotesGenerator()
        categorized = generator.categorize_commits([commit])
        
        self.assertIn('feat', categorized)
        self.assertEqual(len(categorized['feat']), 1)
        self.assertEqual(categorized['feat'][0], commit)

    def test_full_workflow_simulation(self):
        """Test a full workflow simulation."""
        commits = [
            GitCommit("abc123", "feat(auth): add login", "Author1", "2023-01-01"),
            GitCommit("def456", "fix(api): resolve issue", "Author2", "2023-01-02"),
            GitCommit("ghi789", "chore: update deps", "Author1", "2023-01-03")
        ]
        
        generator = ReleaseNotesGenerator()
        
        # Test categorization
        categorized = generator.categorize_commits(commits)
        self.assertEqual(len(categorized), 3)  # feat, fix, chore
        
        # Test markdown generation
        markdown = generator.generate_markdown("v1.0.0", "v1.1.0", commits)
        self.assertIn("## Features", markdown)
        self.assertIn("## Bug Fixes", markdown)
        self.assertIn("## Chores", markdown)
        self.assertIn("add login **(auth)**", markdown)
        self.assertIn("resolve issue **(api)**", markdown)


if __name__ == '__main__':
    unittest.main()