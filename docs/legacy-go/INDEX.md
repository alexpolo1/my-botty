# Legacy: Go Rewrite Design Notes

These docs are archived from an abandoned `~/git/botty-go` directory (May 2026).
That project was a planned ground-up Go rewrite of `johannes-do/botty` for
cross-platform (Linux + Windows) support. Only design docs existed — no `.go`
source was ever written.

The Python `my-botty` project (this repo) is the active path. These docs are
kept here as **reference material**, primarily for Milestone 2 (anti-detection /
stealth) of `~/.claude/plans/continue-the-make-up-sunny-honey.md`.

## Files

- **`ANTI_DETECTION.md`** — Multi-layer anti-detection framework. Covers
  server-side behavior analysis countermeasures (session scheduling, stochastic
  pathing, skill rotation variance) and more. Directly applicable as the design
  basis for the Python stealth layer.
- **`GO_REWRITE_README.md`** — Original README of the abandoned Go project.
  Context only — explains feature scope and what the rewrite was aiming for.
