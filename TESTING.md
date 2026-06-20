# Pantella-WoW Testing

This project uses `pytest` for the Python backend and `luacheck` for the Lua addon frontend.

## Python Unit Tests

The Python tests use aggressive mocking so they can run headlessly on any operating system without requiring World of Warcraft, Windows APIs (`win32gui`), or a full Pantella installation.

### Running the tests

1. Install testing dependencies:
   ```bash
   pip install pytest pytest-mock
   ```

2. Run the test suite:
   ```bash
   pytest -v tests/
   ```

## Lua Linting

We use `luacheck` to analyze `MantellaWoW.lua` for syntax errors, accidental global leaks, and undefined variables. The `.luacheckrc` file contains a whitelist of standard WoW APIs (e.g., `UnitHealth`, `IsMounted`).

### Running the linter

1. Install `luarocks` and `luacheck`
2. Run the linter:
   ```bash
   luacheck MantellaWoW/
   ```

## Continuous Integration

Every push and pull request triggers the `.github/workflows/ci.yml` pipeline which runs the full test suite automatically on GitHub Actions runners.

## Pre-Commit and Pre-Push Hooks

This project uses the `pre-commit` framework to enforce quality locally before you push to GitHub.

- **Pre-commit**: Runs `luacheck` automatically every time you commit. If there's a syntax error in your Lua, the commit will be blocked.
- **Pre-push**: Runs the `pytest` suite locally before pushing to the remote repository.

### Setting up the hooks locally
1. Install the `pre-commit` framework (if you haven't already):
   ```bash
   pip install pre-commit
   ```
2. Install the hooks into your local Git repository:
   ```bash
   pre-commit install -t pre-commit -t pre-push
   ```
