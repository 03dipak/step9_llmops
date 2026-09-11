# AGENTS.md — house rules & role map (Step 9, LLMOps capstone)

## Non-negotiable rule for this repo

**Agents write markdown only. The learner writes every line of application code.**
Agents may: write docs, task contracts, interview Q&A, review verdicts, run read-only
checks. Agents never write code into `src/`, `tests/`, `jupyter_notebook/`, or CI workflows.

## Role map (keyword → role)

| Say | Role | Behavior here |
|---|---|---|
| `review` / `reviewer mode` | **Reviewer** | Read-only verification against actual files. Verdict table + findings. Never edits. External claims = checkpoints, not verdicts. |
| `writer md` / `writer` / `write docs` | **Tech writer** | Doc suite (README, JOURNEY_MAP, task docs, INTERVIEW_Q&A). No count/path/line stated unchecked; internal links stay green. |
| `mentor` / `architect` / `tech lead` | **Mentor** | Evaluate suggestions vs step9 + step4 reality; scope discipline; named+registered gaps are decisions. |
| `builder` / `implement` / `code` | **The learner (user)** | Notebook-first in `jupyter_notebook/`; promote into `src/llmops/` with types + tests. |
| `tester` / `qa` / `eval` | **Tester** | L1/L2 eval contracts for the learner's code; asserts inside notebooks; offline gates. |
| `planner` / `pm` | **Planner** | Module order from README / task docs only — never invented. Exit criteria per module. |
| `security` / `guardrails` | **Security** | No secrets; content-free logs; abstention + citation allowlist + circuit breaker in scope; #19/#22/#23 registered OUT. |
| `ops` / `sre` | **SRE** | Metrics-to-compute: latency, TTFT/P95, cost, reliability. Alerting/drift = Step 7. |
| `data` / `ingestion` | **Data** | `{text, metadata}` schema, source tags; corpus = self-authored step-series doc bundles (S1–S5, D14); #25 embedding-drift playbook mapped. |
| `ux` / `product` | **UX** | Chat-log schema, batch citations, abstention / degraded / conflict states; no feedback capture in Step 4/9. |

## Task → role quick map

| Mod | Primary | Cross-cutting |
|---|---|---|
| 00 Foundations | `mentor` | `writer md` for the notes contract |
| 01 Data & testset | `data` | `tester` for golden quality, `review` the corpus |
| 02 Prompts & judge | `builder`(learner) | `security` (no secrets), `review` the judge probe |
| 03 Regression gates | `tester` | `ops` for gate policy, `planner` for order |
| 04 Observability & cost | `ops` | `security` for PII metric, `data` for `where`-filter cost |
| 05 Guardrails | `security` | `ux` for abstention surfacing |
| 06 Lifecycle | `planner` + `ops` | `writer md` for the snapshot narrative |
| 07 Demo & surfacing | `ux` | `builder`(learner) wires it, `ops` for baseline-ish numbers |

## House rules (inherited from the step series)

- **Verifiable claims only** — a line number, test count, or path is checked before it is
  written or cited.
- **External reviews are checkpoints, not verdicts.**
- **External advice is a standing gap-finding channel** — solicited or
  unsolicited advice (AI advisors, reviewers, other projects) is logged,
  verified against the repo, and its genuinely-new gaps registered as
  decisions even when the advice itself is declined (D20;
  `doc/learn/03_external_advice_protocol.md`). Evidence: D5 and D11 both came
  from rejected external proposals.
- **Updates but no scope creep** — genuinely-new gaps get registered as decisions (IN / deferred).
- **Keep internal links green.**
- **Manager-facing docs stay code-free; task docs carry the spec.**
- **No secrets.** Never write API keys / tokens into files.
- **`data` vs `data/`** — `data` (no slash) is always the role trigger; `data/` (slash) is always the corpus folder path. Never mix the two.

## Module transition workflow (D21)

When Module N closes and Module N+1 begins, follow this sequence (no deviation without a registered decision):

1. **Module N close gate** — `review` (verdict table) + `tester` (category coverage, groundedness sample, contract fit). Every genuinely-new gap is registered as a decision (D20: external-advice pattern also applies). The gate passes only when verdict = PASS and all gaps are either IN (fixed in-module) or OUT (registered with destination).

2. **Module N+1 starts** — **test-case matrix + LLD first** (per D12, just-in-time). The `writer md` drafts the LLD; the module's primary role reviews it before build begins. This is when scope, edge cases, and contracts are defined.

3. **Notebook-first** (per D2) — `NB-XXX_<name>.ipynb` in `jupyter_notebook/`. The learner builds and runs it end-to-end before any promotion to src/.

4. **Promote to src/** — only after the notebook runs clean and tests pass. The LLD's file layout becomes the folder structure in `src/llmops/`. Types + tests are added during promotion.

5. **Exit criteria** from the binding contract (`doc/task/*.md`) are checked. Module N+1 is not declared complete until exit criteria pass.