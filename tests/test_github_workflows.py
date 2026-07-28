from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestGitHubWorkflows(unittest.TestCase):
    def test_data_workflow_ignores_chatgpt_coworker_artifact(self):
        workflow = (ROOT / ".github/workflows/daily_macro.yml").read_text()

        self.assertIn("paths-ignore:", workflow)
        self.assertIn("web/public/llm_analysis.md", workflow)

    def test_chatgpt_coworker_workflow_deploys_without_data_fetch(self):
        workflow = (ROOT / ".github/workflows/chatgpt_coworker.yml").read_text()

        self.assertIn("paths:", workflow)
        self.assertIn("web/public/llm_analysis.md", workflow)
        self.assertNotIn("python prefetch_fred.py", workflow)
        self.assertNotIn("python main.py run", workflow)
        self.assertNotIn("validate_fresh_macro_data.py", workflow)


if __name__ == "__main__":
    unittest.main()
