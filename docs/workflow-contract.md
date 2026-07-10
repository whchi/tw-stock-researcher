# Workflow Contract

`workflow-contract.json` is the single canonical definition of the research
workflow DAG. It replaces prose ordering lists as the source of truth for
stage dependencies, ownership, and question namespaces.

## Shape

- `terminal_stage`: the stage that gates completion of a case (`session-wrap`).
- `stage_statuses`: full status vocabulary a stage record may hold.
- `consumable_statuses`: statuses a downstream stage may treat as usable input
  (`pass`, `degraded`). `blocked`, `stale`, and `failed` are never consumable.
- `stages[]`: one entry per workflow stage with:
  - `id`: stable stage identifier, matches the owning `.agents/skills/<id>/` directory for DAG stages.
  - `depends_on`: direct upstream stage ids.
  - `required_inputs` / `optional_inputs`: case-relative filenames the stage reads.
  - `outputs`: case-relative filenames the stage writes. Each output has exactly one owning stage across the whole contract.
  - `question_namespace`: the open-questions ID prefix this stage may upsert/resolve.

## The `degraded` rule

A stage's output may carry `status: "degraded"` when a required dataset is
missing rows but the fetch otherwise completed (see `scripts/data_contract.py`,
Task 3). A downstream stage may consume a `degraded` upstream output **only**
when that specific downstream stage explicitly documents that it tolerates the
missing evidence for that upstream output. Absent that explicit allowance,
`degraded` is treated the same as `blocked`: the consuming stage must not
proceed past a read-only preflight check.

`blocked`, `stale`, and `failed` are never consumable by any downstream stage,
regardless of file presence. A file existing on disk is not evidence that its
producing stage passed.

## Non-DAG meta stages

`signal-update` and `case-revisit` are event-driven skills that operate across
the whole case rather than owning a single DAG edge. They are intentionally
absent from `workflow-contract.json` `stages[]`. `tests/structure/test_skills.sh`
tracks them as an explicit, documented exception rather than folding them into
the DAG or maintaining a second duplicated stage list.

## Consumers

- `tests/test_workflow_contract.py` asserts single-writer-per-output, acyclic
  topological order, and the order constraints implied by the current agent
  skill prose.
- `tests/structure/test_skills.sh` derives its skill-name/README checks from
  this file instead of a hardcoded shell list.
- Tasks 4-9 (`scripts/workflow_state.py`, `scripts/open_questions.py`,
  `scripts/build_research_summary.py`, etc.) load this file directly with
  `json.load` to preflight/gate/record stage transitions and to scope question
  namespaces. There is no separate shared Python loader module — the contract
  is plain JSON and each consumer reads it directly.
