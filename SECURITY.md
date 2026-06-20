# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please DO NOT create a public issue. Instead, send an email or use GitHub's private vulnerability reporting feature if enabled on the repository.

## Automated Security Scanning

This repository is protected by:
- **CodeQL**: Automated semantic code analysis runs on every push and pull request to detect vulnerabilities like injection flaws or unsafe API usage.
- **Dependabot**: Automatically monitors and proposes updates for outdated or vulnerable dependencies in `requirements.txt` and GitHub Actions.

## Recommended Branch Protection Rules

To maintain the integrity of the project, it is highly recommended to configure the following Branch Protection Rules for the `main` (or `master`) branch via GitHub Repository Settings -> Branches -> Add branch protection rule:

1. **Require a pull request before merging**: Prevents direct pushes to the main branch.
2. **Require status checks to pass before merging**:
   - `Python Tests` (Pytest)
   - `Lua Lint` (Luacheck)
   - `Analyze (python)` (CodeQL)
3. **Require review from Code Owners**: Ensures at least one other developer reviews architectural changes.
4. **Do not allow bypassing the above settings**: Enforces the rules strictly.
