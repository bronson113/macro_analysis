import re

with open('tests/test_macro_pipeline.py', 'r') as f:
    content = f.read()

content = re.sub(
    r'cls\.storage = MacroStorage\(cls\.tmp_path / "macro_test\.db"\)',
    r'cls.storage = MacroStorage(indicators_csv=cls.tmp_path / "ind.csv", observations_csv=cls.tmp_path / "obs.csv", snapshots_csv=cls.tmp_path / "snap.csv", news_csv=cls.tmp_path / "news.csv", run_logs_csv=cls.tmp_path / "logs.csv")',
    content
)

content = re.sub(
    r'with tempfile\.NamedTemporaryFile\(suffix="\.db"\) as tmp:\n(\s+)storage = MacroStorage\(tmp\.name\)',
    r'with tempfile.TemporaryDirectory() as tmp:\n\1storage = MacroStorage(indicators_csv=f"{tmp}/ind.csv", observations_csv=f"{tmp}/obs.csv", snapshots_csv=f"{tmp}/snap.csv", news_csv=f"{tmp}/news.csv", run_logs_csv=f"{tmp}/logs.csv")',
    content
)

with open('tests/test_macro_pipeline.py', 'w') as f:
    f.write(content)
