---
name: skill-builder
description: |
  Create, restructure, and validate Claude Code skills following production-tested
  patterns. Handles directory structure, YAML frontmatter, progressive disclosure,
  self-learning with LEARNED.md, anti-skip enforcement, and script organization.
  Use when creating new skills, restructuring existing skills, reviewing skill quality,
  or asking about skill structure, patterns, or best practices.
allowed-tools: Bash Read Write Edit
---

# Skill Builder

Read [LEARNED.md](LEARNED.md) before building or reviewing any skill.

Create reusable, discoverable, **bulletproof** skills for Claude Code.

---

## Core Principles

### Context Window is Sacred

Skills share context with system prompt, conversation history, and the user's request. Only add what Claude doesn't already know. **For every line ask:** Does this justify its token cost?

### Progressive Disclosure

Skills load in three stages. Design for this.

| Stage | What loads | Budget | Contains |
|-------|-----------|--------|----------|
| Discovery | `name` + `description` | ~100 tokens | Trigger keywords, when to use |
| Activation | SKILL.md body | <5000 tokens | Instructions, workflows, quick start |
| Execution | references/, scripts/ | As needed | Detailed docs, executable code |

**Critical:** The `description` field is the trigger mechanism. All "when to use" info goes there, not the body.

### Self-Learning is Mandatory

Every skill MUST have `LEARNED.md` with consolidation rules. No exceptions.

---

## Why Skills Fail

| Failure Mode | Why It Happens | Prevention |
|--------------|----------------|------------|
| **Steps skipped** | No enforcement mechanism | Checkpoints + TodoWrite requirement |
| **Optional-feeling steps** | Weak language ("consider", "optionally") | REQUIRED markers + ⛔ warnings |
| **Middle steps forgotten** | Focus on start/end, lose middle | Phase structure + variable carrying |
| **Skill not activated** | Poor description field | Trigger words + symptoms in description |
| **Wrong behavior** | Ambiguous instructions | Examples of ❌ WRONG vs ✅ RIGHT |
| **No learning** | Missing LEARNED.md | Self-learning section + consolidation rules |

---

## The Bulletproof Skill Architecture

### Required Sections (In Order)

```
1. ⛔ CRITICAL ITEMS (commonly missed steps - at TOP)
2. STOP - READ THIS FIRST (mandatory checklist creation)
3. PHASES with CHECKPOINTS (grouped steps with gates)
4. Reference section (lookups, configuration)
5. Error handling table
```

### Why This Order Matters

- **Critical items first**: Forces attention to historically-skipped steps
- **Stop section**: Creates TodoWrite checklist before any execution
- **Phases with checkpoints**: Blocks progress until verification
- **Reference at end**: Keeps working sections uncluttered

---

## Section Templates

### 1. Critical Items Section

**Place at the VERY TOP, before any instructions.**

```markdown
## ⛔ CRITICAL ITEMS - CHECK EVERY ONE

These items have been missed before. **Verify each explicitly:**

| # | Item | Location | How to Verify |
|---|------|----------|---------------|
| 1 | **[Commonly missed thing]** | [Where] | [Specific check] |
| 2 | **[Another missed thing]** | [Where] | [Specific check] |

**If ANY item is missing at the end, the task has failed.**
```

### 2. Stop Section with TodoWrite Requirement

```markdown
## ⛔ STOP - READ THIS FIRST

**YOU MUST COMPLETE ALL [N] STEPS. NO EXCEPTIONS.**

Before doing ANYTHING else, create a TodoWrite checklist with ALL items:

```
1. [ ] [Step 1 description]
2. [ ] [Step 2 description]
...
```

**If you skip ANY step, you have failed this task.**

**Mark each step complete in TodoWrite BEFORE proceeding to the next.**
```

### 3. Phase Structure with Checkpoints

```markdown
## PHASE 1: [Phase Name]

### Step 1.1: [Step Name] [REQUIRED]

[Instructions]

**Mark Step 1.1 complete before proceeding.**

---

### Step 1.2: [Step Name] [REQUIRED - DO NOT SKIP]

**⚠️ THIS STEP IS COMMONLY SKIPPED. DO NOT SKIP IT.**

[Instructions]

**Mark Step 1.2 complete before proceeding.**

---

## ⏸️ CHECKPOINT: PHASE 1 COMPLETE

Before proceeding, verify you have ALL of these:

| Item | Value | ✓ |
|------|-------|---|
| `variable_1` | [expected] | |
| `variable_2` | [expected] | |

**If ANY item is missing, go back and complete that step.**
```

### 4. Commonly Skipped Steps Table

```markdown
## 🚫 COMMONLY SKIPPED STEPS - DO NOT SKIP THESE

| Step | What Gets Skipped | Why It Matters |
|------|-------------------|----------------|
| **Step N** | [Description] | [Consequence of skipping] |
| **Step M** | [Description] | [Consequence of skipping] |

**If you find yourself about to skip any of these, STOP.**
```

### 5. Error Handling Table

```markdown
## Error Handling

| Issue | Solution |
|-------|----------|
| [Problem 1] | [Fix] |
| [Problem 2] | [Fix] |
| Skipped [step] | GO BACK AND DO STEP [N] |
```

---

## Anti-Skip Patterns

### Pattern 1: Variable Carrying

Force steps to depend on outputs from previous steps:

```markdown
### Step 2: Extract Values [REQUIRED]

Store these values (you'll need ALL of them in later steps):

| Variable | Source |
|----------|--------|
| `title` | Frontmatter |
| `image_path` | Step 3 output |

### Step 5: Upload Image [REQUIRED]

Use `image_path` from Step 3: [instructions]
```

If Step 3 is skipped, Step 5 will fail—creating natural enforcement.

### Pattern 2: Checkpoint Gates

Block progress until verification:

```markdown
## ⏸️ CHECKPOINT: Do NOT proceed until verified

| Check | Status |
|-------|--------|
| Image generated? | |
| Image verified (viewed it)? | |
| Path stored? | |

**If ANY check is incomplete, go back.**
```

### Pattern 3: Explicit Warnings on Skip-Prone Steps

```markdown
### Step 3: Generate Image [REQUIRED - DO NOT SKIP]

**⚠️ THIS STEP IS MANDATORY. DO NOT SKIP IT.**

**If you're about to skip this step, you're making a mistake.**
```

### Pattern 4: Wrong vs Right Examples

```markdown
❌ WRONG: "Your [Lead Magnet Name] is ready"
✅ RIGHT: "Your ChatGPT → Claude Migration Kit is ready"
```

### Pattern 5: TodoWrite Enforcement

```markdown
**Mark Step N complete in your todo list before proceeding.**
```

---

## Writing Effective Instructions

### Be Explicit, Not Suggestive

| ❌ Weak | ✅ Strong |
|---------|----------|
| "Consider adding..." | "Add [specific thing]" |
| "You might want to..." | "You MUST [action]" |
| "Optionally..." | "[REQUIRED]" or remove entirely |
| "If needed..." | Specify exact condition |

### Provide Context (WHY, Not Just WHAT)

```markdown
### Step 4: Set Preview Text [REQUIRED]

**⚠️ PREVIEW TEXT IS CRITICAL FOR OPEN RATES. NEVER LEAVE BLANK.**

Preview text appears after the subject line in email clients.
Without it, email clients show the first line of body content,
which is usually "Hi [name]" - wasting prime real estate.
```

### Use Structured Formats for State

```markdown
**Variables to track:**

| Variable | Value | Set In |
|----------|-------|--------|
| `subject_a` | | Step 1 |
| `image_path` | | Step 3 |
| `preview_text` | | Step 1 |
```

---

## Skill Discovery Optimization

The `description` field determines when Claude activates the skill.

### Required Elements in Description

1. **Action triggers**: "Use when asked to...", "Use when user says..."
2. **Symptom triggers**: Error patterns, contexts, problems
3. **Keyword synonyms**: Alternative phrasings users might use

### Examples

**Bad:**
```yaml
description: Handles email workflows
```

**Good:**
```yaml
description: Fast email triage for both inboxes. Auto-cleans known junk, categorizes remaining, forwards invoices with codes (DCL, HSA, Airbnb, TF). Use when asked to "clean inbox", "check email", or "inbox zero".
```

---

## Required Structure

```
skill-name/
├── SKILL.md           # Required. <500 lines. Core instructions.
├── LEARNED.md         # Required. <50 lines. Dated entries + consolidation.
├── scripts/           # Executable code. Runs but never loaded into context.
├── references/        # Detailed docs. Loaded into context on demand (costs tokens).
├── setup/             # Credential templates, setup instructions.
└── assets/            # Files used in output (templates, icons). Never loaded into context.
```

**Key distinction:** `references/` costs tokens when read. `scripts/` and `assets/` don't — scripts execute and return output, assets are used in generated files. Put large docs, templates, and data in `assets/`, not `references/`.

### When to Split Files

| Keep in SKILL.md | Move to separate file |
|------------------|----------------------|
| Core workflow steps | Detailed reference tables (→ references/) |
| Checkpoints | Extensive examples (→ references/) |
| Critical warnings | Large templates (→ assets/) |
| Variable tracking | Configuration details (→ setup/) |
| Quick start | Executable code (→ scripts/) |

### Reference Files Contextually

```markdown
For the complete list of auto-archive rules, see `references/rules.md`.
```

Claude loads files on-demand, keeping context lean.

---

## Testing Skills (TDD Approach)

### Before Deploying

1. **Identify the gap (RED)**
   - Run the task WITHOUT the skill
   - Document where Claude fails or deviates
   - This is your baseline

2. **Write minimal skill (GREEN)**
   - Address ONLY the documented failures
   - Don't over-engineer

3. **Test with edge cases (REFACTOR)**
   - Run again with the skill
   - Identify new failure modes
   - Add explicit guidance for each

### Validation Checklist

```
[ ] Ran baseline without skill - documented failures
[ ] Skill addresses specific failures
[ ] All steps have [REQUIRED] markers where needed
[ ] Critical items section lists historically-skipped steps
[ ] TodoWrite checklist creation is mandated
[ ] Checkpoints exist between phases
[ ] Variables carry forward (creating dependencies)
[ ] Wrong vs right examples included
[ ] Error handling table covers common issues
[ ] Description includes triggers and symptoms
[ ] Tested skill activation in fresh session
```

---

## Complete Example

See [references/example-skill.md](references/example-skill.md) for a full bulletproof skill template.

---

## Common Mistakes When Building Skills

| Mistake | Why It's Bad | Do Instead |
|---------|--------------|------------|
| No STOP section | Steps get skipped | Add mandatory checklist |
| No checkpoints | No enforcement | Add checkpoint after each phase |
| Weak language | Feels optional | Use REQUIRED, MUST, ⚠️ |
| No variable carrying | Steps feel independent | Make later steps need earlier outputs |
| No skip warnings | Easy to skip | Add 🚫 COMMONLY SKIPPED section |
| Giant monolithic skill | Hard to maintain | Split into phases + reference files |
| Vague description | Skill not discovered | Add specific triggers and symptoms |
| No testing | Untested = broken | Always TDD approach |
| .5 step numbering | Feels optional | Use full sequential numbers |

---

## Quick Reference

### Markers to Use

| Marker | When to Use |
|--------|-------------|
| `[REQUIRED]` | Every non-optional step |
| `[REQUIRED - DO NOT SKIP]` | Steps that get skipped |
| `⛔` | Critical sections, stop-and-read |
| `⚠️` | Warnings within steps |
| `⏸️` | Checkpoints between phases |
| `🚫` | Commonly skipped steps table |
| `❌` / `✅` | Wrong vs right examples |

### Section Order

1. ⛔ CRITICAL ITEMS (top)
2. ⛔ STOP - READ THIS FIRST
3. 🚫 COMMONLY SKIPPED STEPS
4. PHASE 1 + Checkpoint
5. PHASE 2 + Checkpoint
6. ...
7. Final Verification
8. Error Handling
9. Reference (bottom)

---

## Creating a New Skill

### 1. Scaffold

```bash
python3 scripts/init_skill.py my-skill --path ~/.claude/skills
```

Creates SKILL.md, LEARNED.md, scripts/, references/, setup/, and assets/ with guided TODOs.

### 2. Write the description FIRST

Before the body. The description determines if the skill ever triggers.

**Pattern:** [What it does] + [How/via what] + [Specific actions] + [Trigger keywords]

### 3. Write SKILL.md body

Stay under 500 lines. If approaching 300, start splitting to references/.

### 4. Add LEARNED.md

```markdown
# skill-name - Learned

<!-- Keep under 50 lines. Consolidate before adding. -->

## [Category]

- (YYYY-MM-DD) Observation here
```

### 5. Validate

```bash
python3 scripts/validate_skill.py ~/.claude/skills/my-skill
```

Fix errors, address warnings, re-run until clean.

---

## Frontmatter

```yaml
---
name: skill-name
description: |
  Third person. WHAT it does + WHEN to use it + trigger keywords.
  This is the primary trigger. Max 1024 chars. No angle brackets.
allowed-tools: Bash Read Write
---
```

**name:** kebab-case, max 64 chars. Must match directory name.

**description:** The most important field. Claude reads ALL descriptions to decide which skill to trigger. Front-load trigger conditions. Include keywords users would actually say.

**allowed-tools:** Only tools the skill needs.

**Allowed keys:** `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`. Nothing else.

---

## Self-Learning

Read [LEARNED.md](LEARNED.md) before building or reviewing any skill.

**Update LEARNED.md when you discover:**
- Patterns that worked well in production skills
- Description wording that improved or hurt triggering
- Common mistakes when building skills
- Validation gaps
- Structure decisions that helped or hurt

**Consolidation (keep under 50 lines):**
Before adding, check length. If over 50: merge duplicates, prune stale (>3mo unreinforced), drop one-offs.

---

## Sources

Architecture patterns derived from:
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) - Anthropic
- [Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills) - Anthropic
- [Claude 4 Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices) - Anthropic
- [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system) - Anthropic
- [Prompt Chaining](https://www.promptingguide.ai/techniques/prompt_chaining) - Prompting Guide
