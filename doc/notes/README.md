# doc/notes — the learner's workspace

Everything in this folder is written by **you** (the learner) as you complete each
module. Agents read these files during `review`; they never create or edit them.

> Convention (D13): a file listed here may be **absent before its module runs — that
> is by design, not a broken link.** A `review` pass checks a notes file only after
> the module that produces it claims completion, and a link sweep treats absence
> here as "expected future deliverable".

## Expected files (7)

| Module | File | Records | When it lands |
|---|---|---|---|
| 0 | `00_my_definition.md` | your "LLMOps in my words" note: the measure-vs-decide line, 8 pillars, one deferral you can explain (≤ 20 lines) | Mod 0 — `doc/task/00_llmops_foundations.md` |
| 00b | `00b_probe_notes.md` | NB-000 stack-probe evidence + the D9 judge-endpoint decision (no keys) | Mod 00b — when NB-000 runs (`doc/task/00b_uv_scaffold.md` Step 6) |
| 1 | `01_corpus_plan.md` | corpus sources, per-source chunk strategy, per-source golden counts | Mod 1 — before authoring goldens (`doc/task/01_data_testset.md`) |
| 4 | `04_cost_notes.md` | free-tier quota budget — measured, not guessed | Mod 4 — `doc/task/04_observability_cost.md` |
| 5 | `05_guardrail_notes.md` | abstention gate: before/after effect on gate outcome | Mod 5 — `doc/task/05_guardrails.md` |
| 6 | `06_lifecycle_notes.md` | store-maintenance lifecycle observations | Mod 6 — `doc/task/06_lifecycle.md` |
| 7 | `07_demo_script.md` | 5-minute demo script — the story order you will actually say | Mod 7 — `doc/task/07_demo_ui.md` |

Every file above: markdown only, no API keys or tokens, committed as review evidence.

Heavy artifacts (probe outputs, golden anchors) stay with their notebooks in
`jupyter_notebook/` — never here. Reproducible golden-authoring scripts live in
`tools/goldens/` (in-repo, portable).