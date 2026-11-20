#!/usr/bin/env bash
# Instala a stack AEC para Claude Code no macOS (Homebrew).
#
# Uso, na pasta do repositório:
#   bash setup/instalar-macos.sh                       # stack aberta (recomendada)
#   bash setup/instalar-macos.sh --sketchup --rhino --archicad --bonsai --plugin-arquitetura --skills-ddc
#
# Instala: uv, Python 3.12, Node, Git, Blender, FreeCAD, LibreCAD; bibliotecas Python em ~/aec-stack/.venv;
# MCPs blender, freecad e autocad (ezdxf) no Claude Code; as skills deste repositório em ~/.claude/skills.
# Programas comerciais (Revit, SketchUp, Rhino, Archicad, AutoCAD) não são instalados: precisam de licença.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
STACK="$HOME/aec-stack"
SKETCHUP=0 RHINO=0 ARCHICAD=0 BONSAI=0 PLUGIN=0 DDC=0 SEMPROG=0
for a in "$@"; do
  case "$a" in
    --sketchup) SKETCHUP=1 ;; --rhino) RHINO=1 ;; --archicad) ARCHICAD=1 ;; --bonsai) BONSAI=1 ;;
    --plugin-arquitetura) PLUGIN=1 ;; --skills-ddc) DDC=1 ;; --sem-programas) SEMPROG=1 ;;
    *) echo "opção desconhecida: $a"; exit 2 ;;
  esac
done

PEND=()
passo() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()    { printf '    \033[32m[ok]\033[0m %s\n' "$1"; }
aviso() { printf '    \033[33m[!]\033[0m  %s\n' "$1"; PEND+=("$1"); }
clonar() { if [ -d "$2/.git" ]; then git -C "$2" pull --ff-only >/dev/null; else git clone --depth 1 "$1" "$2"; fi; }
mcp_add() {  # mcp_add nome [-e VAR=val ...] -- comando args
  local nome="$1"; shift
  claude mcp remove "$nome" -s user >/dev/null 2>&1
  if claude mcp add "$nome" -s user "$@"; then ok "MCP '$nome' registrado"; else aviso "falha ao registrar MCP '$nome'"; fi
}

# 1. Programas
if [ "$SEMPROG" = 0 ]; then
  passo "Programas (Homebrew)"
  if ! command -v brew >/dev/null; then
    echo "Homebrew não encontrado. Instale em https://brew.sh e rode de novo."; exit 1
  fi
  for f in git uv python@3.12 node; do
    brew list --formula "$f" >/dev/null 2>&1 && ok "$f já instalado" || { brew install "$f" && ok "$f instalado" || aviso "falha ao instalar $f"; }
  done
  for c in blender freecad librecad; do
    brew list --cask "$c" >/dev/null 2>&1 && ok "$c já instalado" || { brew install --cask "$c" && ok "$c instalado" || aviso "falha ao instalar $c"; }
  done
fi
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
for c in git uv uvx; do command -v "$c" >/dev/null || { echo "'$c' não encontrado no PATH."; exit 1; }; done
TEM_CLAUDE=0; command -v claude >/dev/null && TEM_CLAUDE=1
[ "$TEM_CLAUDE" = 1 ] || aviso "Claude Code não encontrado no PATH: MCPs e plugins não serão registrados"

# 2. Bibliotecas Python
passo "Bibliotecas Python em $STACK/.venv"
mkdir -p "$STACK"
PY="$STACK/.venv/bin/python"
[ -x "$PY" ] || uv venv --python 3.12 "$STACK/.venv"
uv pip install --python "$PY" -r "$REPO/setup/requirements.txt" && ok "bibliotecas instaladas" || aviso "falha no pip install"

# 3. MCPs: código e addons
passo "AutoCAD/DXF MCP (puran-water/autocad-mcp, backend ezdxf no macOS)"
ACAD="$STACK/autocad-mcp"
clonar https://github.com/puran-water/autocad-mcp.git "$ACAD"
(cd "$ACAD" && uv sync) && ok "autocad-mcp pronto" || aviso "uv sync falhou em autocad-mcp"

passo "FreeCAD MCP: addon"
FC="$STACK/freecad-mcp"
clonar https://github.com/neka-nat/freecad-mcp.git "$FC"
MODDIR=""
FCCMD="$(ls /Applications/FreeCAD.app/Contents/Resources/bin/{FreeCADCmd,freecadcmd} 2>/dev/null | head -1)"
if [ -n "$FCCMD" ]; then
  MODDIR="$("$FCCMD" -c "import FreeCAD,os;print('MODDIR='+os.path.join(FreeCAD.getUserAppDataDir(),'Mod'))" 2>/dev/null | sed -n 's/^MODDIR=//p' | tail -1)"
fi
if [ -z "$MODDIR" ]; then
  MODDIR="$HOME/Library/Application Support/FreeCAD/v1-1/Mod"; aviso "pasta Mod do FreeCAD presumida: $MODDIR (confira)"
fi
mkdir -p "$MODDIR" && cp -R "$FC/addon/FreeCADMCP" "$MODDIR/" && ok "addon copiado para $MODDIR/FreeCADMCP"

passo "Blender MCP: addon"
uvx mcp-for-blender install-addon && ok "addon do Blender instalado" || aviso "rode 'uvx mcp-for-blender install-addon' com o Blender fechado"

if [ "$BONSAI" = 1 ]; then
  passo "Bonsai MCP (IFC no Blender)"
  clonar https://github.com/JotaDeRodriguez/Bonsai_mcp.git "$STACK/Bonsai_mcp"
  aviso "Bonsai MCP: instale o addon.py do Bonsai_mcp no Blender (substitui o addon do Blender MCP; use um por vez)"
fi

# 4. Registrar MCPs
if [ "$TEM_CLAUDE" = 1 ]; then
  passo "Registrando servidores MCP no Claude Code (escopo do usuário)"
  mcp_add blender -- uvx mcp-for-blender
  mcp_add freecad -- uvx freecad-mcp
  mcp_add autocad -e AUTOCAD_MCP_BACKEND=ezdxf -- "$ACAD/.venv/bin/python" -m autocad_mcp
  [ "$SKETCHUP" = 1 ] && { mcp_add sketchup -- uvx sketchup-mcp2; aviso "SketchUp: instale o .rbz de github.com/zinin/sketchup-mcp2/releases"; }
  [ "$RHINO" = 1 ]    && { mcp_add rhino -- uvx rhinomcp@latest; aviso "Rhino 8.20+: Tools > Package Manager > 'rhinomcp'; depois o comando mcpstart"; }
  [ "$ARCHICAD" = 1 ] && { mcp_add archicad -- uvx --from tapir-archicad-mcp archicad-server; aviso "Archicad: instale o add-on Tapir"; }
  [ "$BONSAI" = 1 ]   && mcp_add bonsai -- uv --directory "$STACK/Bonsai_mcp" run tools.py
fi

# 5. Skills e plugins
passo "Skills deste repositório → ~/.claude/skills"
mkdir -p "$HOME/.claude/skills"
for d in "$REPO"/.claude/skills/*/; do cp -R "$d" "$HOME/.claude/skills/" && ok "skill $(basename "$d")"; done
if [ "$PLUGIN" = 1 ] && [ "$TEM_CLAUDE" = 1 ]; then
  passo "Plugin Arch Studio (AlpacaLabsLLC/skills-for-architects)"
  claude plugin marketplace add AlpacaLabsLLC/skills-for-architects
  claude plugin install as@skills-for-architects
  aviso "Arch Studio envia um ping anônimo diário de versão/uso; veja o README do projeto para desligar"
fi
if [ "$DDC" = 1 ]; then
  passo "Skills DDC de orçamento"
  npx --yes skills add datadrivenconstruction/ddc_skills_for_ai_agents_in_construction --skill estimate-builder --agent claude-code
fi

# 6. Verificação
passo "Verificação"
"$PY" "$REPO/setup/verificar_stack.py"

cat <<EOF

==> Passos manuais
  1. Blender: Settings > Get Extensions > busque 'Bonsai' > Install (BIM/IFC).
     Para o MCP: tecla N na viewport 3D > aba 'MCP for Blender' > Start MCP Server.
  2. FreeCAD: bancada 'MCP Addon' > Start RPC Server.
  3. DWG: ODA File Converter (opendesign.com/guestfiles/oda_file_converter) para DXF <-> DWG.
  4. SINAPI: baixe a planilha do mês/UF em caixa.gov.br/sinapi.
  5. Reinicie o Claude Code e rode /mcp.
  Python da stack: $PY
EOF
if [ ${#PEND[@]} -gt 0 ]; then printf '\n\033[33m==> Pendências\033[0m\n'; printf '  - %s\n' "${PEND[@]}"; fi
