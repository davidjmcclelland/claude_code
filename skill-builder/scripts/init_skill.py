#!/usr/bin/env python3
"""Scaffold a new Claude Code skill with the standard directory structure."""

import argparse
import os
import sys
from pathlib import Path

SKILL_MD_TEMPLATE = """---
name: {name}
description: |
  TODO: [What it does] + [How/via what] + [Specific actions] + [Trigger keywords].
  Front-load trigger conditions. Max 1024 chars. No angle brackets.
allowed-tools: Bash Read Write Edit
---

# {title}

Read [LEARNED.md](LEARNED.md) before using this skill.

## Quick Start

TODO: Minimal working example - simplest successful use.

## Core Operations

TODO: Brief list of what this skill does. Link to references/ if >100 lines.

## Workflows

TODO: Checklists for multi-step tasks. Conditional routing for different paths.

## Error Reference

| Issue | Solution |
|-------|----------|
| TODO | TODO |

## Self-Learning

Read [LEARNED.md](LEARNED.md) before using this skill.

**Update LEARNED.md when you discover:**
- TODO: List skill-specific things to record

**Consolidation (keep under 50 lines):**
Before adding a new entry, check file length. If over 50 lines:
1. Merge duplicate/overlapping entries into single proven patterns
2. Remove entries older than 3 months that haven't been reinforced
3. Drop one-off observations that never recurred
4. Keep only entries that would change behavior - if obvious, cut it
"""

LEARNED_MD_TEMPLATE = """# {name} - Learned

<!-- Keep under 50 lines. Consolidate before adding. -->

## General

"""

def create_skill(name: str, base_path: str):
    skill_dir = Path(base_path) / name

    if skill_dir.exists():
        print(f"Error: {skill_dir} already exists")
        sys.exit(1)

    title = name.replace("-", " ").title()

    # Create directory structure
    dirs = [
        skill_dir,
        skill_dir / "scripts",
        skill_dir / "references",
        skill_dir / "setup",
        skill_dir / "assets",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Write SKILL.md
    (skill_dir / "SKILL.md").write_text(
        SKILL_MD_TEMPLATE.format(name=name, title=title)
    )

    # Write LEARNED.md
    (skill_dir / "LEARNED.md").write_text(
        LEARNED_MD_TEMPLATE.format(name=name)
    )

    # Write placeholder files
    (skill_dir / "setup" / "README.md").write_text(
        f"# {title} Setup\n\nTODO: Document setup steps, credentials, dependencies.\n"
    )

    print(f"Created skill: {skill_dir}")
    print(f"  SKILL.md        - Main instructions (edit this first)")
    print(f"  LEARNED.md      - Self-learning log")
    print(f"  scripts/         - Executable code (not loaded into context)")
    print(f"  references/      - Detailed docs (loaded into context, costs tokens)")
    print(f"  setup/           - Setup instructions and credential templates")
    print(f"  assets/          - Output templates and files (not loaded into context)")
    print()
    print("Next steps:")
    print("  1. Write the description field FIRST (it's the trigger mechanism)")
    print("  2. Fill in SKILL.md body")
    print("  3. Add scripts to scripts/")
    print(f"  4. Validate: python3 validate_skill.py {skill_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new Claude Code skill")
    parser.add_argument("name", help="Skill name (kebab-case)")
    parser.add_argument(
        "--path",
        default=os.path.expanduser("~/.claude/skills"),
        help="Base path for skills (default: ~/.claude/skills)",
    )
    args = parser.parse_args()
    create_skill(args.name, args.path)
