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
| `data` / `ingestion` | **Data** | `{text, metadata}` schema, source tags; corpus = class transcripts + QA_DEEP_DIVES content; #25 embedding-drift playbook mapped. |
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
- **Updates but no scope creep** — genuinely-new gaps get registered as decisions (IN / deferred).
- **Keep internal links green.**
- **Manager-facing docs stay code-free; task docs carry the spec.**
- **No secrets.** Never write API keys / tokens into files.