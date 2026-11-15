"""Testes do núcleo menu-mira.py.

Execução:
    python3 tests/test_menu_mira.py
    python3 -m unittest discover -s tests -p "test_*.py"
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "menu-mira.py"
WRAPPER_SH = REPO_ROOT / "bin" / "install.sh"


def load_core():
    spec = importlib.util.spec_from_file_location("menu_mira", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_skill(skills_root: Path, name: str, description: str = "Descrição simples.") -> Path:
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_file


def make_fixture(root: Path) -> Path:
    skills = root / ".agents" / "skills"
    write_skill(skills, "mira-capa")
    write_skill(skills, "mira-validator")
    write_skill(skills, "mira")
    write_skill(skills, "antares-foo")
    shared = skills / "_shared"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "README.md").write_text("# shared\n", encoding="utf-8")
    return skills


def run_cli(cwd: Path, *args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        stdin=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class CoreUnitTests(unittest.TestCase):
    def test_build_command_multiline_description(self):
        core = load_core()
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp)
            skill_file = write_skill(skills, "mira-capa")
            skill_file.write_text(
                "---\nname: mira-capa\ndescription: >-\n  linha um,\n  linha dois + & :\n---\n\n# x\n",
                encoding="utf-8",
            )
            content = core.build_command("mira-capa", skill_file)
        self.assertIn('description: "linha um, linha dois + & :"', content)
        self.assertIn("# Comando `mira-capa` do Mira", content)
        self.assertNotIn(">-", content)
        self.assertTrue(content.startswith("---\n"))

    def test_build_command_fallback_description(self):
        core = load_core()
        with tempfile.TemporaryDirectory() as tmp:
            skill_file = Path(tmp) / "SKILL.md"
            skill_file.write_text("# sem frontmatter\n", encoding="utf-8")
            content = core.build_command("sem-desc", skill_file)
        self.assertIn("Comando Mira: sem-desc", content)

    def test_find_skill_dirs_only_mira(self):
        core = load_core()
        with tempfile.TemporaryDirectory() as tmp:
            skills = make_fixture(Path(tmp))
            names = core.find_skill_dirs(skills)
        self.assertEqual(names, ["mira", "mira-capa", "mira-validator"])

    def test_json_dumps_escaping(self):
        core = load_core()
        with tempfile.TemporaryDirectory() as tmp:
            skill_file = Path(tmp) / "SKILL.md"
            skill_file.write_text('---\ndescription: "aspas \\"internas\\""\n---\n', encoding="utf-8")
            content = core.build_command("x", skill_file)
        line = [ln for ln in content.splitlines() if ln.startswith("description:")][0]
        value = line[len("description: "):]
        self.assertEqual(json.loads(value), 'aspas "internas"')


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def commands_dir(self):
        return self.root / ".opencode" / "commands"

    def backups_dir(self):
        return self.root / ".opencode" / "backups"

    def test_install_creates_commands_and_gitignore(self):
        result = run_cli(self.root, "install", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.commands_dir() / "mira-capa.md").is_file())
        self.assertTrue((self.commands_dir() / "mira-validator.md").is_file())
        self.assertTrue((self.commands_dir() / "mira.md").is_file())
        self.assertFalse((self.commands_dir() / "antares-foo.md").exists())
        self.assertFalse((self.commands_dir() / "_shared.md").exists())
        gitignore = (self.root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(gitignore.count(".opencode/"), 1)

    def test_install_is_idempotent(self):
        run_cli(self.root, "install", "--yes")
        before = (self.commands_dir() / "mira-capa.md").read_bytes()
        second = run_cli(self.root, "install", "--yes")
        self.assertIn("Criados: 0", second.stdout)
        self.assertIn("Sem alteração", second.stdout)
        self.assertEqual(before, (self.commands_dir() / "mira-capa.md").read_bytes())

    def test_gitignore_not_duplicated(self):
        run_cli(self.root, "install", "--yes")
        run_cli(self.root, "install", "--yes")
        lines = (self.root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count(".opencode/"), 1)

    def test_sync_updates_changed_with_backup(self):
        run_cli(self.root, "install", "--yes")
        write_skill(self.root / ".agents" / "skills", "mira-validator", "Descrição ALTERADA.")
        result = run_cli(self.root, "sync", "--yes")
        self.assertIn("Atualizado: mira-validator", result.stdout)
        content = (self.commands_dir() / "mira-validator.md").read_text(encoding="utf-8")
        self.assertIn("Descrição ALTERADA.", content)
        self.assertEqual(len(list(self.backups_dir().glob("mira-validator.md.*.bak"))), 1)

    def test_sync_removes_mira_orphan_with_backup(self):
        run_cli(self.root, "install", "--yes")
        orphan = self.commands_dir() / "mira-old.md"
        orphan.write_text("orfa\n", encoding="utf-8")
        result = run_cli(self.root, "sync", "--yes")
        self.assertIn("Comando órfão detectado: mira-old", result.stdout)
        self.assertFalse(orphan.exists())
        self.assertEqual(len(list(self.backups_dir().glob("mira-old.md.*.bak"))), 1)

    def test_sync_ignores_antares_orphan(self):
        run_cli(self.root, "install", "--yes")
        foreign = self.commands_dir() / "antares-old.md"
        foreign.write_text("fora do escopo do menu-mira\n", encoding="utf-8")
        result = run_cli(self.root, "sync", "--yes")
        self.assertTrue(foreign.exists())
        self.assertNotIn("antares-old", result.stdout)

    def test_opencode_json_preserved_and_backed_up(self):
        (self.root / "opencode.json").write_text('{\n  "x": true\n}\n', encoding="utf-8")
        run_cli(self.root, "install", "--yes")
        self.assertTrue((self.root / "opencode.json").is_file())
        self.assertEqual(len(list(self.backups_dir().glob("opencode.json.*.bak"))), 1)
        run_cli(self.root, "sync", "--yes")
        self.assertTrue((self.root / "opencode.json").is_file())

    def test_dry_run_changes_nothing(self):
        result = run_cli(self.root, "install", "--dry-run", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.commands_dir().exists())
        self.assertFalse((self.root / ".gitignore").exists())

    def test_no_yes_defaults_to_cancel(self):
        result = run_cli(self.root, "install", stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Operação cancelada", result.stdout)
        generated = list(self.commands_dir().glob("*.md")) if self.commands_dir().exists() else []
        self.assertEqual(generated, [])

    def test_missing_skills_root_errors(self):
        result = run_cli(self.root, "install", "--yes", "--skills-root", ".does-not-exist")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERRO", result.stderr + result.stdout)

    def test_determinism_across_runs(self):
        run_cli(self.root, "install", "--yes")
        first = {
            p.name: p.read_bytes() for p in sorted(self.commands_dir().glob("*.md"))
        }
        shutil.rmtree(self.commands_dir())
        run_cli(self.root, "install", "--yes")
        second = {
            p.name: p.read_bytes() for p in sorted(self.commands_dir().glob("*.md"))
        }
        self.assertEqual(first, second)


@unittest.skipUnless(shutil.which("bash"), "bash indisponível")
class WrapperTests(unittest.TestCase):
    def test_bash_wrapper_runs_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_fixture(root)
            result = subprocess.run(
                ["bash", str(WRAPPER_SH), "--yes"],
                cwd=str(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / ".opencode" / "commands" / "mira-validator.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
