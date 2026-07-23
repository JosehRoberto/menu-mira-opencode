# Menu de Comandos Mira para OpenCode

Gera automaticamente os comandos `/mira-*` no menu do OpenCode a partir dos skills instalados pelo [Mira Animator](https://github.com/sandeco/mira-animator).

## Instalação

Após instalar o Mira em uma nova pasta, abra o OpenCode e cole este prompt na primeira mensagem:

> Execute o procedimento descrito em https://github.com/JosehRoberto/menu-mira-opencode para instalar todos os comandos Mira no menu do OpenCode.

O agente acessará este README via `webfetch` e executará o script automaticamente.

> **Compatibilidade:** o script usa Python 3 e bash (Linux/macOS). Quando executado via prompt no OpenCode, o agente de IA traduz os comandos para o shell do seu sistema automaticamente (PowerShell no Windows, zsh no macOS, bash no Linux). Para execução manual no Windows, use Git Bash ou WSL.

### O que o script faz

```bash
mkdir -p .opencode/commands

python3 << 'PYEOF'
import yaml, os, glob

skills_dir = '.agents/skills'
output_dir = '.opencode/commands'
os.makedirs(output_dir, exist_ok=True)

for skill_path in sorted(glob.glob(f'{skills_dir}/mira-*/SKILL.md')):
    skill_name = os.path.basename(os.path.dirname(skill_path))
    out_file = f'{output_dir}/{skill_name}.md'

    with open(skill_path) as f:
        content = f.read()

    parts = content.split('---', 2)
    desc = ''
    if len(parts) >= 3:
        try:
            data = yaml.safe_load(parts[1])
            desc = data.get('description', '') if data else ''
        except:
            pass

    if not desc:
        desc = f'Comando Mira: {skill_name}'

    desc_escaped = desc.replace('"', '\\"')

    with open(out_file, 'w') as f:
        f.write('---\n')
        f.write(f'description: "{desc_escaped}"\n')
        f.write('agent: build\n')
        f.write('model: anthropic/claude-3-5-sonnet-20241022\n')
        f.write('---\n')
        f.write('\n')
        f.write(f'# Comando `{skill_name}` do Mira\n')
        f.write('\n')
        f.write(f'Ative este comando para carregar o skill `{skill_name}` e siga as instruções do SKILL.md.\n')
        f.write('\n')
        f.write('```\n')
        f.write(f'/{skill_name}\n')
        f.write('```\n')

print(f'OK {len(glob.glob(f"{output_dir}/mira-*.md"))} comandos gerados')
PYEOF

rm -f opencode.json

echo "Comandos instalados"
```

Depois feche e reabra o OpenCode.

---

## Comportamento esperado

O OpenCode tem um **bug conhecido** (issue [#4555](https://github.com/anomalyco/opencode/issues/4555)): o autocomplete do menu `/` exibe apenas ~10 comandos inicialmente. **Não é um problema de carregamento** — todos os comandos estão carregados e funcionam normalmente.

| Ação | Comportamento |
|------|---------------|
| Digitar `/` | Mostra ~10 comandos (limitados pelo bug #4555) |
| Digitar `/mira-` | Filtra e mostra os comandos que começam com `mira-` |
| Digitar `/mira-val` | Filtra e mostra `mira-validator` |
| Digitar o comando completo (ex.: `/mira-new`) e Enter | **Funciona normalmente** |

**Conclusão:** não se preocupe com o menu parcial — basta digitar alguns caracteres após `/mira-` que o autocomplete filtra corretamente.

---

## Por que Python em vez de bash/grep?

Os arquivos `SKILL.md` do Mira usam a sintaxe YAML `>-` (bloco foldado) para a descrição:

```yaml
description: >-
  Texto da descrição que continua
  em múltiplas linhas como esta.
```

O `grep` simples pega apenas a linha literal `description: >-` e não o texto real. O parser YAML do Python extrai corretamente o texto completo, garantindo que a descrição apareça no menu do OpenCode.

---

## Atualização (Mira com novos agentes)

Quando o Mira for atualizado com novos skills, abra o OpenCode e cole este prompt:

> Sincronize os comandos Mira no menu do OpenCode conforme o procedimento em https://github.com/JosehRoberto/menu-mira-opencode.

O agente executará o script abaixo. Ele cria arquivos `.md` apenas para skills novos e remove comandos de skills que não existem mais.

```bash
mkdir -p .opencode/commands

python3 << 'PYEOF'
import yaml, os, glob

skills_dir = '.agents/skills'
output_dir = '.opencode/commands'
os.makedirs(output_dir, exist_ok=True)

# Criar comandos para skills novos
for skill_path in sorted(glob.glob(f'{skills_dir}/mira-*/SKILL.md')):
    skill_name = os.path.basename(os.path.dirname(skill_path))
    out_file = f'{output_dir}/{skill_name}.md'

    with open(skill_path) as f:
        content = f.read()

    parts = content.split('---', 2)
    desc = ''
    if len(parts) >= 3:
        try:
            data = yaml.safe_load(parts[1])
            desc = data.get('description', '') if data else ''
        except:
            pass

    if not desc:
        desc = f'Comando Mira: {skill_name}'

    desc_escaped = desc.replace('"', '\\"')

    with open(out_file, 'w') as f:
        f.write('---\n')
        f.write(f'description: "{desc_escaped}"\n')
        f.write('agent: build\n')
        f.write('model: anthropic/claude-3-5-sonnet-20241022\n')
        f.write('---\n')
        f.write('\n')
        f.write(f'# Comando `{skill_name}` do Mira\n')
        f.write('\n')
        f.write(f'Ative este comando para carregar o skill `{skill_name}` e siga as instruções do SKILL.md.\n')
        f.write('\n')
        f.write('```\n')
        f.write(f'/{skill_name}\n')
        f.write('```\n')

# Remover comandos de skills que não existem mais
for cmd_file in glob.glob(f'{output_dir}/mira-*.md'):
    skill_name = os.path.basename(cmd_file).replace('.md', '')
    if not os.path.isdir(f'{skills_dir}/{skill_name}'):
        os.remove(cmd_file)

print(f'OK {len(glob.glob(f"{output_dir}/mira-*.md"))} comandos sincronizados')
PYEOF

rm -f opencode.json
```

Sempre feche e reabra o OpenCode após alterações em `.opencode/commands/`.

---

## Notas técnicas

- **`opencode.json` não é necessário**: o OpenCode descobre skills de `.agents/skills/` automaticamente. O script remove o arquivo por segurança.
- **`agent: build`**: os comandos usam o agente `build` padrão do OpenCode. Se um agente específico for necessário, altere o `agent` no frontmatter.
- **Bug conhecido**: [#4555](https://github.com/anomalyco/opencode/issues/4555) — autocomplete truncado; [#8017](https://github.com/anomalyco/opencode/issues/8017) — delay de ~1 minuto para comandos aparecerem; [#18987](https://github.com/anomalyco/opencode/issues/18987) — `opencode.json` presente pode interferir no carregamento.
- **Versão testada**: OpenCode 1.18.4 com 37 comandos Mira.

---

## Licença

MIT
