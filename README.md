# Automated Release Notes Generator

This Python script generates automatic release notes from Git commit history between two tags.

## Main Features

- Integration with Git CLI
- Retrieval of data from Git logs between the two latest tags
- Grouping of commit messages based on prefixes (such as feat:, fix:, chore:, etc.)
- Creation of Markdown file ready for publication
- Flexible configuration options

## Supported Commit Categories

- `feat` / `feature` → Features
- `fix` / `bugfix` → Bug Fixes
- `perf` / `performance` → Performance Improvements
- `refactor` → Code Refactoring
- `style` → Styling
- `chore` → Chores
- `docs` / `doc` → Documentation
- `test` / `testing` → Tests
- `build` → Build System
- `ci` → Continuous Integration
- `revert` → Reverts
- Others → Other Changes

## Usage

### Installation

No special installation required, just ensure Python 3.6+ and Git are installed on your system.

### Basic Usage

```bash
python release_notes_generator.py
```

This command will:
- Detect the two latest tags in the current repository
- Retrieve commits between these two tags
- Create a `RELEASE_NOTES.md` file in the current directory

### Command Options

```bash
-h, --help              Show help
-s TAG, --start-tag TAG  Starting tag (default: second most recent tag)
-e TAG, --end-tag TAG    Ending tag (default: most recent tag)
-o FILE, --output FILE   Output file name (default: RELEASE_NOTES.md)
-r PATH, --repo-path PATH Path to Git repository (default: current directory)
--title TITLE           Custom title for the release
-v, --verbose           Enable detailed output
```

### Usage Examples

```bash
# Use the two latest tags
python release_notes_generator.py

# Specify tags explicitly
python release_notes_generator.py -s v1.0.0 -e v1.1.0

# Save to custom filename
python release_notes_generator.py -o changelog.md

# Use different repository
python release_notes_generator.py -r /path/to/repo

# Use custom title
python release_notes_generator.py --title "Important Release"

# Enable verbose mode
python release_notes_generator.py -v
```

## Output Structure

The generated Markdown file includes:

- Release title
- Release date
- Tag range
- Summary statistics (number of commits and contributors)
- Categorized commit list
- List of all commits

## Testing

To run the unit tests for the release notes generator:

```bash
# Using unittest module (built into Python)
python -m unittest test_release_notes_generator.py

# Or to run with verbose output
python -m unittest test_release_notes_generator.py -v

# To run all tests in the project
python -m unittest discover -s . -p "test_*.py"
```

The test suite includes comprehensive tests for:
- GitCommit class functionality
- ReleaseNotesGenerator class methods
- Edge cases and error conditions
- Integration scenarios

## Contributing

Please create a pull request if you want to add features or fix bugs.