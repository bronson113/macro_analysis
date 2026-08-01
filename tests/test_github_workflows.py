from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATHS = (ROOT / ".github/workflows/daily_macro.yml",)


class TestGitHubWorkflows(unittest.TestCase):
    def test_all_workflow_actions_are_pinned_to_full_commit_shas(self):
        for path in WORKFLOW_PATHS:
            content = path.read_text(encoding="utf-8")
            uses = re.findall(r"uses:\s+([^\s#]+)", content)
            self.assertTrue(uses)
            self.assertTrue(all(re.search(r"@[0-9a-f]{40}$", item) for item in uses))

    def test_legacy_llm_trade_directive_delivery_is_retired(self):
        workflow = (ROOT / ".github/workflows/daily_macro.yml").read_text()
        dashboard = (ROOT / "web/src/App.jsx").read_text()

        self.assertNotIn("llm_analysis.md", workflow)
        self.assertNotIn("LlmAnalysis", dashboard)
        self.assertFalse((ROOT / "web/public/llm_analysis.md").exists())
        self.assertFalse((ROOT / ".github/workflows/chatgpt_coworker.yml").exists())

    def test_docker_dashboard_serves_unified_payload(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn(
            "./output/dashboard_data.json:/usr/share/nginx/html/data.json:ro",
            compose,
        )
        self.assertNotIn("./output/latest_raw_payload.json", compose)

if __name__ == "__main__":
    unittest.main()
