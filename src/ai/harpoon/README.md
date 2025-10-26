# Harpoon A0-A3 Domain Squatting Detection

A multi-agent system for detecting potential domain squatting and typosquatting attacks by comparing newly registered domains against a list of approved/legitimate domains.

## Overview

Harpoon uses a four-agent architecture (A0-A3) to:

1. **A0 (Orchestrator)**: Coordinates the workflow between agents
2. **A1 (Canonicalizer/Validator)**: Cleans and validates domain names
3. **A2 (Variant Generator)**: Generates potential typosquatting variants
4. **A3 (Fuzzy Matcher/Scorer)**: Scores new domains against approved domains and variants

## Quick Start

### Prerequisites

- Azure AI Foundry project configured
- Environment variables set:
  - `AZURE_EXISTING_AIPROJECT_ENDPOINT`
  - `AZURE_AIPROJECT_NAME` (optional)

### Run with Azure Agents

```bash
python src/ai/harpoon/harpoon_a0_a3.py
```

### Run in Dry-Run Mode (Local Processing)

```bash
python src/ai/harpoon/harpoon_a0_a3.py --dry-run
```

### Custom Configuration

```bash
python src/ai/harpoon/harpoon_a0_a3.py \
  --endpoint "https://your-endpoint.azure.com" \
  --model "gpt-4o-mini" \
  --similarity-threshold 0.85 \
  --approved-domains ./data/approved.md \
  --new-domains ./data/new.md \
  --output ./results/candidates.json \
  --verbose
```

## Input Format

Input files should be Markdown tables with a `Domain` column:

```markdown
# Approved Domains

| # | Domain |
|---|--------|
| 1 | `microsoft.com` |
| 2 | github.com |
| 3 | `azure.com` |
```

- Backticks around domains are handled automatically
- Domains are de-duplicated and canonicalized
- Whitespace is stripped

## Output

### Console Summary

```
================================================================================
HARPOON A0-A3 SUMMARY
================================================================================
Clean approved domains: 10
Clean new domains: 12
Suspicious candidates: 8
================================================================================

Top 10 Candidates by Similarity:
--------------------------------------------------------------------------------
Domain                         Looks Like                Similarity   Reason         
--------------------------------------------------------------------------------
micros0ft.com                  microsoft.com             0.933        homoglyph      
faceb00k.com                   facebook.com              0.889        homoglyph      
goog1e.com                     google.com                0.857        char_swap      
--------------------------------------------------------------------------------
```

### JSON Output

Full results are saved to `./src/data/harpoon/candidates.json`:

```json
{
  "candidates": [
    {
      "domain": "micros0ft.com",
      "looks_like": "microsoft.com",
      "similarity": 0.933,
      "reason": "homoglyph",
      "matched_from": "approved"
    }
  ],
  "clean_approved": ["microsoft.com", "github.com", ...],
  "clean_new": ["micros0ft.com", ...]
}
```

## Detection Techniques

### Canonicalization (A1)
- Unicode NFC normalization
- Lowercase conversion
- Prefix stripping (www., m., ftp.)
- Trailing dot removal
- RFC-style validation

### Variant Generation (A2)
- **Homoglyph substitution**: o→0, l→1, i↔l, a→@, e→3, s→5
- **Character operations**: omit, insert, replace, swap
- **Prefix additions**: the-, my-, go-, work-, job-
- **Suffix additions**: -career, -hr, -login, -secure
- **TLD swaps**: .com↔.co/.cm, .net↔.org
- **Hyphen toggles**: add/remove hyphens

### Scoring (A3)
Multiple similarity metrics:
- **Levenshtein distance**: Character-level edit distance
- **Jaro-Winkler similarity**: String matching for typos
- **Trigram similarity**: N-gram based comparison
- **Keyboard adjacency**: Common typos from keyboard layout
- **Homoglyph detection**: Visual similarity characters

**Flagging criteria**:
- Similarity ≥ 0.85 (configurable)
- Edit distance ≤ 2
- Homoglyph characters present

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--endpoint` | `$AZURE_EXISTING_AIPROJECT_ENDPOINT` | Azure AI Foundry endpoint |
| `--project` | `$AZURE_AIPROJECT_NAME` | Azure AI project name |
| `--model` | `gpt-4o-mini` | Model deployment name |
| `--similarity-threshold` | `0.85` | Minimum similarity to flag |
| `--dry-run` | `False` | Use local processing only |
| `--verbose` | `False` | Enable debug logging |
| `--approved-domains` | `./src/data/harpoon/approved_domains.md` | Approved domains file |
| `--new-domains` | `./src/data/harpoon/newly_registered_domains.md` | New domains file |
| `--output` | `./src/data/harpoon/candidates.json` | Output file path |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Input: approved_domains.md, newly_registered_domains.md   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   A0: Orch     │  Orchestrates workflow
                    └────────┬───────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │ A1: Canon│ │ A2: Variant│ │ A3: Score│
          │ /Validator│ │  Generator│ │  /Match  │
          └─────┬────┘ └─────┬─────┘ └────┬─────┘
                │            │             │
                └────────────┴─────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │  candidates.json │
                   └──────────────────┘
```

## Use Cases

- **Security monitoring**: Detect phishing domain registrations
- **Brand protection**: Monitor for trademark infringement
- **Threat intelligence**: Track adversary infrastructure
- **Incident response**: Investigate suspicious domains
- **Compliance**: Maintain approved domain inventories

## Implementation Notes

- **Dry-run mode**: Fully functional local implementation for testing without Azure
- **Error handling**: Clear, actionable error messages for auth, network, and data issues
- **Logging**: Structured logging with INFO (default) and DEBUG (--verbose) levels
- **Type hints**: Full type annotations for maintainability
- **Standards compliance**: Follows Python best practices and Azure SDK patterns
