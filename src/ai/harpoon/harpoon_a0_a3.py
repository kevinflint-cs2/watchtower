"""
harpoon_a0_a3.py - Multi-agent domain squatting detection system.

Provisions and runs Azure AI Foundry Agents A0-A3 to detect potential domain
squatting by comparing newly registered domains against approved domains.
"""

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from typing import Any

from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Agent instructions (use verbatim as specified)
AGENT_INSTRUCTIONS = {
    "A0": (
        "You are Harpoon-A0 (Orchestrator). Receive 'approved_domains' and 'new_domains' in the same thread. "
        "1) Call A1 with both lists. 2) When A1 returns {clean_approved, clean_new}, call A2 with {clean_approved} "
        "and call A3 with {clean_approved, clean_new}. 3) When A2 returns {generated_variants}, provide those to A3 "
        "so it can rescore/finalize. 4) Wait for A3 to produce the final 'candidates' array, then stop the run and "
        "return those candidates to the user. Include a brief summary (counts). Do not invoke any agents beyond A3."
    ),
    "A1": (
        "You are Harpoon-A1 (Canonicalizer/Validator). Inputs: approved_domains, new_domains. Convert to lowercase "
        "and Unicode NFC; trim; remove trailing dots; strip prefixes 'www.', 'm.', 'ftp.'; de-duplicate; validate "
        "RFC-style syntax (labels 1–63 chars, total ≤253, alphanumeric or hyphen, no leading/trailing hyphen). "
        "Output JSON: { \"clean_approved\":[...], \"clean_new\":[...], \"rejected_domains\":[{\"value\":\"...\", "
        "\"reason\":\"...\"]}] } and return to caller."
    ),
    "A2": (
        "You are Harpoon-A2 (Variant Generator). Input: clean_approved. For each domain, generate variants using: "
        "omit/insert/replace/swap edits; homoglyphs (o→0, l→1, i↔l, a→@, e→3, s→5); hyphen toggles; prefixes "
        "(the, my, go, work, job); suffixes (career, hr, login, secure); dot-typos; TLD swaps (.com↔.co/.cm, "
        ".net↔.org). Deduplicate and return { \"generated_variants\":[...] } to caller."
    ),
    "A3": (
        "You are Harpoon-A3 (Fuzzy Matcher/Scorer). Inputs: clean_approved, clean_new, generated_variants. "
        "For each domain in clean_new, compute similarity vs both sets using Levenshtein, Jaro-Winkler, n-gram "
        "cosine, keyboard-adjacency, and homoglyph mapping. Choose best 'looks_like'. Mark as candidate if "
        "similarity ≥ 0.85 OR homoglyph present OR edit distance ≤ 2. Output 'candidates' as "
        "[{ \"domain\":\"...\", \"looks_like\":\"...\", \"similarity\":0.93, \"reason\":\"homoglyph|char_swap|tld_swap\", "
        "\"matched_from\":\"approved|variant\" }]. Return to caller."
    ),
}

logger = logging.getLogger(__name__)


def load_domains_from_markdown(path: str) -> list[str]:
    """
    Load domains from a Markdown table file.

    Expects a table with a 'Domain' column. Handles backticked cells and plain text.
    De-duplicates and strips whitespace.

    Args:
        path: Path to the Markdown file

    Returns:
        List of unique domain strings
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Markdown file not found: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    domains = []
    lines = content.strip().split("\n")

    # Find header row to locate Domain column index
    domain_col_idx = -1
    for line in lines:
        if "|" in line and "domain" in line.lower():
            cols = [col.strip() for col in line.split("|")]
            for idx, col in enumerate(cols):
                if "domain" in col.lower():
                    domain_col_idx = idx
                    break
            break

    if domain_col_idx == -1:
        logger.warning(f"No 'Domain' column found in {path}, assuming column index 1")
        domain_col_idx = 1

    # Parse data rows
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "---" in line or "Domain" in line:
            continue
        if "|" not in line:
            continue

        cols = [col.strip() for col in line.split("|")]
        if len(cols) <= domain_col_idx:
            continue

        domain_cell = cols[domain_col_idx]
        # Remove backticks if present
        domain_cell = domain_cell.strip("`").strip()
        if domain_cell and not domain_cell.isdigit():
            domains.append(domain_cell)

    # De-duplicate and return
    unique_domains = list(dict.fromkeys(domains))
    logger.info(f"Loaded {len(unique_domains)} unique domains from {path}")
    return unique_domains


def canonicalize(domains: list[str]) -> list[str]:
    """
    Canonicalize domain names (local fallback implementation).

    Converts to lowercase, normalizes Unicode, strips common prefixes,
    removes trailing dots, and validates basic syntax.

    Args:
        domains: List of domain strings

    Returns:
        List of canonicalized domain strings
    """
    clean = []
    for domain in domains:
        # Normalize Unicode to NFC
        d = unicodedata.normalize("NFC", domain.lower().strip())
        # Remove trailing dots
        d = d.rstrip(".")
        # Strip common prefixes
        for prefix in ["www.", "m.", "ftp."]:
            if d.startswith(prefix):
                d = d[len(prefix) :]
        # Basic validation: non-empty, reasonable length
        if d and len(d) <= 253 and "." in d:
            clean.append(d)

    return list(dict.fromkeys(clean))


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """
    Calculate Jaro-Winkler similarity (simplified implementation).

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 1:
        match_distance = 1

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3.0

    # Jaro-Winkler adjustment
    prefix_len = 0
    for i in range(min(len1, len2)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break
    prefix_len = min(4, prefix_len)

    return jaro + prefix_len * 0.1 * (1 - jaro)


def trigram_similarity(s1: str, s2: str) -> float:
    """
    Calculate trigram similarity between two strings.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    def get_trigrams(s: str) -> set[str]:
        return {s[i : i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}

    t1 = get_trigrams(s1)
    t2 = get_trigrams(s2)

    if not t1 or not t2:
        return 0.0

    intersection = len(t1 & t2)
    union = len(t1 | t2)

    return intersection / union if union > 0 else 0.0


def generate_variants(clean_approved: list[str]) -> list[str]:
    """
    Generate typosquatting variants (local fallback implementation).

    Args:
        clean_approved: List of approved domains

    Returns:
        List of generated variant domains
    """
    variants = []
    homoglyphs = {"o": "0", "l": "1", "i": "l", "a": "@", "e": "3", "s": "5"}
    prefixes = ["the", "my", "go", "work", "job"]
    suffixes = ["career", "hr", "login", "secure"]

    for domain in clean_approved:
        base, tld = domain.rsplit(".", 1) if "." in domain else (domain, "com")

        # Homoglyph substitutions
        for char, replacement in homoglyphs.items():
            if char in base:
                variants.append(base.replace(char, replacement, 1) + "." + tld)

        # Prefixes and suffixes
        for prefix in prefixes:
            variants.append(f"{prefix}{base}.{tld}")
        for suffix in suffixes:
            variants.append(f"{base}{suffix}.{tld}")
            variants.append(f"{base}-{suffix}.{tld}")

        # TLD swaps
        for alt_tld in ["co", "cm", "net", "org"]:
            if alt_tld != tld:
                variants.append(f"{base}.{alt_tld}")

    return list(dict.fromkeys(variants))


def score_candidates(
    clean_new: list[str], clean_approved: list[str], variants: list[str], threshold: float
) -> list[dict[str, Any]]:
    """
    Score new domains against approved and variant domains (local fallback).

    Args:
        clean_new: List of new domains to evaluate
        clean_approved: List of approved domains
        variants: List of generated variants
        threshold: Similarity threshold for flagging

    Returns:
        List of candidate dictionaries with scoring details
    """
    candidates = []
    all_targets = clean_approved + variants

    for new_domain in clean_new:
        best_match = None
        best_similarity = 0.0
        best_reason = ""
        matched_from = ""

        for target in all_targets:
            # Calculate multiple similarity metrics
            lev_dist = levenshtein_distance(new_domain, target)
            max_len = max(len(new_domain), len(target))
            lev_sim = 1.0 - (lev_dist / max_len) if max_len > 0 else 0.0
            jw_sim = jaro_winkler_similarity(new_domain, target)
            tri_sim = trigram_similarity(new_domain, target)

            # Combined similarity (weighted average)
            similarity = (lev_sim * 0.4) + (jw_sim * 0.4) + (tri_sim * 0.2)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = target
                matched_from = "approved" if target in clean_approved else "variant"

                # Determine reason
                if lev_dist <= 2:
                    best_reason = "char_swap"
                elif any(hg in new_domain for hg in ["0", "1", "@", "3", "5"]):
                    best_reason = "homoglyph"
                elif new_domain.rsplit(".", 1)[-1] != target.rsplit(".", 1)[-1]:
                    best_reason = "tld_swap"
                else:
                    best_reason = "similarity"

        # Flag as candidate if meets threshold or has suspicious characteristics
        if best_match and (best_similarity >= threshold or levenshtein_distance(new_domain, best_match) <= 2):
            candidates.append(
                {
                    "domain": new_domain,
                    "looks_like": best_match,
                    "similarity": round(best_similarity, 3),
                    "reason": best_reason,
                    "matched_from": matched_from,
                }
            )

    # Sort by similarity descending
    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates


def get_client(endpoint: str) -> AIProjectClient:
    """
    Initialize Azure AI Project client.

    Args:
        endpoint: Azure AI Foundry endpoint URL

    Returns:
        AIProjectClient instance
    """
    try:
        credential = DefaultAzureCredential()
        client = AIProjectClient(credential=credential, endpoint=endpoint)
        logger.info(f"Connected to Azure AI Project at {endpoint}")
        return client
    except Exception as e:
        logger.error(f"Failed to create Azure AI Project client: {e}")
        raise


def create_agent(client: AIProjectClient, name: str, instructions: str, model: str) -> str:
    """
    Create an Azure AI agent.

    Args:
        client: AIProjectClient instance
        name: Agent name
        instructions: Agent system instructions
        model: Model deployment name

    Returns:
        Agent ID
    """
    try:
        agent = client.agents.create_agent(model=model, name=name, instructions=instructions)
        logger.info(f"Created agent {name}: {agent.id}")
        return agent.id
    except Exception as e:
        logger.error(f"Failed to create agent {name}: {e}")
        raise


def run_agent_workflow(
    client: AIProjectClient,
    orchestrator_id: str,
    approved_domains: list[str],
    new_domains: list[str],
) -> dict[str, Any]:
    """
    Run the multi-agent workflow through Azure AI.

    Args:
        client: AIProjectClient instance
        orchestrator_id: ID of the orchestrator agent (A0)
        approved_domains: List of approved domains
        new_domains: List of newly registered domains

    Returns:
        Results dictionary with candidates
    """
    import time
    
    try:
        # Create thread
        thread = client.agents.threads.create()
        logger.info(f"Created thread: {thread.id}")

        # Post input messages
        approved_msg = f"approved_domains: {json.dumps(approved_domains)}"
        new_msg = f"new_domains: {json.dumps(new_domains)}"

        client.agents.messages.create(thread_id=thread.id, role="user", content=approved_msg)
        client.agents.messages.create(thread_id=thread.id, role="user", content=new_msg)
        logger.info("Posted input messages to thread")

        # Run orchestrator
        run = client.agents.runs.create(thread_id=thread.id, agent_id=orchestrator_id)
        logger.info(f"Created run: {run.id} with initial status: {run.status}")

        # Poll until run completes
        run_status = getattr(run, "status", None)
        poll_count = 0
        max_polls = 120  # 2 minutes max
        
        while run_status in ("queued", "in_progress", "requires_action") and poll_count < max_polls:
            time.sleep(1)
            poll_count += 1
            try:
                run = client.agents.runs.get(thread_id=thread.id, run_id=run.id)
                run_status = getattr(run, "status", None)
                if poll_count % 5 == 0:
                    logger.info(f"Run status: {run_status} (poll {poll_count})")
            except Exception as e:
                logger.warning(f"Polling error: {e}")
                if poll_count > 30:
                    logger.error("Run polling failed repeatedly")
                    break

        logger.info(f"Run completed with status: {run_status}")

        if run_status == "failed":
            last_err = getattr(run, "last_error", None)
            logger.error(f"Agent run failed: {last_err}")
            return {"candidates": [], "clean_approved": [], "clean_new": []}

        # Extract messages from thread
        messages = client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.DESCENDING)
        logger.info(f"Retrieved messages from thread")

        # Find the final response with candidates
        for message in messages:
            if hasattr(message, "text_messages") and message.text_messages:
                for text_msg in message.text_messages:
                    if hasattr(text_msg, "text") and text_msg.text:
                        text_value = text_msg.text.value
                        logger.debug(f"Checking message text: {text_value[:200]}...")
                        # Try to extract JSON from the response
                        match = re.search(r"\{.*\"candidates\".*\}", text_value, re.DOTALL)
                        if match:
                            try:
                                result = json.loads(match.group(0))
                                logger.info("Successfully extracted candidates from agent response")
                                return result
                            except json.JSONDecodeError as e:
                                logger.warning(f"Found candidates text but failed to parse JSON: {e}")

        logger.warning("No candidates found in agent responses")
        return {"candidates": [], "clean_approved": [], "clean_new": []}

    except Exception as e:
        logger.error(f"Agent workflow failed: {e}")
        raise


def print_summary(results: dict[str, Any]) -> None:
    """
    Print summary of results to console.

    Args:
        results: Results dictionary with candidates and counts
    """
    candidates = results.get("candidates", [])
    clean_approved = results.get("clean_approved", [])
    clean_new = results.get("clean_new", [])

    print("\n" + "=" * 80)
    print("HARPOON A0-A3 SUMMARY")
    print("=" * 80)
    print(f"Clean approved domains: {len(clean_approved)}")
    print(f"Clean new domains: {len(clean_new)}")
    print(f"Suspicious candidates: {len(candidates)}")
    print("=" * 80)

    if candidates:
        print("\nTop 10 Candidates by Similarity:")
        print("-" * 80)
        print(f"{'Domain':<30} {'Looks Like':<25} {'Similarity':<12} {'Reason':<15}")
        print("-" * 80)

        for candidate in candidates[:10]:
            domain = candidate.get("domain", "")[:29]
            looks_like = candidate.get("looks_like", "")[:24]
            similarity = candidate.get("similarity", 0.0)
            reason = candidate.get("reason", "")[:14]
            print(f"{domain:<30} {looks_like:<25} {similarity:<12.3f} {reason:<15}")

        print("-" * 80)


def save_candidates(candidates: list[dict[str, Any]], output_path: str) -> None:
    """
    Save candidates to JSON file.

    Args:
        candidates: List of candidate dictionaries
        output_path: Path to output JSON file
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2)
        logger.info(f"Saved {len(candidates)} candidates to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save candidates: {e}")
        raise


def main() -> int:
    """Main entry point for the Harpoon script."""
    parser = argparse.ArgumentParser(
        description="Harpoon A0-A3: Multi-agent domain squatting detection system"
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("AZURE_EXISTING_AIPROJECT_ENDPOINT", ""),
        help="Azure AI Foundry endpoint URL",
    )
    parser.add_argument("--project", default=os.getenv("AZURE_AIPROJECT_NAME", ""), help="Azure AI project name/ID")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model deployment name (default: gpt-4o-mini)")
    parser.add_argument(
        "--similarity-threshold", type=float, default=0.85, help="Similarity threshold (default: 0.85)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Use local scoring only (no Azure agents)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--approved-domains",
        default="./src/data/harpoon/approved_domains.md",
        help="Path to approved domains markdown file",
    )
    parser.add_argument(
        "--new-domains",
        default="./src/data/harpoon/newly_registered_domains.md",
        help="Path to newly registered domains markdown file",
    )
    parser.add_argument(
        "--output",
        default="./src/data/harpoon/candidates.json",
        help="Path to output candidates JSON file",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load environment variables
    load_dotenv()

    try:
        # Load input data
        logger.info("Loading domain lists...")
        approved_domains = load_domains_from_markdown(args.approved_domains)
        new_domains = load_domains_from_markdown(args.new_domains)

        if not approved_domains:
            logger.error("No approved domains loaded")
            return 1

        if not new_domains:
            logger.error("No new domains loaded")
            return 1

        if args.dry_run:
            # Local fallback mode
            logger.info("Running in dry-run mode (local processing only)")
            clean_approved = canonicalize(approved_domains)
            clean_new = canonicalize(new_domains)
            variants = generate_variants(clean_approved)
            candidates = score_candidates(clean_new, clean_approved, variants, args.similarity_threshold)

            results = {
                "clean_approved": clean_approved,
                "clean_new": clean_new,
                "candidates": candidates,
            }
        else:
            # Azure agent mode
            logger.info("Running with Azure AI agents...")

            if not args.endpoint:
                logger.error("Missing --endpoint or AZURE_EXISTING_AIPROJECT_ENDPOINT environment variable")
                return 1

            # Strip quotes from endpoint if present
            endpoint = args.endpoint.strip('"').strip("'")

            # Create client
            client = get_client(endpoint)

            # Create agents A0-A3
            logger.info("Creating agents A0-A3...")
            agent_ids = {}
            for agent_name in ["A0", "A1", "A2", "A3"]:
                full_name = f"Harpoon-{agent_name}"
                agent_ids[agent_name] = create_agent(
                    client, full_name, AGENT_INSTRUCTIONS[agent_name], args.model
                )

            # Note: Agent routing/connections would need additional Azure AI Foundry SDK configuration
            # This is a simplified implementation - full routing may require handoff/function calling setup

            # Run workflow
            logger.info("Running multi-agent workflow...")
            results = run_agent_workflow(client, agent_ids["A0"], approved_domains, new_domains)

            # If Azure didn't return structured results, fall back to local processing
            if not results.get("candidates"):
                logger.warning("Azure workflow did not return candidates, falling back to local processing")
                clean_approved = canonicalize(approved_domains)
                clean_new = canonicalize(new_domains)
                variants = generate_variants(clean_approved)
                candidates = score_candidates(clean_new, clean_approved, variants, args.similarity_threshold)
                results = {
                    "clean_approved": clean_approved,
                    "clean_new": clean_new,
                    "candidates": candidates,
                }

        # Print summary
        print_summary(results)

        # Save candidates
        save_candidates(results.get("candidates", []), args.output)

        # Print full JSON to stdout
        print("\nFull results (JSON):")
        print(json.dumps(results, indent=2))

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
