import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "workflow-contract.json"

EXPECTED_ORDER_CONSTRAINTS = {
    "company-deep-dive": {"yahoo-profile-financials"},
    "financial-analysis": {"company-deep-dive", "financial-data-fetch"},
    "market-action-read": {"market-data-fetch"},
    "quality-and-valuation-check": {"financial-analysis", "market-data-fetch"},
    "investment-thesis": {
        "company-deep-dive",
        "financial-analysis",
        "industry-transmission-analysis",
        "macro-impact-analysis",
        "quality-and-valuation-check",
        "market-action-read",
    },
    "session-wrap": {"investment-thesis"},
    "research-html-output": {"session-wrap"},
}


def load_contract(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def topological_order(contract: dict) -> list:
    stages = {stage["id"]: stage for stage in contract["stages"]}
    state = {}
    order = []

    def visit(stage_id: str, chain: tuple) -> None:
        if state.get(stage_id) == "done":
            return
        if state.get(stage_id) == "visiting":
            path = " -> ".join(chain + (stage_id,))
            raise ValueError(f"cycle detected in workflow contract: {path}")
        state[stage_id] = "visiting"
        for dep in stages[stage_id]["depends_on"]:
            visit(dep, chain + (stage_id,))
        state[stage_id] = "done"
        order.append(stage_id)

    for stage_id in stages:
        visit(stage_id, ())
    return order


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract(CONTRACT_PATH)
        self.stages_by_id = {stage["id"]: stage for stage in self.contract["stages"]}

    def _transitive_deps(self, stage_id: str, seen=None) -> set:
        seen = seen if seen is not None else set()
        for dep in self.stages_by_id[stage_id]["depends_on"]:
            if dep not in seen:
                seen.add(dep)
                self._transitive_deps(dep, seen)
        return seen

    def test_every_output_has_one_owner(self):
        owners = {}
        for stage in self.contract["stages"]:
            for output in stage["outputs"]:
                self.assertNotIn(output, owners, f"duplicate owner for {output}")
                owners[output] = stage["id"]

    def test_terminal_stage_is_session_wrap(self):
        self.assertEqual(self.contract["terminal_stage"], "session-wrap")

    def test_order_constraints_satisfied_transitively(self):
        for stage_id, required_deps in EXPECTED_ORDER_CONSTRAINTS.items():
            self.assertIn(stage_id, self.stages_by_id, f"unknown stage: {stage_id}")
            transitive = self._transitive_deps(stage_id)
            missing = required_deps - transitive
            self.assertFalse(
                missing,
                f"{stage_id} is missing transitive dependency on: {sorted(missing)}",
            )

    def test_topological_order_is_acyclic_and_complete(self):
        order = topological_order(self.contract)
        self.assertEqual(set(order), set(self.stages_by_id))
        position = {stage_id: index for index, stage_id in enumerate(order)}
        for stage in self.contract["stages"]:
            for dep in stage["depends_on"]:
                self.assertLess(
                    position[dep],
                    position[stage["id"]],
                    f"{dep} must precede {stage['id']} in topological order",
                )

    def test_stage_ids_are_unique(self):
        ids = [stage["id"] for stage in self.contract["stages"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_consumable_statuses_are_a_subset_of_stage_statuses(self):
        for status in self.contract["consumable_statuses"]:
            self.assertIn(status, self.contract["stage_statuses"])
        self.assertEqual(self.contract["consumable_statuses"], ["pass", "degraded"])

    def test_every_stage_has_a_question_namespace(self):
        for stage in self.contract["stages"]:
            self.assertTrue(stage.get("question_namespace"), stage["id"])

    def test_depends_on_reference_known_stages(self):
        for stage in self.contract["stages"]:
            for dep in stage["depends_on"]:
                self.assertIn(dep, self.stages_by_id, f"{stage['id']} depends on unknown stage {dep}")


def _extract_order_chain(text: str):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("stock-case-init") and "->" in line:
            return [token.strip().strip("`") for token in line.split("->")]
    return None


DOCS_WITH_DAG_ORDER = ("AGENTS.md", "README.md", "FIRST_RUN.md")


class DocumentedOrderMatchesContractTests(unittest.TestCase):
    """Keeps the human-readable DAG prose in AGENTS.md/README.md/FIRST_RUN.md
    honest against workflow-contract.json instead of letting docs and code drift."""

    def setUp(self):
        self.contract = load_contract(CONTRACT_PATH)
        self.stages_by_id = {stage["id"]: stage for stage in self.contract["stages"]}

    def test_every_doc_has_an_extractable_order_chain(self):
        for doc_name in DOCS_WITH_DAG_ORDER:
            text = (ROOT / doc_name).read_text(encoding="utf-8")
            chain = _extract_order_chain(text)
            self.assertIsNotNone(chain, f"{doc_name} has no 'stock-case-init -> ...' order line")

    def test_every_documented_stage_is_a_real_contract_stage(self):
        for doc_name in DOCS_WITH_DAG_ORDER:
            text = (ROOT / doc_name).read_text(encoding="utf-8")
            chain = _extract_order_chain(text)
            for stage_id in chain:
                self.assertIn(stage_id, self.stages_by_id, f"{doc_name} lists unknown stage {stage_id!r}")

    def test_every_documented_order_respects_contract_dependencies(self):
        for doc_name in DOCS_WITH_DAG_ORDER:
            text = (ROOT / doc_name).read_text(encoding="utf-8")
            chain = _extract_order_chain(text)
            position = {stage_id: index for index, stage_id in enumerate(chain)}
            for stage_id in chain:
                for dep in self.stages_by_id[stage_id]["depends_on"]:
                    if dep not in position:
                        continue
                    self.assertLess(
                        position[dep],
                        position[stage_id],
                        f"{doc_name}: {dep} must precede {stage_id}",
                    )


if __name__ == "__main__":
    unittest.main()
