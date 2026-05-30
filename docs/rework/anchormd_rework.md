# anchormd Rework Spec

> **Purpose:** Solve anchormd's real problem — distribution, not features — and position it for its eventual merge into `arete-context` as the bundle-generator component of the Context Bundle primitive (P5).

---

## Part 1: Strategy

### 1.1 Current state

anchormd is a CLAUDE.md generator CLI, live on PyPI (v0.4.0). 60 commits, 693 tests, Stripe integrated. It was renamed from claudemd-forge after competitive name research. It is ready for a monetization layer.

It has zero paying users.

### 1.2 The diagnosis

693 tests and zero paying users is not a feature problem. It is a distribution problem. The product works. Nobody finds it.

This is an easy pattern to fall into — well-tested code feels like progress, and it is progress of a kind, but it is not the progress that gets users. Every hour spent on the 694th test is an hour not spent on the first paying customer.

### 1.3 The fork

anchormd has two futures, and you need to pick one.

**Future A: anchormd stays a standalone commercial CLI.** Solve distribution. Pick a killer integration. Build an audience. Convert. This is a business. It will succeed or fail on its own merits.

**Future B: anchormd becomes the bundle-generator inside `arete-context` (P5).** Commercial surface shuts down. Code is absorbed into the Context Bundle primitive. anchormd stops being a product and starts being infrastructure for the venture studio.

Both are defensible. The question is which one you actually want to run.

### 1.4 The recommendation

**Future B.** Merge into `arete-context`.

Reasoning:

- anchormd alone is a small market. CLAUDE.md generation is useful but not a standalone business for you at this stage.
- The same code serves a much larger surface as part of Credentia (B) — portable professional identity.
- You do not need the distraction of distribution, marketing, and customer support on a side product while building the studio.
- The 693 tests do not go to waste; they are now regression protection for a studio-critical primitive.

If you choose Future A instead, the rest of this doc adjusts — but I'd push back hard on that choice unless you have a specific reason I'm missing.

### 1.5 What "merged into arete-context" actually means

`arete-context` is the Context Bundle primitive. It consists of:

- A bundle generator (this is anchormd, extended)
- An MCP server (this is arete-context-mcp, generalized)
- A signing layer (this is P1, reused)
- An attestation layer (this is P3, reused)

anchormd's role in that stack: the piece that introspects a codebase, a knowledge base, or a workspace and produces the structured markdown bundle that the other layers sign and serve.

The CLI surface stays, because it is a useful authoring tool. The Stripe integration goes away. The PyPI package continues to exist but its role shifts from "commercial product" to "studio infrastructure component."

---

## Part 2: Build Blueprint

### 2.1 Target architecture

```
arete-context (the merged package)
├── generator/                 # (formerly anchormd)
│   ├── introspect.py          # Codebase/workspace analysis
│   ├── templates/             # Bundle templates (CLAUDE.md, context.md, etc.)
│   └── emit.py                # Markdown generation
├── mcp_server/                # (formerly arete-context-mcp)
│   ├── server.py              # MCP protocol implementation
│   └── resolver.py            # Context resolution for requests
├── signing/                   # Imports from arete-ledger (P1)
└── attestation/               # Imports from arete-attest (P3)
```

### 2.2 Functional scope of the generator component

The generator, post-merge, produces three bundle types:

**Type 1: Codebase context (the current anchormd use case)**
- Input: a code repository
- Output: CLAUDE.md or equivalent
- Content: structure, conventions, key files, architecture summary

**Type 2: Professional context (new)**
- Input: a directory of work artifacts (resume, case studies, sample docs)
- Output: signed context bundle in the Credentia format
- Content: professional profile, skills, attestations, work samples

**Type 3: Domain context (new, for future Rubric product line)**
- Input: a domain description and source materials
- Output: a context pack for use with LLMs working in that domain
- Content: vocabulary, conventions, references, constraints

Types 2 and 3 are the surface that justifies the merge. Type 1 is the migrated functionality.

### 2.3 Migration plan

**Phase 0: Decision and communication (this week)**

- Decide Future B (or Future A with explicit reasoning)
- If B: announce on the PyPI listing and GitHub that anchormd is entering merge-into-arete-context phase
- If B: disable Stripe integration; stop any remaining monetization work

**Phase 1: Clean separation (week 1-2)**

- Create the `arete-context` repo
- Move anchormd code into `arete-context/generator/` as a submodule
- Ensure the CLI still works at the existing PyPI entry point (backward compatibility for any existing users)
- Update the anchormd README to point at arete-context as the successor

**Phase 2: Integration with signing and attestation (week 2-4)**

- Import `arete-ledger` as a dependency (Animus extraction must be done first — see Animus spec)
- Bundle outputs get signed by default
- Add verification subcommand to the CLI

**Phase 3: New bundle types (week 4-8)**

- Implement Type 2 (professional context) — this is the first real Credentia artifact
- Implement Type 3 (domain context) — this is infrastructure for Rubric

**Phase 4: MCP server integration (week 6-10, overlaps)**

- Merge arete-context-mcp code into the same repo
- MCP server reads generated bundles and serves them to Claude sessions
- This is the externally visible surface of the whole primitive

### 2.4 What to kill explicitly

- **Stripe integration.** anchormd does not need billing post-merge. Remove the code, revoke the keys.
- **Pricing pages or any monetization UI.** The product is no longer sold standalone.
- **Competitive positioning content** (comparisons to other CLAUDE.md generators). Not the frame anymore.
- **The "ready to monetize" framing** internally. This was the distraction. Name it and move past it.

### 2.5 What to add

- **Signing on every bundle output** by default, with an opt-out flag
- **Verification subcommand:** `arete-context verify <bundle>`
- **Bundle type selector:** `arete-context generate --type=codebase|professional|domain`
- **Integration tests** that round-trip generate → sign → verify → consume via MCP

### 2.6 The 693 tests

Keep all of them. They protect the generator component during the merge. Add new test suites for the new bundle types and the signing integration. Do not refactor existing tests unless they block new work.

This is a case where the prior over-investment in testing pays off. It would have been wasted if you had abandoned the project; since you are repositioning it, the tests keep their value.

### 2.7 Integration with primitive stack

Post-merge, anchormd's code is the **generator component of P5 (Context Bundle)**. It is consumed by:

- **Credentia (product line B)** — the portable professional identity protocol
- **Ledger (product line A)** — bundles are signed by the P1 substrate
- **Gemba (product line E)** — engagement deliverables are produced as signed bundles
- **TIAID** — audit outputs transition from PDF to bundle format

Every studio product that needs to emit structured, signed, LLM-readable context uses this code.

### 2.8 Risk: existing anchormd users

If any users exist (even unpaid), they deserve notice. The PyPI package should continue to work at its current entry point through at least the transition. Breaking changes come with a major version bump and clear migration documentation.

Low-risk in practice given the stated "zero paying users," but worth handling cleanly.

### 2.9 Success criteria

The rework succeeds if:

1. arete-context is on PyPI and anchormd's CLI surface still works via it within four weeks
2. Signed bundle generation is the default by week six
3. The first Credentia bundle (your own professional context) is generated and served via MCP by week eight
4. No time is spent on anchormd-as-standalone-product marketing after the decision is made

---

## Part 3: What to do this week

1. **Make the call: Future A or Future B.** Write the decision down. If A, tell me and I'll rewrite this spec; if B (recommended), proceed.
2. **Update the anchormd GitHub README** with a note about the forthcoming merge. This commits you publicly and ends the ambiguity.
3. **Create the `arete-context` repo** with an empty scaffold and a README that names the merge plan.
4. **Shut down the Stripe integration** (assuming Future B). Revoke keys, remove code. One-hour task.
5. **Write the bundle-type taxonomy.** Codebase, professional, domain — define what each one contains. This spec becomes the target for the merge work.
