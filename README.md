# Menu de Comandos Mira para OpenCode

Gera automaticamente os comandos `/mira-*` no menu do OpenCode a partir dos skills instalados pelo [Mira Animator](https://github.com/sandeco/mira-animator).

## Pré-requisitos

- **Python 3** com o módulo `pyyaml`.
  - Instalação: `pip install pyyaml` ou `pip3 install pyyaml`.
  - Verificação: `python3 -c "import yaml"`.
- **Bash** (Linux/macOS).
- No Windows, use Git Bash ou WSL.

## Instalação

Após instalar o Mira em uma nova pasta, abra o OpenCode e cole este prompt na primeira mensagem:

> Execute o procedimento descrito em https://github.com/JosehRoberto/menu-mira-opencode para instalar os comandos Mira no menu do OpenCode com segurança, preservando qualquer configuração existente do OpenCode.

O agente acessará este README via `webfetch` e executará o procedimento descrito aqui.

> **Compatibilidade:** os scripts usam Python 3 e Bash (Linux/macOS). Quando executados via prompt no OpenCode, o agente de IA traduz os comandos para o shell do seu sistema automaticamente (PowerShell no Windows, zsh no macOS, bash no Linux). Para execução manual no Windows, use Git Bash ou WSL.

## O que mudou nesta versão

Esta atualização substitui os scripts anteriores por versões mais seguras e corrige a leitura da `description` dos `SKILL.md`.

- Não removem `opencode.json` nem `opencode.jsonc` automaticamente.
- Criam backup quando o usuário desejar preservar arquivos existentes.
- Pedem confirmação antes de gerar, atualizar ou remover comandos.
- Evitam sobrescrever arquivos sem necessidade.
- Usam `PyYAML` para ler corretamente `description: >-` e outros formatos YAML válidos.
- Tratam melhor o caso em que já existe configuração local do OpenCode.

## Instalação segura

Use este script para uma instalação inicial mais segura. Ele cria os comandos Mira em `.opencode/commands/`, preserva a configuração existente do usuário e oferece backup quando encontrar `opencode.json` ou `opencode.jsonc`.

```bash
#!/usr/bin/env bash
set -euo pipefail

COMMANDS_DIR=".opencode/commands"
SKILLS_ROOT=".agents/skills"
BACKUP_DIR=".opencode/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
CREATED_COUNT=0
SKIPPED_COUNT=0
UPDATED_COUNT=0

echo "==> Instalação segura dos comandos Mira no OpenCode"
echo

if [ ! -d "$SKILLS_ROOT" ]; then
  echo "ERRO: diretório '$SKILLS_ROOT' não encontrado."
  echo "Abra este script na raiz do projeto onde o Mira foi instalado."
  exit 1
fi

mkdir -p "$COMMANDS_DIR"
mkdir -p "$BACKUP_DIR"

backup_file() {
  local file="$1"
  if [ -f "$file" ]; then
    local base
    base="$(basename "$file")"
    cp -p "$file" "$BACKUP_DIR/${base}.${TIMESTAMP}.bak"
    echo "Backup criado: $BACKUP_DIR/${base}.${TIMESTAMP}.bak"
  fi
}

confirm() {
  local prompt="$1"
  local response
  read -r -p "$prompt [y/N]: " response
  case "$response" in
    y|Y|yes|YES|s|S|sim|SIM) return 0 ;;
    *) return 1 ;;
  esac
}

echo "Diretório de skills: $SKILLS_ROOT"
echo "Diretório de comandos: $COMMANDS_DIR"
echo

if [ -f "opencode.json" ] || [ -f "opencode.jsonc" ]; then
  echo "ATENÇÃO: foi encontrado arquivo de configuração do OpenCode neste projeto."
  [ -f "opencode.json" ] && echo " - opencode.json"
  [ -f "opencode.jsonc" ] && echo " - opencode.jsonc"
  echo
  echo "Esse arquivo NÃO será apagado."
  echo "O OpenCode suporta comandos por arquivos .md e também por configuração JSON/JSONC."
  echo "Apagar automaticamente pode remover configurações válidas do usuário."
  echo
  if confirm "Deseja criar backup desses arquivos agora?"; then
    [ -f "opencode.json" ] && backup_file "opencode.json"
    [ -f "opencode.jsonc" ] && backup_file "opencode.jsonc"
  fi
  echo
fi

if ! confirm "Deseja gerar os comandos Mira em '$COMMANDS_DIR'?"; then
  echo "Operação cancelada pelo usuário."
  exit 0
fi

for root in "$SKILLS_ROOT"; do
  [ -d "$root" ] || continue

  for skill_dir in "$root"/mira-*/ "$root"/mira/; do
    [ -d "$skill_dir" ] || continue

    skill_name="$(basename "$skill_dir")"
    skill_file="$skill_dir/SKILL.md"
    cmd_file="$COMMANDS_DIR/$skill_name.md"

    if [ ! -f "$skill_file" ]; then
      echo "Ignorado: $skill_name (sem SKILL.md)"
      SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
      continue
    fi

    tmp_file="$(mktemp)"
    python3 <<'PYEOF' "$skill_file" "$skill_name" "$tmp_file"
import sys
from pathlib import Path
import yaml

skill_file = Path(sys.argv)[3]
skill_name = sys.argv[4]
tmp_file = Path(sys.argv)[5]

data = yaml.safe_load(skill_file.read_text(encoding="utf-8")) or {}
desc = str(data.get("description", "")).strip() if isinstance(data, dict) else ""
if not desc:
    desc = f"Comando Mira: {skill_name}"

content = f"""---
description: "{desc.replace('"', '\\"')}"
agent: build
model: anthropic/claude-3-5-sonnet-20241022
***

# Comando `{skill_name}` do Mira

Ative este comando para carregar o skill `{skill_name}` e siga as instruções do SKILL.md.

/{skill_name}
"""
tmp_file.write_text(content, encoding="utf-8")
PYEOF

    if [ -f "$cmd_file" ]; then
      if cmp -s "$tmp_file" "$cmd_file"; then
        echo "Sem alteração: $skill_name"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        rm -f "$tmp_file"
        continue
      fi

      echo
      echo "Comando existente detectado: $cmd_file"
      if confirm "Deseja atualizar este comando mantendo backup?"; then
        backup_file "$cmd_file"
        mv "$tmp_file" "$cmd_file"
        echo "Atualizado: $skill_name"
        UPDATED_COUNT=$((UPDATED_COUNT + 1))
      else
        echo "Mantido sem alteração: $skill_name"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        rm -f "$tmp_file"
      fi
    else
      mv "$tmp_file" "$cmd_file"
      echo "Criado: $skill_name"
      CREATED_COUNT=$((CREATED_COUNT + 1))
    fi
  done
done

echo
echo "Resumo:"
echo " - Criados: $CREATED_COUNT"
echo " - Atualizados: $UPDATED_COUNT"
echo " - Ignorados: $SKIPPED_COUNT"
echo
echo "Concluído com segurança."
echo "Feche e reabra o OpenCode para recarregar os comandos."
```

Depois feche e reabra o OpenCode.

## Atualização segura

Quando o Mira for atualizado com novos skills, abra o OpenCode e cole este prompt:

> Sincronize os comandos Mira no menu do OpenCode conforme o procedimento seguro em https://github.com/JosehRoberto/menu-mira-opencode, preservando comandos existentes, criando backups e pedindo confirmação antes de remover comandos órfãos.

O script abaixo cria comandos novos, atualiza comandos alterados com backup, preserva `opencode.json` e pergunta antes de remover comandos órfãos.

```bash
#!/usr/bin/env bash
set -euo pipefail

COMMANDS_DIR=".opencode/commands"
SKILLS_ROOT=".agents/skills"
BACKUP_DIR=".opencode/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
CREATED_COUNT=0
UPDATED_COUNT=0
REMOVED_COUNT=0
SKIPPED_COUNT=0

if [ ! -d "$SKILLS_ROOT" ]; then
  echo "ERRO: diretório '$SKILLS_ROOT' não encontrado."
  echo "Abra este script na raiz do projeto onde o Mira foi instalado."
  exit 1
fi

mkdir -p "$COMMANDS_DIR"
mkdir -p "$BACKUP_DIR"

backup_file() {
  local file="$1"
  if [ -f "$file" ]; then
    local base
    base="$(basename "$file")"
    cp -p "$file" "$BACKUP_DIR/${base}.${TIMESTAMP}.bak"
    echo "Backup criado: $BACKUP_DIR/${base}.${TIMESTAMP}.bak"
  fi
}

confirm() {
  local prompt="$1"
  local response
  read -r -p "$prompt [y/N]: " response
  case "$response" in
    y|Y|yes|YES|s|S|sim|SIM) return 0 ;;
    *) return 1 ;;
  esac
}

echo "==> Sincronização segura dos comandos Mira"
echo

if [ -f "opencode.json" ] || [ -f "opencode.jsonc" ]; then
  echo "Configuração existente do OpenCode detectada neste projeto."
  [ -f "opencode.json" ] && echo " - opencode.json"
  [ -f "opencode.jsonc" ] && echo " - opencode.jsonc"
  echo "Esses arquivos serão preservados."
  echo
fi

for root in "$SKILLS_ROOT"; do
  [ -d "$root" ] || continue

  for skill_dir in "$root"/mira-*/ "$root"/mira/; do
    [ -d "$skill_dir" ] || continue

    skill_name="$(basename "$skill_dir")"
    skill_file="$skill_dir/SKILL.md"
    cmd_file="$COMMANDS_DIR/$skill_name.md"

    if [ ! -f "$skill_file" ]; then
      echo "Ignorado: $skill_name (sem SKILL.md)"
      SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
      continue
    fi

    tmp_file="$(mktemp)"
    python3 <<'PYEOF' "$skill_file" "$skill_name" "$tmp_file"
import sys
from pathlib import Path
import yaml

skill_file = Path(sys.argv)[3]
skill_name = sys.argv[4]
tmp_file = Path(sys.argv)[5]

data = yaml.safe_load(skill_file.read_text(encoding="utf-8")) or {}
desc = str(data.get("description", "")).strip() if isinstance(data, dict) else ""
if not desc:
    desc = f"Comando Mira: {skill_name}"

content = f"""---
description: "{desc.replace('"', '\\"')}"
agent: build
model: anthropic/claude-3-5-sonnet-20241022
***

# Comando `{skill_name}` do Mira

Ative este comando para carregar o skill `{skill_name}` e siga as instruções do SKILL.md.

/{skill_name}
"""
tmp_file.write_text(content, encoding="utf-8")
PYEOF

    if [ -f "$cmd_file" ]; then
      if cmp -s "$tmp_file" "$cmd_file"; then
        echo "Sem alteração: $skill_name"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        rm -f "$tmp_file"
      else
        echo
        echo "Comando alterado detectado: $cmd_file"
        if confirm "Deseja atualizar este comando mantendo backup?"; then
          backup_file "$cmd_file"
          mv "$tmp_file" "$cmd_file"
          echo "Atualizado: $skill_name"
          UPDATED_COUNT=$((UPDATED_COUNT + 1))
        else
          echo "Mantido sem alteração: $skill_name"
          SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
          rm -f "$tmp_file"
        fi
      fi
    else
      mv "$tmp_file" "$cmd_file"
      echo "Criado: $skill_name"
      CREATED_COUNT=$((CREATED_COUNT + 1))
    fi
  done
done

for cmd_file in "$COMMANDS_DIR"/mira*.md "$COMMANDS_DIR"/mira.md; do
  [ -f "$cmd_file" ] || continue
  skill_name="$(basename "$cmd_file" .md)"

  if [ ! -d "$SKILLS_ROOT/$skill_name" ]; then
    echo
    echo "Comando órfão detectado: $skill_name"
    if confirm "Deseja remover este comando órfão mantendo backup?"; then
      backup_file "$cmd_file"
      rm -f "$cmd_file"
      echo "Removido: $skill_name"
      REMOVED_COUNT=$((REMOVED_COUNT + 1))
    else
      echo "Preservado: $skill_name"
      SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
  fi
done

echo
echo "Resumo:"
echo " - Criados: $CREATED_COUNT"
echo " - Atualizados: $UPDATED_COUNT"
echo " - Removidos: $REMOVED_COUNT"
echo " - Ignorados: $SKIPPED_COUNT"
echo
echo "Sincronização concluída com segurança."
echo "Feche e reabra o OpenCode após alterações em .opencode/commands/."
```

## Comportamento esperado

O OpenCode tem um **bug conhecido** (issue [#4555](https://github.com/anomalyco/opencode/issues/4555)): o autocomplete do menu `/` exibe apenas parte dos comandos inicialmente. Isso não significa que os comandos não foram carregados; os comandos continuam utilizáveis quando digitados por nome ou quando o filtro reduz a lista.

| Ação | Comportamento |
|------|---------------|
| Digitar `/` | Pode mostrar apenas parte dos comandos |
| Digitar `/mira-` | Filtra e mostra os comandos que começam com `mira-` |
| Digitar `/mira-val` | Filtra e mostra `mira-validator` |
| Digitar o comando completo e pressionar Enter | Funciona normalmente |

Além disso, existe relato de atraso para os comandos aparecerem após alterações, por isso é recomendável fechar e reabrir o OpenCode depois de modificar `.opencode/commands/`.

## Orientações de uso

### Quando usar o script de instalação

Use o script de **Instalação segura** quando:

- o projeto acabou de receber `npx mira install`;
- ainda não existem comandos Mira em `.opencode/commands/`;
- você quer preservar qualquer configuração local já existente do OpenCode.

### Quando usar o script de sincronização

Use o script de **Atualização segura** quando:

- você executou `npx mira update`;
- novas skills Mira foram adicionadas, removidas ou alteradas;
- você quer revisar antes de atualizar ou remover comandos já existentes.

### Sobre `opencode.json` e `opencode.jsonc`

Se já existir `opencode.json` ou `opencode.jsonc`, a recomendação desta versão é **preservar esses arquivos**.

- Não apagar automaticamente.
- Fazer backup antes de qualquer mudança manual.
- Usar `.opencode/commands/*.md` para os comandos Mira.
- Revisar manualmente o conteúdo de `opencode.json` apenas se houver suspeita de conflito de configuração.

Essa mudança existe porque `opencode.json` e `opencode.jsonc` são formatos válidos de configuração do OpenCode, e apagar esses arquivos sem confirmação pode remover configurações legítimas do usuário.

## Notas técnicas

- O OpenCode suporta configuração por `opencode.json` e `opencode.jsonc`, então esses arquivos devem ser preservados por padrão.
- Os scripts desta versão criam backup em `.opencode/backups/` antes de atualizar comandos existentes.
- A remoção de comandos órfãos na sincronização exige confirmação explícita do usuário.
- `PyYAML` é usado para ler o frontmatter de `SKILL.md`, o que garante a extração correta de `description` mesmo quando ela usa `>-` ou outras formas válidas de YAML.
- `skills.paths` não é necessário neste fluxo.
- `agent: build` é usado como agente padrão neste repositório; se houver um agente específico desejado, ajuste o frontmatter conforme necessário.

### Bugs e observações conhecidas

- [#4555](https://github.com/anomalyco/opencode/issues/4555): autocomplete truncado no menu `/`.
- [#8017](https://github.com/anomalyco/opencode/issues/8017): atraso para comandos aparecerem após alterações.
- [#18987](https://github.com/anomalyco/opencode/issues/18987): presença de `opencode.json` pode interferir em alguns cenários; por isso a recomendação atual é preservar, fazer backup e revisar manualmente em vez de apagar automaticamente.

## Licença

MIT