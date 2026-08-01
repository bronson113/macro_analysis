from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DAILY_WORKFLOW = ROOT / ".github/workflows/daily_macro.yml"
COWORK_WORKFLOW = ROOT / ".github/workflows/chatgpt_coworker.yml"
COWORK_PROMPT = ROOT / "docs/chatgpt_coworker_morning_prompt.md"
WORKFLOW_PATHS = (DAILY_WORKFLOW, COWORK_WORKFLOW)


class TestGitHubWorkflows(unittest.TestCase):
    def test_all_workflow_actions_are_pinned_to_full_commit_shas(self):
        for path in WORKFLOW_PATHS:
            content = path.read_text(encoding="utf-8")
            uses = re.findall(r"uses:\s+([^\s#]+)", content)
            self.assertTrue(uses)
            self.assertTrue(all(re.search(r"@[0-9a-f]{40}$", item) for item in uses))

    def test_cowork_handoff_is_isolated_from_the_daily_data_workflow(self):
        workflow = DAILY_WORKFLOW.read_text(encoding="utf-8")
        dashboard = (ROOT / "web/src/App.jsx").read_text()

        self.assertIn("paths-ignore:", workflow)
        self.assertIn("web/public/llm_analysis.md", workflow)
        self.assertIn("docs/chatgpt_coworker_morning_prompt.md", workflow)
        self.assertIn("EditorialReview", dashboard)

    def test_cowork_workflow_publishes_only_the_editorial_handoff(self):
        workflow = COWORK_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("paths:", workflow)
        self.assertIn("web/public/llm_analysis.md", workflow)
        self.assertIn("docs/chatgpt_coworker_morning_prompt.md", workflow)
        self.assertNotIn("python prefetch_fred.py", workflow)
        self.assertNotIn("python main.py run", workflow)
        self.assertNotIn("validate_fresh_macro_data.py", workflow)
        self.assertNotIn("git-auto-commit-action", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("path: './web/dist'", workflow)

    def test_cowork_prompt_allows_editorial_interpretation_without_action_labels(self):
        prompt = COWORK_PROMPT.read_text(encoding="utf-8")

        self.assertIn("editorial interpretation", prompt)
        self.assertIn("evidence assessments", prompt)
        self.assertNotRegex(
            prompt,
            r"(?i)\b(BUY|SELL|ACCUMULATE|TRIM|CONVICTION|CONFIDENCE)\b",
        )

    def test_docker_dashboard_serves_unified_payload(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn(
            "./output/dashboard_data.json:/usr/share/nginx/html/data.json:ro",
            compose,
        )
        self.assertNotIn("./output/latest_raw_payload.json", compose)

if __name__ == "__main__":
    unittest.main()
