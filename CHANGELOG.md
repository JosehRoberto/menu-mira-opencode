# Changelog

> Convenção: skill `changelog-convention`.
> Ordem **cronológica decrescente**; **não** misturar séries de numeração sem a nota + divisor.

## [Unreleased]

## [1.0.0] - 2026-11-15

### v1.0 (15/11/2026) — Núcleo Python determinístico e multiplataforma

- **Adicionado:** `menu-mira.py` — núcleo único, portátil (Linux/macOS/Windows) e não interativo, com subcomandos `install` e `sync`. Substitui os scripts shell embutidos no README.
- **Adicionado:** flags `--yes`, `--dry-run`, `--backup-dir`, `--keep-gitignore`, `--skills-root`, `--commands-dir`.
- **Adicionado:** wrappers finos `bin/install.sh` e `bin/sync.sh` (Linux/macOS) e `bin/install.ps1` e `bin/sync.ps1` (Windows 10/11).
- **Adicionado:** testes em `tests/test_menu_mira.py` (16 testes), incluindo determinismo, ausência de toque em órfãos `antares-*` e o wrapper bash.
- **Adicionado:** seção Windows 10/11 e matriz de compatibilidade no README.
- **Alterado:** README reescrito para fluxo determinístico (versão fixada + execução não interativa), com pré-requisitos por sistema operacional e solução de problemas (PEP 668, macOS sem `python3`, ExecutionPolicy, encoding).
- **Alterado:** serialização da descrição passou a usar `json.dumps` (antes `desc.replace('"', '\\"')`), tornando válidos textos com aspas, barras, dois-pontos, `+` e `&`.
- **Alterado:** frontmatter gerado alinhado ao `menu-antares-opencode` (removida a linha em branco entre `agent: build` e `---`).
- **Arquivos:** `menu-mira.py`, `bin/*`, `tests/test_menu_mira.py`, `README.md`.
- **Testes:** +16. Suíte em **16**.

---

> **Nota de versionamento.** O `[1.0.0]` (nov/2026) inaugura a **série atual** do projeto `menu-mira-opencode`, baseada no núcleo Python. O bloco abaixo — `[0.x]`, com data **até 2026-11-15** — é o **histórico legado** da numeração anterior, baseada em script shell embutido no README.

## Histórico legado (pré-v1 — até 2026-11-15)

## [0.1.0] - 2026-11-15

### v0.1 (15/11/2026) — Scripts shell embutidos no README

- **Adicionado:** README com scripts Bash de instalação segura e sincronização dos comandos Mira no OpenCode (commit `70ba21b`).
- **Arquivos:** `README.md`.
- **Testes:** 0.

---

## Legenda

- **Adicionado** — novas funcionalidades
- **Alterado** — mudanças em funcionalidades existentes
- **Corrigido** — correções de bugs
- **Removido** — funcionalidades removidas
- **Segurança** — correções de vulnerabilidades
- **Obsoleto** — funcionalidades marcadas para remoção futura
