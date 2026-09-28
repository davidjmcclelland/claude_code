# Skill Builder — Claude Code

A skill that builds skills. Drop this folder into your Claude Code project and Claude will use it to build production-quality skills for any workflow.

## Install

Copy this `skill-builder/` folder to:
- `.claude/skills/skill-builder/` in any project (project-specific)
- `~/.claude/skills/skill-builder/` (global — available in all projects)

## Use

Tell Claude: "I want to build a skill for [your workflow]"

Or scaffold a new skill manually:
  python3 scripts/init_skill.py my-skill --path ~/.claude/skills

Validate a skill:
  python3 scripts/validate_skill.py ~/.claude/skills/my-skill

## What's Inside

- SKILL.md — The meta-skill (what Claude reads)
- LEARNED.md — Self-learning log (fills up as you build skills)
- references/example-skill.md — Bulletproof skill template
- scripts/init_skill.py — Scaffolds new skill directories
- scripts/validate_skill.py — Validates skill structure and frontmatter

Built by Dan Cumberland Labs — dancumberlandlabs.com
