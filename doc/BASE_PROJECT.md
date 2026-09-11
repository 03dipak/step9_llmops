# BASE_PROJECT — this folder is our base project template

> **When we say "this is our base folder", we mean BASE PROJECT — a template repo from
> which we can spawn many projects. It is NOT an ML "base model"** (the embedding / LLM
> foundation models like `bge-base-en-v1.5`, `qwen3-embed`, or `llama-3.3-70b-versatile`
> are runtime dependencies, documented in the corpus — never part of this meaning).

## 1. What this folder is

`step9_llmops` is the canonical base project for the journey-series repos
(`step3_langchain_rag`, `step5_agentic_rag`, `step6_multi_agent`, `step7_deploy`,
`step8_finetune`, …). It exists so a new project starts from a **proven scaffold**
instead of a blank directory:

- **Contracts first:** `AGENTS.md` role map + house rules, `doc/task/0X_*.md`
  module contracts with exit criteria, `doc/design/*_lld_tests.md` verification
  matrices, `doc/DECISIONS.md` decision register.
- **Learner workspace convention (D13):** `doc/notes/` belongs to the person doing
  the work — indexed in `doc/notes/README.md`, absent-until-produced by design.
- **Golden eval data (step9 D16):** `eval/goldens/` uses the exact 8-key schema and
  the T-01 verification matrix (`doc/design/01_lld_tests.md`).
- **Repository hygiene:** uv scaffold, `.env` git-ignored, no secrets ever written,
  agents write markdown only — code stays with the project owner.

## 2. Spawning a new project from this base

Follows the same flow as the earlier step repos: **clone → rename → fresh remote →
fresh secrets → re-ground the eval data.** Nothing here is copied by reference; each
spawn is its own repository.

| Step | What to do | What NOT to do |
|---|---|---|
| 1. Clone | `git clone` this repo, or copy the tree (exclude `.git/`, `.env`, `data/docs/` if the corpus differs) | Copy `.env` or any committed secrets — never |
| 2. Rename | New repo name + `# <New> — …` title in README | Keep the old repo name in headings |
| 3. Remote | Point `origin` at the new project's remote | Push to the base repo's remote |
| 4. Purpose | Rewrite the one-line thesis + role map intro to the new project | Keep step9's capstone narrative verbatim |
| 5. Corpus | Replace `data/docs/` with the new project's own documents | Reuse this repo's bundles — goldens are byte-exact anchored to them (T-01-3) |
| 6. Goldens | Re-run the anchor check (NB-01 pattern) against the new corpus | Ship step9's golden rows unchanged — they will fail grounding |
| 7. Decisions | Keep the *format* of `DECISIONS.md`; re-decide each D for the new scope | Copy D-numbers as if they were already decided |

## 3. What carries over vs. what must be re-decided

Carries over unchanged (conventions):

- `AGENTS.md` role map and house rules (verifiable claims, no scope creep, green links,
  code-free manager docs, no secrets).
- Task-contract, T-matrix, and decision-register *formats*.
- The 8-key golden schema + `S[1-5]-Q\d+ / MS-Q\d+` id convention + union syntax.
- uv scaffold + notebook-first workflow.

Must be re-decided per spawn (register in the new repo's `DECISIONS.md`):

- Corpus sources and per-source budget (the step4/step9 inventory does not transfer).
- Model endpoints (`GROQ_MODEL`, `GEMINI_MODEL`, `LLM_MODEL`), embedder, chunking.
- Any deferral that names a step (e.g. "hybrid fusion is a Step-4 concern" is only true
  in this series' ordering).

## 4. Keeping the base healthy

- The base stays **generic** — real spawns are separate repos; the base is never the
  live project for a real deployment.
- Keep tables of contents (`doc/JOURNEY_MAP.md`, `doc/notes/README.md`) green when a
  section is renamed — same house rule as everywhere else.
- This note itself is a convention file: `review` and `writer md` treat it like README,
  never as a learner worksheet.