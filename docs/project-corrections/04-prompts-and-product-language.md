# Prompt Corrections And Suggestions

## Why This Matters

`anchormd` is both a product and a guidance generator. That means wording quality is product quality.

The repo currently has several guidance surfaces:

- prompt files in `prompts/`
- generated CLAUDE.md output
- skill docs in `skills/`
- web copy
- README and docs messaging

These should feel like the same product, not parallel drafts.

## Main Corrections

### 1. Separate internal prompts from user-facing claims

Internal prompt language can be strong and opinionated.
User-facing copy should be precise, conservative, and testable.

Correction:

- avoid overstating enforcement or intelligence in product copy
- avoid implying guarantees that the system does not actually provide
- keep marketing claims aligned with what generation, audit, and scan flows truly do

### 2. Standardize terminology

Important terms should be consistent:

- `generate`
- `audit`
- `deep scan`
- `drift`
- `premium`
- `verified`
- `public repo`
- `private repo`

If the same concept has multiple labels, users and future contributors will miss edge cases.

### 3. Make actionability the default

Generated instructions should prefer:

- concrete commands
- concrete anti-patterns
- concrete file or folder references

over vague advice.

## Prompt Design Suggestions

- keep prompts modular by concern
- avoid embedding product-tier logic inside general analysis prompts
- treat security prompts as separate from marketing or positioning prompts
- give prompts a clear output contract where possible

## Good Prompt Review Questions

- does this prompt ask for information the codebase can really support
- does it encourage hallucinated repo facts
- does it blur product policy with analysis logic
- does it produce guidance that another agent could actually follow

## Practical Next Tasks

- audit `prompts/` for duplicated instruction blocks
- align web copy with CLI terminology
- add a small style guide for generated guidance tone
- add examples of “good generated output” and “too vague output”
