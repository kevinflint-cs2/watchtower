Here’s a **copy-paste prompt** you can give to GitHub Copilot. It tells Copilot exactly what to build, where to put it, how to wire A0→A3, and what conventions to follow.

---

# Copilot, build Harpoon A0–A3 as a single Python script

**Goal:** Create a single, human-readable Python script that provisions and runs Azure AI Foundry Agents **A0–A3** (Orchestrator, Canonicalizer/Validator, Variant Generator, Fuzzy Matcher/Scorer), then returns the A3 candidates to stdout.

## Constraints & placement

* File path: `./src/ai/harpoon/harpoon_a0_a3.py` (single, standalone script).
* Follow coding guidelines from:
  `https://raw.githubusercontent.com/github/awesome-copilot/refs/heads/main/instructions/python.instructions.md`
  (naming, typing, docstrings, logging, small functions, early returns, no dead code).
* Use these files as style/structure references (do **not** import from them; just mirror structure/clarity):

  * `src/ai/agents/create_agent_simple.py`
  * `src/ai/agents/create_agent_contoso_fs.py`
* Input data files (Markdown tables with a `Domain` column):

  * `./src/data/harpoon/approved_domains.md`
  * `./src/data/harpoon/newly_registered_domains.md`

## What the script must do

1. **Config & CLI**

   * Accept config via env vars and/or CLI args:

     * `--endpoint` (Azure AI Foundry endpoint / Agents service)
     * `--project` (project or hub name/id)
     * `--model` (default small/fast model, e.g., `gpt-4o-mini`)
     * `--similarity-threshold` (default `0.85`)
   * Provide `--dry-run` (parse + local scoring only) and `--verbose` flags.
   * Print a clear summary and JSON output of candidates.

2. **Data loading**

   * Read both Markdown files, extracting the `Domain` column (ignore header/number column).
   * Robust parser: handle backticked cells (e.g., `` `robertha1f.com` ``) and plain text.
   * De-duplicate and strip whitespace.

3. **Agent creation (Azure AI Foundry Agents SDK)**

   * Create agents **A0–A3** programmatically with the following **instructions** (use as the agent “system” text).
   * **Connections**:

     * A0 routes to A1, A2, A3.
     * A2 routes to A3.
     * A1 and A3 return to caller (A0).
   * **Halt at A3**: When A3 returns `candidates`, A0 returns that to the user (stdout).

4. **Run flow**

   * Create a thread/run.
   * Post two messages (approved list, new list).
   * A0 → A1 (clean), A0 → A2 (generate variants), A0 → A3 (clean lists + variants).
   * Wait for A3 results, then print:

     * Counts: clean_approved, clean_new, candidates.
     * Top 10 candidates by similarity (pretty table).
     * Full `candidates` JSON to stdout (and save to `./src/data/harpoon/candidates.json`).

5. **Local fallback (for `--dry-run`)**

   * Implement local pure-Python functions mirroring A1–A3:

     * `canonicalize(domains) -> list[str]`
     * `generate_variants(clean_approved) -> list[str]`
     * `score_candidates(clean_new, clean_approved, variants, threshold) -> list[dict]`
   * Use Levenshtein/Jaro-Winkler via a lightweight library if available, else a simple edit-distance + trigram similarity implementation.

6. **Logging & errors**

   * Use `logging` (INFO default, DEBUG with `--verbose`).
   * Clear exceptions with actionable messages (bad endpoint, auth, malformed MD, empty inputs).

## Agent instructions (use verbatim)

### A0 — Orchestrator (routes_to: A1, A2, A3)

```
You are Harpoon-A0 (Orchestrator). Receive 'approved_domains' and 'new_domains' in the same thread. 1) Call A1 with both lists. 2) When A1 returns {clean_approved, clean_new}, call A2 with {clean_approved} and call A3 with {clean_approved, clean_new}. 3) When A2 returns {generated_variants}, provide those to A3 so it can rescore/finalize. 4) Wait for A3 to produce the final 'candidates' array, then stop the run and return those candidates to the user. Include a brief summary (counts). Do not invoke any agents beyond A3.
```

### A1 — Canonicalizer / Validator (returns to caller)

```
You are Harpoon-A1 (Canonicalizer/Validator). Inputs: approved_domains, new_domains. Convert to lowercase and Unicode NFC; trim; remove trailing dots; strip prefixes 'www.', 'm.', 'ftp.'; de-duplicate; validate RFC-style syntax (labels 1–63 chars, total ≤253, alphanumeric or hyphen, no leading/trailing hyphen). Output JSON: { "clean_approved":[...], "clean_new":[...], "rejected_domains":[{"value":"...", "reason":"..."}] } and return to caller.
```

### A2 — Variant Generator (routes_to: A3)

```
You are Harpoon-A2 (Variant Generator). Input: clean_approved. For each domain, generate variants using: omit/insert/replace/swap edits; homoglyphs (o→0, l→1, i↔l, a→@, e→3, s→5); hyphen toggles; prefixes (the, my, go, work, job); suffixes (career, hr, login, secure); dot-typos; TLD swaps (.com↔.co/.cm, .net↔.org). Deduplicate and return { "generated_variants":[...] } to caller.
```

### A3 — Fuzzy Matcher / Scorer (returns to caller)

```
You are Harpoon-A3 (Fuzzy Matcher/Scorer). Inputs: clean_approved, clean_new, generated_variants. For each domain in clean_new, compute similarity vs both sets using Levenshtein, Jaro-Winkler, n-gram cosine, keyboard-adjacency, and homoglyph mapping. Choose best 'looks_like'. Mark as candidate if similarity ≥ 0.85 OR homoglyph present OR edit distance ≤ 2. Output 'candidates' as [{ "domain":"...", "looks_like":"...", "similarity":0.93, "reason":"homoglyph|char_swap|tld_swap", "matched_from":"approved|variant" }]. Return to caller.
```

## Minimal structure Copilot should generate

* `main()` with argparse.
* `load_domains_from_markdown(path) -> list[str]`
* Azure initialization helper (`get_client()`), guarded by try/except.
* `create_agent(client, name, instructions, model, tools=None, routes=None) -> agent_id`
* Wiring: create A0, A1, A2, A3; set routes (`A0→A1,A2,A3`, `A2→A3`).
* Thread/run helpers:

  * `create_thread(client, project) -> thread_id`
  * `post_message(thread_id, role, content)`
  * `run_agent(thread_id, agent_id) -> run_id`
  * `wait_for_run_complete(run_id) -> artifacts/results`
* Extract `candidates` payload from A3; print summary + save JSON.

## Output & acceptance

* Console summary (Markdown-ish):

  * Clean approved: N
  * Clean new: M
  * Candidates: K
  * Top 10 by similarity (table).
* Save full JSON to `./src/data/harpoon/candidates.json`.
* Exit code `0` on success; non-zero on errors.

## Keep it simple & readable

* Clear function names, type hints, short blocks, docstrings.
* No premature abstractions.
* Prefer standard libs; add minimal third-party only if essential (guarded import + fallback).

**Now generate the complete `./src/ai/harpoon/harpoon.py` implementing the above.**
