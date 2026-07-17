from __future__ import annotations

import subprocess
import unittest
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = (
    ROOT / "plugins" / "stock-data-desk" / "skills" / "stock-data-desk"
)
OAUTH_PLAN = ROOT / "docs" / "hosted-mcp-oauth-migration-plan.md"


class ReleaseRepositoryHygieneTest(unittest.TestCase):
    def test_company_report_workflow_is_required_by_the_skill(self) -> None:
        workflow = SKILL_ROOT / "references" / "company-report-workflow.md"
        self.assertTrue(workflow.is_file())

        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/company-report-workflow.md", skill)

    def test_generated_output_directories_are_ignored(self) -> None:
        rules = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertTrue({"output/", "outputs/"}.issubset(rules))

    def test_only_docs_oauth_plan_is_kept(self) -> None:
        self.assertTrue(OAUTH_PLAN.is_file())
        self.assertFalse((ROOT / "hosted-mcp-oauth-migration-plan.md").exists())

    def test_oauth_plan_is_explicitly_historical(self) -> None:
        preface = OAUTH_PLAN.read_text(encoding="utf-8")[:1600]
        for marker in (
            "历史架构记录和未来 OAuth",
            "`public_noauth`",
            "用户无需",
            "历史方案 / 未来 OAuth 规划",
            "不得复制到当前 Plugin Directory",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, preface)

    def test_current_release_surfaces_do_not_require_login(self) -> None:
        release_surfaces = (
            ROOT / "README.md",
            ROOT / "plugins" / "stock-data-desk" / "README.md",
            ROOT
            / "plugins"
            / "stock-data-desk"
            / ".codex-plugin"
            / "plugin.json",
            ROOT / "docs" / "stocks-info-0.2.0-beta.1-release-notes.md",
        )
        forbidden_phrases = (
            "approved-access beta",
            "reviewer oauth account",
            "pending entitlement",
            "users must log in",
            "user must log in",
            "用户必须登录",
        )

        for path in release_surfaces:
            text = path.read_text(encoding="utf-8").lower()
            for phrase in forbidden_phrases:
                with self.subTest(path=path.relative_to(ROOT), phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_tracked_files_exclude_generated_release_artifacts(self) -> None:
        if not (ROOT / ".git").exists():
            self.skipTest("Git metadata is unavailable")

        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        forbidden: list[str] = []
        for relative in completed.stdout.splitlines():
            path = PurePosixPath(relative)
            if not path.parts:
                continue
            if path.parts[0] in {"output", "outputs"}:
                forbidden.append(relative)
                continue
            if "__pycache__" in path.parts:
                forbidden.append(relative)
                continue
            if path.suffix.lower() in {".csv", ".pdf", ".pyc"}:
                forbidden.append(relative)
                continue
            if path.name == ".env":
                forbidden.append(relative)

        self.assertEqual(forbidden, [])


if __name__ == "__main__":
    unittest.main()
