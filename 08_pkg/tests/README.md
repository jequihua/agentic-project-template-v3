# Package Tests

Status: no separate package test suite is required by default.

Reusable template behavior is covered by the top-level `tests/` suite
(`python -m unittest discover -s tests`), including the scaffold safeguards, the
profile fixtures and `--profile` checker, the deterministic navigation-view
regeneration tests, the mixed legacy/profile authoring tests, and the architect
operating-card tests.

A project may add its own package test module here when it packages reusable code;
follow `08_pkg/testing_strategy.md`. This directory must not contain invented test
names or pretend future behavior exists.
