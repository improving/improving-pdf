---
description: Cut a new versioned release of improving-pdf-tool (bump version, tag, push, GitHub release)
---

# Release Workflow

This workflow cuts a new release of the `improving-pdf-tool` package. It bumps the version, commits, tags, pushes to GitHub, and creates a GitHub release.

## Prerequisites

Before starting, verify all of the following:

1. Confirm you are on the `main` branch:
// turbo
```
git branch --show-current
```
If not on `main`, stop and tell the user.

2. Confirm the working tree is clean:
// turbo
```
git status --porcelain
```
If there is output (uncommitted changes), stop and tell the user to commit or stash first.

3. Confirm `gh` CLI is available:
// turbo
```
gh --version
```
If not installed, stop and tell the user to install GitHub CLI (`gh`) and authenticate with `gh auth login`.

## Steps

4. Ask the user what type of version bump to perform: `major`, `minor`, or `patch`. If the user already specified the bump type when invoking this workflow, use that.

5. Read the current version from `src/improving_pdf_tool/__init__.py`. The version is stored as `__version__ = "X.Y.Z"`. Parse X, Y, Z as integers.

6. Compute the new version:
   - `patch`: increment Z (e.g., 1.2.3 → 1.2.4)
   - `minor`: increment Y, reset Z to 0 (e.g., 1.2.3 → 1.3.0)
   - `major`: increment X, reset Y and Z to 0 (e.g., 1.2.3 → 2.0.0)

7. Update the version in **both** files:
   - `src/improving_pdf_tool/__init__.py`: update `__version__ = "X.Y.Z"`
   - `pyproject.toml`: update `version = "X.Y.Z"`

8. Stage the changes:
```
git add -A
```

9. Commit with the release message:
```
git commit -m "release: vX.Y.Z"
```
Replace X.Y.Z with the actual new version.

10. Create an annotated git tag:
```
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

11. Push the commit and tag to origin:
```
git push origin main --tags
```

12. Create a GitHub release with auto-generated notes:
```
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes
```

13. Print a summary for the user:
```
Release vX.Y.Z complete!

Install this version:
  pip install git+https://github.com/improving/improving-pdf.git@vX.Y.Z

Install latest:
  pip install git+https://github.com/improving/improving-pdf.git
```

14. Check if `skill.md` exists and contains a pinned version reference (e.g., `@v`). If so, remind the user to update the pinned version in `skill.md` to the new version.
