#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
CONTRACT="$ROOT_DIR/workflow-contract.json"

# signal-update and case-revisit are event-driven meta skills outside the
# DAG (see docs/workflow-contract.md). They are intentionally absent from
# workflow-contract.json stages[] and are listed here as an explicit,
# documented exception rather than a duplicated stage-order list.
meta_skills="signal-update case-revisit"

stage_ids=$(.venv/bin/python -c '
import json
with open("'"$CONTRACT"'", encoding="utf-8") as handle:
    contract = json.load(handle)
for stage in contract["stages"]:
    print(stage["id"])
')

known_skills=$(printf '%s\n%s\n' "$stage_ids" "$meta_skills" | tr '\n' ' ')

# Existing skill directories must be known to the contract (or the meta
# allowlist above) and must carry consistent frontmatter/README references.
# Contract stages that do not yet have a skill directory (e.g. a stage added
# ahead of the task that implements its skill) are not required here; that
# completeness is verified once the implementing task creates the directory.
for dir in "$ROOT_DIR"/.agents/skills/*/; do
  name=$(basename "$dir")
  case " $known_skills " in
    *" $name "*) ;;
    *)
      printf 'Skill directory not present in workflow-contract.json stages or meta_skills: %s\n' "$name" >&2
      exit 1
      ;;
  esac

  file="$dir/SKILL.md"
  if [ ! -f "$file" ]; then
    printf 'Missing skill file: %s\n' ".agents/skills/$name/SKILL.md" >&2
    exit 1
  fi
  if ! grep -Fq "name: $name" "$file"; then
    printf 'Skill frontmatter name mismatch: %s\n' ".agents/skills/$name/SKILL.md" >&2
    exit 1
  fi
  if ! grep -Fq "\`$name\`" "$ROOT_DIR/README.md"; then
    printf 'README does not list skill: %s\n' "$name" >&2
    exit 1
  fi
done

printf 'All project skill checks passed.\n'
