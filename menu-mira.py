#!/usr/bin/env python3
"""Gera os comandos /mira-* no menu do OpenCode.

Nucleo unico, portatil (Linux, macOS e Windows) e nao interativo por padrao,
substituindo os scripts Bash embutidos no README.

Subcomandos:
  install   Instalacao inicial: cria os comandos a partir de .agents/skills.
  sync      Sincronizacao: cria/atualiza comandos e remove orfaos com confirmacao.

Exemplos:
  python3 menu-mira.py install --yes
  python3 menu-mira.py sync --yes
  python3 menu-mira.py install --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - mensagem amigavel
    print("ERRO: o modulo 'pyyaml' nao esta instalado.")
    print("Instale com: pip install pyyaml  (ou pip3 install pyyaml)")
    print("Em ambientes com PEP 668: pip install --user pyyaml  ou  python3-yaml pelo gerenciador do sistema.")
    sys.exit(2)


DEFAULT_COMMANDS_DIR = ".opencode/commands"
DEFAULT_SKILLS_ROOT = ".agents/skills"
DEFAULT_BACKUP_DIR = ".opencode/backups"
GITIGNORE_ENTRY = ".opencode/"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="menu-mira.py",
        description="Gera os comandos /mira-* no menu do OpenCode.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("install", "Instalacao inicial segura dos comandos Mira."),
        ("sync", "Sincronizacao dos comandos, com deteccao de orfaos."),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("-y", "--yes", action="store_true",
                       help="Nao interativo: responde 'sim' a todas as confirmacoes.")
        p.add_argument("--dry-run", action="store_true",
                       help="Mostra o que seria feito sem alterar arquivos.")
        p.add_argument("--backup-dir", default=DEFAULT_BACKUP_DIR,
                       help=f"Diretorio de backups (padrao: {DEFAULT_BACKUP_DIR}).")
        p.add_argument("--keep-gitignore", action="store_true",
                       help="Nao altera o .gitignore.")
        p.add_argument("--skills-root", default=DEFAULT_SKILLS_ROOT,
                       help=f"Raiz dos skills (padrao: {DEFAULT_SKILLS_ROOT}).")
        p.add_argument("--commands-dir", default=DEFAULT_COMMANDS_DIR,
                       help=f"Diretorio de comandos (padrao: {DEFAULT_COMMANDS_DIR}).")

    return parser


def make_confirmer(auto_yes: bool):
    def confirm(prompt: str) -> bool:
        if auto_yes:
            print(f"{prompt} [y/N]: y (--yes)")
            return True
        try:
            response = input(f"{prompt} [y/N]: ")
        except EOFError:
            response = ""
        return response.strip().lower() in ("y", "yes", "s", "sim")

    return confirm


def find_skill_dirs(root: Path):
    names = set()
    for path in root.glob("mira-*"):
        if path.is_dir():
            names.add(path.name)
    if (root / "mira").is_dir():
        names.add("mira")
    return sorted(names)


def extract_description(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    frontmatter = text[3:end]
    try:
        data = yaml.safe_load(frontmatter) or {}
    except Exception:
        return ""
    if isinstance(data, dict):
        return str(data.get("description", "")).strip()
    return ""


def build_command(skill_name: str, skill_file: Path) -> str:
    desc = extract_description(skill_file)
    if not desc:
        desc = f"Comando Mira: {skill_name}"
    desc_literal = json.dumps(desc, ensure_ascii=False)
    return (
        "---\n"
        f"description: {desc_literal}\n"
        "agent: build\n"
        "---\n"
        "\n"
        f"# Comando `{skill_name}` do Mira\n"
        "\n"
        f"Ative este comando para carregar o skill `{skill_name}` e siga as instruções do SKILL.md.\n"
        "\n"
        f"/{skill_name}\n"
    )


class Runner:
    def __init__(self, args):
        self.args = args
        self.commands_dir = Path(args.commands_dir)
        self.skills_root = Path(args.skills_root)
        self.backup_dir = Path(args.backup_dir)
        self.dry_run = args.dry_run
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.confirm = make_confirmer(args.yes)
        self.created = 0
        self.updated = 0
        self.removed = 0
        self.skipped = 0

    def backup_file(self, path: Path) -> None:
        if not path.is_file():
            return
        dest = self.backup_dir / f"{path.name}.{self.timestamp}.bak"
        if self.dry_run:
            print(f"[dry-run] Backup: {path} -> {dest}")
            return
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        print(f"Backup criado: {dest}")

    def write_command(self, cmd_file: Path, content: str) -> None:
        if self.dry_run:
            print(f"[dry-run] Escreveria: {cmd_file}")
            return
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        cmd_file.write_text(content, encoding="utf-8")

    def ensure_gitignore(self) -> None:
        if self.args.keep_gitignore:
            return
        gitignore = Path(".gitignore")
        content = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if GITIGNORE_ENTRY in content.splitlines():
            return
        if self.dry_run:
            print(f"[dry-run] Adicionaria ao .gitignore: {GITIGNORE_ENTRY}")
            return
        if content:
            content += "\n"
        content += GITIGNORE_ENTRY + "\n"
        gitignore.write_text(content, encoding="utf-8")
        print(f"Adicionado ao .gitignore: {GITIGNORE_ENTRY}")

    def process_skills(self, existing_label: str) -> None:
        for skill_name in find_skill_dirs(self.skills_root):
            skill_file = self.skills_root / skill_name / "SKILL.md"
            cmd_file = self.commands_dir / f"{skill_name}.md"

            if not skill_file.is_file():
                print(f"Ignorado: {skill_name} (sem SKILL.md)")
                self.skipped += 1
                continue

            content = build_command(skill_name, skill_file)

            if cmd_file.is_file():
                existing = cmd_file.read_text(encoding="utf-8")
                if existing == content:
                    print(f"Sem alteração: {skill_name}")
                    self.skipped += 1
                    continue
                print()
                print(f"{existing_label}: {cmd_file}")
                if self.confirm("Deseja atualizar este comando mantendo backup?"):
                    self.backup_file(cmd_file)
                    self.write_command(cmd_file, content)
                    print(f"Atualizado: {skill_name}")
                    self.updated += 1
                else:
                    print(f"Mantido sem alteração: {skill_name}")
                    self.skipped += 1
            else:
                self.write_command(cmd_file, content)
                print(f"Criado: {skill_name}")
                self.created += 1

    def process_orphans(self) -> None:
        names = set()
        for path in self.commands_dir.glob("mira*.md"):
            names.add(path.name)

        for filename in sorted(names):
            skill_name = filename[:-3]
            if (self.skills_root / skill_name).is_dir():
                continue
            cmd_file = self.commands_dir / filename
            print()
            print(f"Comando órfão detectado: {skill_name}")
            if self.confirm("Deseja remover este comando órfão mantendo backup?"):
                self.backup_file(cmd_file)
                if self.dry_run:
                    print(f"[dry-run] Removeria: {cmd_file}")
                else:
                    cmd_file.unlink()
                print(f"Removido: {skill_name}")
                self.removed += 1
            else:
                print(f"Preservado: {skill_name}")
                self.skipped += 1

    def check_skills_root(self) -> bool:
        if not self.skills_root.is_dir():
            print(f"ERRO: diretório '{self.skills_root}' não encontrado.")
            print("Abra o script na raiz do projeto onde o Mira foi instalado.")
            return False
        return True

    def report_opencode_config(self, backup: bool) -> None:
        found = [name for name in ("opencode.json", "opencode.jsonc") if Path(name).is_file()]
        if not found:
            return
        if backup:
            print("ATENÇÃO: foi encontrado arquivo de configuração do OpenCode neste projeto.")
        else:
            print("Configuração existente do OpenCode detectada neste projeto.")
        for name in found:
            print(f" - {name}")
        print()
        if not backup:
            print("Esses arquivos serão preservados.")
            print()
            return
        print("Esse arquivo NÃO será apagado.")
        print("O OpenCode suporta comandos por arquivos .md e também por configuração JSON/JSONC.")
        print("Apagar automaticamente pode remover configurações válidas do usuário.")
        print()
        if self.confirm("Deseja criar backup desses arquivos agora?"):
            for name in found:
                self.backup_file(Path(name))
        print()

    def make_dirs(self) -> None:
        if self.dry_run:
            return
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)


def run_install(args) -> int:
    runner = Runner(args)
    print("==> Instalação segura dos comandos Mira no OpenCode")
    print()

    if not runner.check_skills_root():
        return 1

    runner.make_dirs()
    runner.report_opencode_config(backup=True)

    if not runner.confirm(f"Deseja gerar os comandos Mira em '{runner.commands_dir}'?"):
        print("Operação cancelada pelo usuário.")
        return 0

    runner.ensure_gitignore()

    print(f"Diretório de skills: {runner.skills_root}")
    print(f"Diretório de comandos: {runner.commands_dir}")
    print()

    runner.process_skills("Comando existente detectado")

    print()
    print("Resumo:")
    print(f" - Criados: {runner.created}")
    print(f" - Atualizados: {runner.updated}")
    print(f" - Ignorados: {runner.skipped}")
    print()
    print("Concluído com segurança.")
    print("Feche e reabra o OpenCode para recarregar os comandos.")
    return 0


def run_sync(args) -> int:
    runner = Runner(args)
    print("==> Sincronização segura dos comandos Mira")
    print()

    if not runner.check_skills_root():
        return 1

    runner.make_dirs()
    runner.report_opencode_config(backup=False)
    runner.ensure_gitignore()
    runner.process_skills("Comando alterado detectado")
    runner.process_orphans()

    print()
    print("Resumo:")
    print(f" - Criados: {runner.created}")
    print(f" - Atualizados: {runner.updated}")
    print(f" - Removidos: {runner.removed}")
    print(f" - Ignorados: {runner.skipped}")
    print()
    print("Sincronização concluída com segurança.")
    print("Feche e reabra o OpenCode após alterações em .opencode/commands/.")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    if args.command == "install":
        return run_install(args)
    if args.command == "sync":
        return run_sync(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
