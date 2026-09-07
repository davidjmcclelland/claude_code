# Complete Example: Bulletproof Skill

```markdown
---
name: example-workflow
description: [Action] with [outcome]. Use when asked to "[trigger phrase 1]", "[trigger phrase 2]", or when [context/symptom].
---

# Example Workflow

[One sentence description]

---

## ⛔ CRITICAL ITEMS - CHECK EVERY ONE

| # | Item | How to Verify |
|---|------|---------------|
| 1 | **Step 3 completed** | Image file exists at expected path |
| 2 | **Step 7 completed** | Preview text field is not empty |

---

## ⛔ STOP - READ THIS FIRST

**YOU MUST COMPLETE ALL 8 STEPS. NO EXCEPTIONS.**

Create TodoWrite checklist now:

1. [ ] Step 1
2. [ ] Step 2
...

---

## 🚫 COMMONLY SKIPPED STEPS

| Step | What Gets Skipped | Why It Matters |
|------|-------------------|----------------|
| **Step 3** | Image generation | Required for web feed |
| **Step 7** | Preview text | Critical for open rates |

---

## PHASE 1: Preparation

### Step 1.1: [Name] [REQUIRED]

[Instructions]

Store: `variable_1` = [value]

**Mark complete before proceeding.**

---

## ⏸️ CHECKPOINT: PHASE 1 COMPLETE

| Variable | Value |
|----------|-------|
| `variable_1` | [should be set] |

---

## PHASE 2: Execution

### Step 2.1: [Name] [REQUIRED - DO NOT SKIP]

**⚠️ COMMONLY SKIPPED. DO NOT SKIP.**

[Instructions using `variable_1` from Step 1]

**Mark complete before proceeding.**

---

## Final Verification

| Item | Status |
|------|--------|
| Step 1 complete | ✅ |
| Step 2 complete | ✅ |
| All variables set | ✅ |

---

## Error Handling

| Issue | Solution |
|-------|----------|
| Variable missing | Go back to step that sets it |
| Skipped step 3 | GO BACK AND DO STEP 3 |
```
