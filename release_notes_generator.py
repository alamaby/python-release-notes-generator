#!/usr/bin/env python3
"""
Automated Release Notes Generator

This script generates release notes from Git commit history between two tags.
It categorizes commits based on conventional commit prefixes (feat, fix, chore, etc.)
and creates a well-formatted Markdown file suitable for publication.
"""

import subprocess
import sys
import argparse
import re
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class GitCommit:
    """Represents a single Git commit with parsed information."""
    
    def __init__(self, hash: str, subject: str, author: str, date: str):
        self.hash = hash
        self.subject = subject
        self.author = author
        self.date = date
        self.type, self.scope, self.description = self.parse_commit_message(subject)
    
    def parse_commit_message(self, message: str) -> Tuple[str, str, str]:
        """
        Parse conventional commit message format: type(scope): description
        
        Args:
            message: Commit message to parse
            
        Returns:
            Tuple of (type, scope, description)
        """
        # Regex pattern to match conventional commit format
        pattern = r'^(\w+)(?:\(([^)]+)\))?:\s*(.*)'
        match = re.match(pattern, message)
        
        if match:
            commit_type = match.group(1).lower()
            scope = match.group(2) if match.group(2) else ""
            description = match.group(3)
        else:
            # If not in conventional format, treat the whole message as description
            # and assign to 'other' type
            commit_type = "other"
            scope = ""
            description = message
        
        return commit_type, scope, description


class ReleaseNotesGenerator:
    """Main class for generating release notes from Git commits."""
    
    # Define commit types and their display names
    COMMIT_TYPES = {
        'feat': 'Features',
        'feature': 'Features',
        'fix': 'Bug Fixes',
        'bugfix': 'Bug Fixes',
        'perf': 'Performance Improvements',
        'performance': 'Performance Improvements',
        'refactor': 'Code Refactoring',
        'style': 'Styling',
        'chore': 'Chores',
        'docs': 'Documentation',
        'doc': 'Documentation',
        'test': 'Tests',
        'testing': 'Tests',
        'build': 'Build System',
        'ci': 'Continuous Integration',
        'revert': 'Reverts',
        'other': 'Other Changes'
    }
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
    def run_git_command(self, command: List[str], allow_failure: bool = False) -> Optional[str]:
        """
        Execute a git command and return its output.
        
        Args:
            command: List of command arguments
            allow_failure: If True, return None on failure instead of raising exception
            
        Returns:
            Command output as string, or None if command fails and allow_failure is True
            
        Raises:
            subprocess.CalledProcessError: If git command fails and allow_failure is False
        """
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if allow_failure:
                return None
            else:
                print(f"Error running git command: {' '.join(command)}")
                print(f"Error message: {e.stderr}")
                raise
    
    def is_git_repo(self) -> bool:
        """Check if the current directory is a Git repository."""
        return self.run_git_command(["rev-parse", "--git-dir"], allow_failure=True) is not None
    
    def get_latest_tags(self) -> List[str]:
        """
        Get the list of all tags sorted by creation date (most recent first).
        
        Returns:
            List of tag names sorted by date (newest first)
        """
        if not self.is_git_repo():
            raise Exception(f"'{self.repo_path}' is not a Git repository")
        
        # Get tags with their dates
        tags_with_date = []
        try:
            # Get all tags with their dates
            raw_tags = self.run_git_command(["for-each-ref", "--format='%(refname:short)|%(creatordate:iso)'", "refs/tags"])
            
            if raw_tags:
                for line in raw_tags.split('\n'):
                    if '|' in line:
                        tag, date_str = line.strip("'").split('|', 1)
                        # Convert date string to datetime object for sorting
                        try:
                            date_obj = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                            tags_with_date.append((tag, date_obj))
                        except ValueError:
                            # If date parsing fails, use the tag name as fallback
                            tags_with_date.append((tag, datetime.min))
                
                # Sort by date (descending - newest first)
                tags_with_date.sort(key=lambda x: x[1], reverse=True)
                return [tag for tag, _ in tags_with_date]
        except Exception:
            pass  # Fall back to simple tag listing
        
        # Fallback: get tags without date info
        try:
            raw_tags = self.run_git_command(["tag", "-l"])
            return raw_tags.split('\n') if raw_tags else []
        except:
            return []
    
    def get_commits_between_tags(self, start_tag: str, end_tag: str) -> List[GitCommit]:
        """
        Get commits between two tags.
        
        Args:
            start_tag: Starting tag (older)
            end_tag: Ending tag (newer)
            
        Returns:
            List of GitCommit objects
        """
        # Format: git log --oneline --pretty=format:"%H|%an|%ad|%s" START_TAG..END_TAG
        cmd = [
            "log",
            "--oneline",
            "--pretty=format:%H|%an|%ad|%s",
            f"{start_tag}..{end_tag}"
        ]
        
        raw_commits = self.run_git_command(cmd)
        
        commits = []
        if raw_commits:
            for line in raw_commits.split('\n'):
                if line.strip():
                    parts = line.split('|', 3)  # Split into max 4 parts
                    if len(parts) >= 4:
                        commit_hash, author, date, subject = parts
                        commits.append(GitCommit(commit_hash[:8], subject, author, date))
        
        return commits
    
    def categorize_commits(self, commits: List[GitCommit]) -> Dict[str, List[GitCommit]]:
        """
        Categorize commits by their type.
        
        Args:
            commits: List of GitCommit objects
            
        Returns:
            Dictionary mapping commit type to list of commits
        """
        categorized = {}
        
        for commit_type_key in self.COMMIT_TYPES.keys():
            categorized[commit_type_key] = []
        
        # Add commits to appropriate categories
        for commit in commits:
            commit_type = commit.type
            if commit_type in categorized:
                categorized[commit_type].append(commit)
            else:
                # Put unrecognized types in 'other'
                categorized['other'].append(commit)
        
        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}
    
    def generate_markdown(self, start_tag: str, end_tag: str, commits: List[GitCommit], 
                         version_title: str = None) -> str:
        """
        Generate Markdown-formatted release notes.
        
        Args:
            start_tag: Starting tag
            end_tag: Ending tag
            commits: List of commits to include
            version_title: Custom title for the release
            
        Returns:
            Markdown-formatted string
        """
        if not version_title:
            version_title = f"Release {end_tag}"
        
        # Get current date for the release notes
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        markdown = f"# {version_title}\n\n"
        markdown += f"**Release Date:** {current_date}\n\n"
        markdown += f"**Tags:** `{start_tag}` ... `{end_tag}`\n\n"
        
        if not commits:
            markdown += "No significant changes.\n\n"
            return markdown
        
        categorized = self.categorize_commits(commits)
        
        # Add summary statistics
        total_commits = len(commits)
        total_authors = len(set(c.author for c in commits))
        
        markdown += f"**Summary:** {total_commits} commits by {total_authors} authors\n\n"
        
        # Add categorized commits
        for commit_type, commit_list in categorized.items():
            display_name = self.COMMIT_TYPES.get(commit_type, commit_type.title())
            markdown += f"## {display_name}\n\n"
            
            for commit in commit_list:
                scope_part = f" **({commit.scope})**" if commit.scope else ""
                markdown += f"- {commit.description}{scope_part} ([`{commit.hash}`](https://github.com/unknown/unknown/commit/{commit.hash}))\n"
            
            markdown += "\n"
        
        # Add all commits section (optional, can be disabled)
        markdown += "## All Commits\n\n"
        for commit in commits:
            markdown += f"- [`{commit.subject}`]({commit.hash}) - {commit.author}\n"
        
        return markdown
    
    def generate_release_notes(self, start_tag: str = None, end_tag: str = None, 
                              output_file: str = "RELEASE_NOTES.md", 
                              version_title: str = None) -> str:
        """
        Generate release notes between two tags.
        
        Args:
            start_tag: Starting tag (if None, uses previous tag)
            end_tag: Ending tag (if None, uses latest tag)
            output_file: Output file path
            version_title: Custom title for the release
            
        Returns:
            Generated markdown content
        """
        print("Checking if this is a Git repository...")
        if not self.is_git_repo():
            raise Exception(f"'{self.repo_path}' is not a Git repository")
        
        print("Getting available tags...")
        all_tags = self.get_latest_tags()
        
        if not all_tags:
            raise Exception("No tags found in the repository")
        
        if len(all_tags) < 2:
            raise Exception("Need at least 2 tags to generate release notes between them")
        
        # Determine which tags to use
        if not end_tag:
            end_tag = all_tags[0]  # Most recent tag
        if not start_tag:
            # Find the previous tag (skip any malformed tags)
            for tag in all_tags[1:]:
                if tag != end_tag:
                    start_tag = tag
                    break
        
        # Ensure we have the right order: older tag first, newer tag second
        # Check which tag is older by looking at commit history
        try:
            # Check if start_tag is actually newer than end_tag
            # If so, swap them
            result = self.run_git_command(["merge-base", start_tag, end_tag], allow_failure=True)
            if result:
                # Determine chronological order by checking which is ancestor of the other
                # If start_tag is an ancestor of end_tag, then the order is correct
                # If end_tag is an ancestor of start_tag, then we need to swap
                try:
                    self.run_git_command(["merge-base", "--is-ancestor", start_tag, end_tag])
                    # Order is correct: start_tag is older than end_tag
                except subprocess.CalledProcessError:
                    # start_tag is NOT an ancestor of end_tag, so swap them
                    start_tag, end_tag = end_tag, start_tag
        except:
            # If merge-base fails, just swap them assuming the most recent tag is the end
            # This is a fallback - in most cases the original order should be fine
            pass
        
        print(f"Generating release notes from {start_tag} to {end_tag}...")
        
        # Get commits between tags
        commits = self.get_commits_between_tags(start_tag, end_tag)
        
        print(f"Found {len(commits)} commits")
        
        # Generate markdown
        markdown_content = self.generate_markdown(
            start_tag, 
            end_tag, 
            commits, 
            version_title
        )
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Release notes saved to {output_file}")
        
        return markdown_content


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Automated Release Notes Generator from Git commits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Generate notes between latest two tags
  %(prog)s -s v1.0.0 -e v1.1.0       # Generate notes between specific tags
  %(prog)s -o changelog.md           # Save to custom filename
  %(prog)s -r /path/to/repo          # Use different repository
  %(prog)s --title "My Custom Release"  # Custom release title
        """
    )
    
    parser.add_argument('-s', '--start-tag', 
                       help='Starting tag (default: second most recent tag)')
    parser.add_argument('-e', '--end-tag', 
                       help='Ending tag (default: most recent tag)')
    parser.add_argument('-o', '--output', 
                       default='RELEASE_NOTES.md',
                       help='Output file name (default: RELEASE_NOTES.md)')
    parser.add_argument('-r', '--repo-path', 
                       default='.',
                       help='Path to Git repository (default: current directory)')
    parser.add_argument('--title',
                       help='Custom title for the release')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Repository path: {args.repo_path}")
        print(f"Output file: {args.output}")
        print(f"Start tag: {args.start_tag or 'auto'}")
        print(f"End tag: {args.end_tag or 'auto'}")
    
    try:
        generator = ReleaseNotesGenerator(args.repo_path)
        content = generator.generate_release_notes(
            start_tag=args.start_tag,
            end_tag=args.end_tag,
            output_file=args.output,
            version_title=args.title
        )
        
        print("\nRelease notes generated successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()