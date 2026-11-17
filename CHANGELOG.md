# Changelog

## 1.0.0 - 2026-11-17 (Phase 9: QA and release)
- Damaged database file: the app now shows a clear message with the file name and what to do, and leaves the file as it was.
  Before, it only wrote the crash log. The file is checked (`PRAGMA quick_check`) before anything is written.
- New tests for data safety: process killed during a save (from inside and from outside), garbage, wrecked and truncated files.
- QA tools: `app\web\dev\qa.py` (all screens, 3 themes, 2 sizes, overflow check), `app\tools\qa_source_compare.py`
  (design CSS and text against the app), load tests for Python and the browser.
- Reports: `docs\qa-report.md`, `docs\requirements-check.md`.
- Load test (1,000 tasks, 200 notes, 50 books, 100 images): no slow action found, no change needed.
- README: damaged-file steps and release checks.

## Before 1.0.0 (Phases 0-8)
Spike, design system and shell, tasks, diary, archive and search, markdown and images, Python backend (SQLite),
desktop polish (single instance, backup, crash log), portable build.
