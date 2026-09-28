#!/usr/bin/env python3
"""Validate a Claude Code skill for structure, frontmatter, and best practices."""

import re
import sys
from pathlib import Path

ALLOWED_FRONTMATTER_KEYS = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility"
}

errors = []
warnings = []


def error(msg):
    errors.append(f"  ERROR: {msg}")


def warn(msg):
    warnings.append(f"  WARN:  {msg}")


def validate_frontmatter(skill_md_text: str, skill_name: str):
    """Validate YAML frontmatter in SKILL.md."""
    if not skill_md_text.startswith("---"):
        error("SKILL.md missing YAML frontmatter (must start with ---)")
        return

    parts = skill_md_text.split("---", 2)
    if len(parts) < 3:
        error("SKILL.md frontmatter not properly closed (need opening and closing ---)")
        return

    frontmatter = parts[1].strip()
    body = parts[2]

    # Check required keys
    has_name = False
    has_description = False

    for line in frontmatter.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" in line:
            key = line.split(":")[0].strip()
            if key not in ALLOWED_FRONTMATTER_KEYS and not line.startswith(" "):
                warn(f"Unknown frontmatter key: '{key}' (allowed: {', '.join(sorted(ALLOWED_FRONTMATTER_KEYS))})")

            if key == "name":
                has_name = True
                name_val = line.split(":", 1)[1].strip()
                if name_val and name_val != skill_name:
                    warn(f"Frontmatter name '{name_val}' doesn't match directory name '{skill_name}'")
                if name_val and len(name_val) > 64:
                    error(f"Name too long ({len(name_val)} chars, max 64)")

            if key == "description":
                has_description = True
                # Check if description is inline or multiline
                desc_val = line.split(":", 1)[1].strip()
                if desc_val and not desc_val.startswith("|"):
                    if len(desc_val) > 1024:
                        error(f"Description too long ({len(desc_val)} chars, max 1024)")

    if not has_name:
        error("Missing 'name' in frontmatter")
    if not has_description:
        error("Missing 'description' in frontmatter")

    # Check description quality
    desc_text = ""
    in_desc = False
    for line in frontmatter.split("\n"):
        if line.strip().startswith("description:"):
            in_desc = True
            desc_text = line.split(":", 1)[1].strip()
            if desc_text.startswith("|"):
                desc_text = ""
            continue
        if in_desc:
            if line.startswith("  ") or line.startswith("\t"):
                desc_text += " " + line.strip()
            else:
                in_desc = False

    if desc_text:
        if len(desc_text) < 50:
            warn("Description seems short — include trigger keywords, actions, and when-to-use")
        if desc_text.lower().startswith("you can"):
            warn("Description should be third person ('Processes...') not second person ('You can...')")

    # Check body length
    body_lines = body.strip().split("\n")
    if len(body_lines) > 500:
        warn(f"SKILL.md body is {len(body_lines)} lines (target: <500, start splitting to references/)")
    elif len(body_lines) > 300:
        warn(f"SKILL.md body is {len(body_lines)} lines (approaching limit, consider splitting)")


def validate_structure(skill_dir: Path):
    """Validate directory structure and required files."""
    # SKILL.md required
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        error("Missing SKILL.md (required)")
        return ""

    text = skill_md.read_text()

    # LEARNED.md required
    learned_md = skill_dir / "LEARNED.md"
    if not learned_md.exists():
        error("Missing LEARNED.md (required — every skill must self-learn)")
    else:
        learned_text = learned_md.read_text()
        learned_lines = [l for l in learned_text.strip().split("\n") if l.strip()]
        if len(learned_lines) > 50:
            warn(f"LEARNED.md is {len(learned_lines)} lines (cap: 50 — time to consolidate)")

    # Check for self-learning section in SKILL.md
    if "LEARNED.md" not in text and "self-learn" not in text.lower():
        warn("SKILL.md doesn't reference LEARNED.md or self-learning")

    # Check for scripts inside SKILL.md (should be in scripts/)
    if "```python" in text and "scripts/" not in text:
        warn("Python code in SKILL.md body — consider moving to scripts/")
    if "```bash" in text:
        bash_blocks = text.count("```bash")
        if bash_blocks > 3:
            warn(f"{bash_blocks} bash blocks in SKILL.md — consider moving complex scripts to scripts/")

    return text


def validate_skill(skill_path: str):
    skill_dir = Path(skill_path).resolve()

    if not skill_dir.is_dir():
        print(f"Error: {skill_dir} is not a directory")
        sys.exit(1)

    skill_name = skill_dir.name
    print(f"Validating: {skill_name}")
    print(f"Path: {skill_dir}")
    print()

    text = validate_structure(skill_dir)
    if text:
        validate_frontmatter(text, skill_name)

    # Print results
    if errors:
        print("ERRORS (must fix):")
        for e in errors:
            print(f"  \033[31m{e}\033[0m")
        print()

    if warnings:
        print("WARNINGS (should fix):")
        for w in warnings:
            print(f"  \033[33m{w}\033[0m")
        print()

    if not errors and not warnings:
        print("  \033[32m✓ All checks passed\033[0m")
        print()

    if errors:
        print(f"Result: {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"Result: 0 errors, {len(warnings)} warning(s)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 validate_skill.py <path-to-skill-directory>")
        sys.exit(1)
    validate_skill(sys.argv[1])
