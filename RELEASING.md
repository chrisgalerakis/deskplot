# Releasing deskplot

Maintainer checklist for shipping a new version.

## 1. Pre-flight

```bash
ruff check src tests examples && pytest      # all green
rm -rf dist && python -m build               # wheel + sdist
twine check dist/*                           # both PASSED
```

## 2. Version and changelog

- Bump `__version__` in `src/deskplot/__init__.py` (pyproject reads it
  dynamically). Semver: MAJOR = breaking API, MINOR = new features,
  PATCH = fixes/docs.
- Move `CHANGELOG.md` entries from `[Unreleased]` into a new
  `[X.Y.Z] - YYYY-MM-DD` section.

## 3. Tag and publish

```bash
git commit -am "Release vX.Y.Z"
git tag vX.Y.Z
git push && git push --tags
gh release create vX.Y.Z --title "deskplot vX.Y.Z" --notes-file - <<'EOF'
(paste the CHANGELOG section here)
EOF
```

## 4. PyPI

```bash
rm -rf dist && python -m build
twine upload dist/*
```

Authentication: a PyPI API token (username `__token__`), either entered
at the prompt or stored in `~/.pypirc`. Verify afterwards with a fresh
venv: `pip install deskplot`, then run an example.
