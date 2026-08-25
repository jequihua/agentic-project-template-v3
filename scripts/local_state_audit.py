"""Read-only local-state footprint audit for a project made from this template.

Makes hidden local disk/worktree state visible without forcing any policy: file
and directory counts, approximate bytes, the largest top-level directories, and
flags for nested `.git` repositories, virtual environments, caches, and large
files. Useful before milestone closure, a handoff, or deleting a local clone.

This tool is strictly READ-ONLY: it never deletes, moves, or modifies anything
(including `.gitignore`). It exits 0 even when a project is large — being large is
not a failure.

Usage::

    python scripts/local_state_audit.py --root .

Stdlib-only. See `scripts/README.md` and
`docs/template_framework/security_and_local_state.md`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _local_state_common as core  # noqa: E402

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT,
                        help="Project root to audit (default: the template root).")
    parser.add_argument("--large-file-mb", type=float, default=core.LARGE_FILE_BYTES / (1024 * 1024),
                        help="Flag individual files at or above this size in MB.")
    parser.add_argument("--limit-bytes", type=int, default=None,
                        help="Pre-launch check: list undeclared files at or above this size and exit 1 "
                             "when any exist (the drive's oracle content bound is 16777216).")
    parser.add_argument("--exclusions", type=Path, default=None,
                        help="The drive's oracle exclusion manifest (strict JSON: contract_version, "
                             "exact_paths, top_level_prefixes); the same file the drive reads.")
    parser.add_argument("--top", type=int, default=10,
                        help="How many largest top-level directories / large files to show.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 2

    fp = core.audit_footprint(root, large_file_bytes=int(args.large_file_mb * 1024 * 1024))

    print(f"Local-state audit (read-only): {root}")
    print(f"  files: {fp.total_files}   directories: {fp.total_dirs}   "
          f"size: {core.human_bytes(fp.total_bytes)}")

    if fp.top_level:
        print("\nLargest top-level directories:")
        for name, size, files in fp.top_level[: args.top]:
            print(f"  {core.human_bytes(size):>10}  {files:>7} files  {name}/")

    if fp.venvs:
        print(f"\nVirtual environments ({len(fp.venvs)}) - not deleted by cleanup; "
              "remove manually when idle:")
        for rel in fp.venvs:
            print(f"  {rel}/")

    if fp.nested_git:
        print(f"\nNested .git repositories ({len(fp.nested_git)}) - review; the template "
              "discourages nested repos:")
        for rel in fp.nested_git:
            print(f"  {rel}/")

    if fp.caches:
        print(f"\nRebuildable caches ({len(fp.caches)}) - clean with "
              "`python scripts/local_cleanup.py --apply`:")
        for rel in fp.caches[: args.top]:
            print(f"  {rel}/")
        if len(fp.caches) > args.top:
            print(f"  ... and {len(fp.caches) - args.top} more")

    if fp.large_files:
        print(f"\nLarge files (>= {args.large_file_mb:g} MB):")
        for rel, size in fp.large_files[: args.top]:
            print(f"  {core.human_bytes(size):>10}  {rel}")

    print("\nRead-only: nothing was changed.")
    if args.limit_bytes is not None:
        exact, prefixes = set(), ()
        if args.exclusions is not None:
            data = json.loads(args.exclusions.read_text(encoding="utf-8"))
            exact = set(data.get("exact_paths", []))
            prefixes = tuple(data.get("top_level_prefixes", []))
        bound = core.audit_footprint(root, large_file_bytes=args.limit_bytes)
        governed = (".git", ".frutlups_drive", "local_state")
        offenders = [
            (rel, size) for rel, size in bound.large_files
            if rel not in exact
            and not rel.startswith(prefixes)
            and rel.split("/")[0] not in governed
        ]
        print(f"\nPre-launch size check (bound {args.limit_bytes} bytes; "
              f"{len(exact)} exact exclusions, {len(prefixes)} prefix exclusions):")
        if offenders:
            for rel, size in sorted(offenders):
                print(f"  ABOVE BOUND  {rel}  {size} bytes")
            print("Declare each in the exclusion manifest or move it under local_state/.")
            return 1
        print("  no undeclared file at or above the bound")
    return 0


if __name__ == "__main__":
    sys.exit(main())
