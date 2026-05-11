"""smartcopilot check-resolvable — skills-tree validator (CLI-03).

Phase 1d: empty tree passes cleanly. Phase 3 will populate this with the real
RESOLVER.md MECE/DRY/orphan checks; Phase 1d only enforces the empty-pass invariant.
"""

from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_SKILLS_DIR = "/vaults/shared/.skills"


def add_subparser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "check-resolvable", help="validate skills tree reachability (CLI-03)"
    )
    p.add_argument("--skills-dir", default=DEFAULT_SKILLS_DIR)
    p.set_defaults(func=_handle_check_resolvable)


async def _handle_check_resolvable(args: argparse.Namespace) -> int:
    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists() or not skills_dir.is_dir():
        print(f"no skills directory at {skills_dir}")
        print("check: OK")
        return 0
    # Phase 1d: an existing-but-empty directory also passes.
    if not any(skills_dir.iterdir()):
        print(f"empty skills directory at {skills_dir}")
        print("check: OK")
        return 0
    # Phase 3 will replace this branch with real validation. For Phase 1d, surface a TODO.
    print(f"skills directory at {skills_dir} — full validation arrives in Phase 3")
    print("check: OK")
    return 0
