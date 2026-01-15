"""
Meta-Prompting Script for Improving Agent Prompts

This script uses the meta-prompting technique from 4_1metaprompt.py to:
1. Extract instructions from each agent prompt
2. Critique the prompt for issues
3. Revise to fix issues
4. Apply best practices for GPT-4 prompts

Usage:
    python improve_prompts.py [--prompt PROMPT_NAME] [--output-dir DIR] [--dry-run]

Examples:
    # Improve all prompts
    python improve_prompts.py

    # Improve specific prompt
    python improve_prompts.py --prompt communication_agent.txt

    # Save to different directory
    python improve_prompts.py --output-dir improved_prompts

    # Preview without saving
    python improve_prompts.py --dry-run
"""

import os
import argparse
from pathlib import Path
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, Field
import difflib

# Initialize OpenAI client
client = OpenAI()
MODEL = "gpt-5.2"  # Using GPT-5.2 for highest quality meta-prompting


# ============================================================================
# Pydantic Models
# ============================================================================

class Instruction(BaseModel):
    instruction_title: str = Field(description="A 2-8 word title of the instruction that the LLM has to follow.")
    extracted_instruction: str = Field(description="The exact text that was extracted from the system prompt that the instruction is derived from.")


class InstructionList(BaseModel):
    instructions: List[Instruction] = Field(description="A list of instructions and their corresponding extracted text that the LLM has to follow.")


class CritiqueIssue(BaseModel):
    issue: str
    snippet: str
    explanation: str
    suggestion: str


class CritiqueIssues(BaseModel):
    issues: List[CritiqueIssue] = Field(..., min_length=0, max_length=6)


# ============================================================================
# System Prompts
# ============================================================================

EXTRACT_INSTRUCTIONS_SYSTEM_PROMPT = """
## Role & Objective
You are an **Instruction-Extraction Assistant**.
Your job is to read a System Prompt provided by the user and distill the **mandatory instructions** the target LLM must obey.

## Instructions
1. **Identify Mandatory Instructions**
   • Locate every instruction in the System Prompt that the LLM is explicitly required to follow.
   • Ignore suggestions, best-practice tips, or optional guidance.

2. **Generate Rules**
   • Re-express each mandatory instruction as a clear, concise rule.
   • Provide the extracted text that the instruction is derived from.
   • Each rule must be standalone and imperative.

## Output Format
Return a json object with a list of instructions which contains an instruction_title and their corresponding extracted text that the LLM has to follow. Do not include any other text or comments.

## Constraints
- Include **only** rules that the System Prompt explicitly enforces.
- Omit any guidance that is merely encouraged, implied, or optional.
"""

CRITIQUE_SYSTEM_PROMPT = """
## Role & Objective
You are a **Prompt-Critique Assistant**.
Examine a user-supplied LLM prompt (targeting GPT-4o or compatible) and surface any weaknesses.

## Instructions
Check for the following issues:
- Ambiguity: Could any wording be interpreted in more than one way?
- Lacking Definitions: Are there any class labels, terms, or concepts that are not defined that might be misinterpreted by an LLM?
- Conflicting, missing, or vague instructions: Are directions incomplete or contradictory?
- Unstated assumptions: Does the prompt assume the model has to be able to do something that is not explicitly stated?

## Do **NOT** list issues of the following types:
- Invent new instructions, tool calls, or external information. You do not know what tools need to be added that are missing.
- Issues that you are not sure about.

## Output Format
Return a JSON object with 0-6 items, each following this schema:

```json
{
  "issue":      "<1-6 word label>",
  "snippet":    "<≤50-word excerpt>",
  "explanation":"<Why it matters>",
  "suggestion": "<Actionable fix>"
}
```
Return a JSON array of these objects. If the prompt is already clear, complete, and effective, return an empty list: `[]`.
"""

REVISE_SYSTEM_PROMPT = """
## Role & Objective
Revise the user's original prompt to resolve most of the listed issues, while preserving the original wording and structure as much as possible.

## Instructions
1. Carefully review the original prompt and the list of issues.
2. Apply targeted edits directly addressing the listed issues. The edits should be as minimal as possible while still addressing the issue.
3. Do not introduce new content or make assumptions beyond the provided information.
4. Maintain the original structure and format of the prompt.

## Output Format
Return only the fully revised prompt. Do not include commentary, summaries, or code fences.
"""

BEST_PRACTICES_SYSTEM_PROMPT = """
## Task
Your task is to take a **Baseline Prompt** (provided by the user) and output a **Revised Prompt** that keeps the original wording and order as intact as possible **while surgically inserting improvements that follow the "GPT‑4 Best Practices" reference**.

## How to Edit
1. **Keep original text** — Only remove something if it directly goes against a best practice. Otherwise, keep the wording, order, and examples as they are.
2. **Add best practices only when clearly helpful.** If a guideline doesn't fit the prompt or its use case (e.g., diff‑format guidance on a non‑coding prompt), just leave that part of the prompt unchanged.
3. **Where to add improvements** (use Markdown `##` headings):
   - At the very top, add *Agentic Reminders* (like Persistence, Tool-calling, or Planning) — only if relevant. Don't add these if the prompt doesn't require agentic behavior (agentic means prompts that involve planning or running tools for a while).
   - When adding sections, follow this order if possible. If some sections do not make sense, don't add them:
     1. `## Role & Objective`
        - State who the model is supposed to be (the role) and what its main goal is.
     2. `## Instructions`
        - List the steps, rules, or actions the model should follow to complete the task.
     3. *(Any sub-sections)*
        - Include any extra sections such as sub-instructions, notes or guidelines already in the prompt that don't fit into the main categories.
     4. `## Reasoning Steps`
        - Explain the step-by-step thinking or logic the model should use when working through the task.
     5. `## Output Format`
        - Describe exactly how the answer should be structured or formatted (e.g., what sections to include, how to label things, or what style to use).
     6. `## Examples`
        - Provide sample questions and answers or sample outputs to show the model what a good response looks like.
     7. `## Context`
        - Supply any background information, retrieved context, or extra details that help the model understand the task better.
   - Don't introduce new sections that don't exist in the Baseline Prompt. For example, if there's no `## Examples` or no `## Context` section, don't add one.
4. If the prompt is for long context analysis or long tool use, repeat key Agentic Reminders, Important Reminders and Output Format points at the end.
5. If there are class labels, evaluation criterias or key concepts, add a definition to each to define them concretely.
6. Add a chain-of-thought trigger at the end of main instructions (like "Think step by step..."), unless one is already there or it would be repetitive.
7. For prompts involving tools or sample phrases, add Failure-mode bullets:
   - "If you don't have enough info to use a tool, ask the user first."
   - "Vary sample phrases to avoid repetition."
8. Match the original tone (formal or casual) in anything you add.
9. **Only output the full Revised Prompt** — no explanations, comments, or diffs. Do not output "keep the original...", you need to fully output the prompt, no shortcuts.
10. Do not delete any sections or parts that are useful and add value to the prompt and doesn't go against the best practices.
11. **Self-check before sending:** Make sure there are no typos, duplicated lines, missing headings, or missed steps.

## GPT‑4 Best Practices Reference
1. **Persistence reminder**: Explicitly instructs the model to continue working until the user's request is fully resolved, ensuring the model does not stop early.
2. **Tool‑calling reminder**: Clearly tells the model to use available tools or functions instead of making assumptions or guesses, which reduces hallucinations.
3. **Planning reminder**: Directs the model to create a step‑by‑step plan and reflect before and after tool calls, leading to more accurate and thoughtful output.
4. **Scaffold structure**: Requires a consistent and predictable heading order (e.g., Role, Instructions, Output Format) to make prompts easier to maintain.
5. **Instruction placement (long context)**: Ensures that key instructions are duplicated or placed strategically so they remain visible and effective in very long prompts.
6. **Chain‑of‑thought trigger**: Adds a phrase that encourages the model to reason step by step, which improves logical and thorough responses.
7. **Instruction‑conflict hygiene**: Checks for and removes any contradictory instructions, ensuring that the most recent or relevant rule takes precedence.
8. **Failure‑mode mitigations**: Adds safeguards against common errors, such as making empty tool calls or repeating phrases, to improve reliability.
9. **Diff / code‑edit format**: Specifies a robust, line‑number‑free diff or code‑edit style for output, making changes clear and easy to apply.
10. **Label Definitions**: Defines all the key labels or terms that are used in the prompt so that the model knows what they mean.
"""


# ============================================================================
# Core Functions
# ============================================================================

def extract_instructions(prompt_text: str) -> InstructionList:
    """Extract mandatory instructions from a prompt."""
    print("  [1/4] Extracting instructions...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": EXTRACT_INSTRUCTIONS_SYSTEM_PROMPT},
            {"role": "user", "content": f"SYSTEM_PROMPT TO ANALYZE: {prompt_text}"}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    import json
    result = json.loads(response.choices[0].message.content)
    return InstructionList(**result)


def critique_prompt(prompt_text: str) -> CritiqueIssues:
    """Critique a prompt for issues."""
    print("  [2/4] Critiquing prompt...")

    user_prompt = f"""
Evaluate the following prompt for clarity, completeness, and effectiveness:
###
{prompt_text}
###
Return your critique using the specified JSON format only.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    import json
    result = json.loads(response.choices[0].message.content)
    return CritiqueIssues(**result)


def revise_prompt(original_prompt: str, critique: CritiqueIssues) -> str:
    """Revise prompt to fix identified issues."""
    print("  [3/4] Revising prompt...")

    if not critique.issues:
        print("      No issues found, skipping revision step")
        return original_prompt

    issues_str = "\n".join(
        f"Issue: {issue.issue}\nSnippet: {issue.snippet}\nExplanation: {issue.explanation}\nSuggestion: {issue.suggestion}\n"
        for issue in critique.issues
    )

    user_prompt = f"""
Here is the original prompt:
---
{original_prompt}
---

Here are the issues to fix:
{issues_str}

Please return **only** the fully revised prompt. Do not include commentary, summaries, or explanations.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": REVISE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.0
    )

    return response.choices[0].message.content


def apply_best_practices(revised_prompt: str) -> str:
    """Apply best practices to the revised prompt."""
    print("  [4/4] Applying best practices...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": BEST_PRACTICES_SYSTEM_PROMPT},
            {"role": "user", "content": f"BASELINE_PROMPT: {revised_prompt}"}
        ],
        temperature=0.0
    )

    return response.choices[0].message.content


def show_diff(original: str, improved: str, filename: str) -> None:
    """Show unified diff between original and improved prompts."""
    print(f"\n{'='*70}")
    print(f"DIFF for {filename}")
    print('='*70)

    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        improved.splitlines(keepends=True),
        fromfile=f"original/{filename}",
        tofile=f"improved/{filename}",
        lineterm=""
    )

    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            print(f"\033[92m{line}\033[0m", end='')  # Green
        elif line.startswith('-') and not line.startswith('---'):
            print(f"\033[91m{line}\033[0m", end='')  # Red
        elif line.startswith('@@'):
            print(f"\033[94m{line}\033[0m", end='')  # Blue
        else:
            print(line, end='')

    print()


def improve_prompt_file(
    prompt_path: Path,
    output_dir: Optional[Path] = None,
    show_diffs: bool = True
) -> str:
    """
    Improve a single prompt file through the meta-prompting pipeline.

    Args:
        prompt_path: Path to the prompt file
        output_dir: Directory to save improved prompt (None = overwrite)
        show_diffs: Whether to show the diff

    Returns:
        The improved prompt text
    """
    print(f"\n{'='*70}")
    print(f"Processing: {prompt_path.name}")
    print('='*70)

    # Read original prompt
    with open(prompt_path, 'r', encoding='utf-8') as f:
        original_prompt = f.read()

    print(f"  Original length: {len(original_prompt)} chars")

    try:
        # Step 1: Extract instructions (for analysis)
        instructions = extract_instructions(original_prompt)
        print(f"      Found {len(instructions.instructions)} instructions")

        # Step 2: Critique
        critique = critique_prompt(original_prompt)
        print(f"      Found {len(critique.issues)} issues")
        for i, issue in enumerate(critique.issues, 1):
            print(f"        {i}. {issue.issue}")

        # Step 3: Revise to fix issues
        revised_prompt = revise_prompt(original_prompt, critique)

        # Step 4: Apply best practices
        improved_prompt = apply_best_practices(revised_prompt)

        print(f"  Improved length: {len(improved_prompt)} chars")
        print(f"  Change: {len(improved_prompt) - len(original_prompt):+d} chars")

        # Show diff
        if show_diffs:
            show_diff(original_prompt, improved_prompt, prompt_path.name)

        # Save if output directory specified
        if output_dir:
            output_path = output_dir / prompt_path.name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(improved_prompt)
            print(f"  ✓ Saved to: {output_path}")

        return improved_prompt

    except Exception as e:
        print(f"  ✗ Error: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Improve agent prompts using meta-prompting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Improve all prompts in place
  python improve_prompts.py

  # Improve specific prompt
  python improve_prompts.py --prompt communication_agent.txt

  # Save to different directory
  python improve_prompts.py --output-dir improved_prompts

  # Preview without saving
  python improve_prompts.py --dry-run --no-diff
        """
    )

    parser.add_argument(
        '--prompt',
        type=str,
        help='Specific prompt file to improve (e.g., communication_agent.txt)'
    )

    parser.add_argument(
        '--prompts-dir',
        type=str,
        default='plotly_agent/prompts',
        help='Directory containing prompt files (default: plotly_agent/prompts)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        help='Directory to save improved prompts (default: overwrite originals)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process prompts but do not save changes'
    )

    parser.add_argument(
        '--no-diff',
        action='store_true',
        help='Do not show diffs'
    )

    args = parser.parse_args()

    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        return 1

    # Setup paths
    prompts_dir = Path(args.prompts_dir)
    if not prompts_dir.exists():
        print(f"Error: Prompts directory not found: {prompts_dir}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None
    if args.dry_run:
        output_dir = None
        print("\n[DRY RUN MODE - No files will be modified]\n")

    # Get prompt files to process
    if args.prompt:
        prompt_files = [prompts_dir / args.prompt]
        if not prompt_files[0].exists():
            print(f"Error: Prompt file not found: {prompt_files[0]}")
            return 1
    else:
        prompt_files = sorted(prompts_dir.glob('*.txt'))

    if not prompt_files:
        print(f"No prompt files found in {prompts_dir}")
        return 1

    # Process each prompt
    print(f"\nFound {len(prompt_files)} prompt file(s) to process")

    results = {}
    for prompt_path in prompt_files:
        try:
            improved = improve_prompt_file(
                prompt_path,
                output_dir=output_dir,
                show_diffs=not args.no_diff
            )
            results[prompt_path.name] = 'success'
        except Exception as e:
            results[prompt_path.name] = f'failed: {e}'

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    for filename, status in results.items():
        symbol = '✓' if status == 'success' else '✗'
        print(f"  {symbol} {filename}: {status}")

    successful = sum(1 for s in results.values() if s == 'success')
    print(f"\nProcessed {len(results)} file(s): {successful} successful")

    if args.dry_run:
        print("\n[DRY RUN - No files were modified]")
    elif output_dir:
        print(f"\nImproved prompts saved to: {output_dir}")
    else:
        print(f"\nPrompts updated in place: {prompts_dir}")

    return 0


if __name__ == "__main__":
    exit(main())
