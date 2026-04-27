# Escalations

Pages or situations where the standard migration recipe doesn't fit. Claude Code should **add to this file, not improvise** — leave a one-paragraph summary and the file path, and Andrew decides whether to port or refactor.

_(Empty at handoff time — populate as you work through the waves.)_

## Template

```
### <page>.py — <one-line summary>

**Path:** `rcm_mc/ui/<path>`
**Kind:** <dashboard / workbench / etc>
**Why this is weird:**
- <bullet 1>
- <bullet 2>

**What I tried:**
- <approach 1> — didn't work because <reason>

**Proposed resolution:** <A / B / C>
```

## Example entries (delete once you have real ones)

### foo_page.py — renders its own <html><body> and bypasses chartis_shell()

**Path:** `rcm_mc/ui/foo_page.py`
**Kind:** long-form
**Why this is weird:**
- Emits full HTML document directly, doesn't call `chartis_shell()`.
- Has its own Google Fonts `<link>` with fonts we don't use anymore.
- Contains a hardcoded `<header>` with the old dark top bar baked in.

**What I tried:**
- Wrapping the existing output in `chartis_shell()` — breaks because we'd nest `<html>` tags.

**Proposed resolution:** refactor to return just the body, call `chartis_shell()` at the end. Estimated 30 min; flagging because the signature-preservation rule is ambiguous — the function currently returns a full document.
