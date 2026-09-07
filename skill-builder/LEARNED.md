# skill-builder - Learned

<!-- Keep under 50 lines. Consolidate before adding. -->

## Description Writing

- (2026-02-13) Description is the PRIMARY trigger mechanism. Claude reads all descriptions to decide which skill to fire. "When to use" info in the body is useless if the description doesn't trigger first.
- (2026-02-13) Good description pattern: [What] + [How/via what] + [Specific actions] + [Trigger keywords]. Front-load the trigger words.

## Structure

- (2026-02-13) `references/` loads into context (costs tokens). `scripts/` and `assets/` don't. Large templates and data should go in assets/, not references/.
- (2026-02-13) Production skills stay well under 500 lines (100-300 lines). 300 is a good soft target.

## Self-Learning

- (2026-02-13) 50-line cap with dated entries and consolidation rules works well. Real skills stay at 7-18 lines naturally.

## Anti-Skip Patterns

- (2026-02-13) Variable carrying (later steps depend on earlier outputs) is the most reliable enforcement — natural dependency, not just warnings.
- (2026-02-13) Checkpoint gates between phases catch skipped steps before they compound.

## Validation

- (2026-02-13) Validator should check for LEARNED.md and self-learning section in SKILL.md. Missing these is the most common gap.
- (2026-02-13) Anthropic allows only these frontmatter keys: name, description, license, allowed-tools, metadata, compatibility.
