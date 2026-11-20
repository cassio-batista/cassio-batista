# Stack AEC para Claude Code: arquitetura e construção residencial

Skills, servidores MCP e bibliotecas para usar o Claude Code em projeto residencial: desenho 2D, BIM/IFC, acessibilidade, orçamento SINAPI e memorial descritivo.

> Este arquivo se chama `LEIAME.md`, e não `README.md`, de propósito. O repositório tem o mesmo nome do usuário no GitHub, e um `README.md` aqui apareceria na página do seu perfil.

## Instalação

**Windows** (PowerShell, na pasta do repositório):

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup\instalar-windows.ps1
# opcionais: -SketchUp -Rhino -Archicad -Bonsai -PluginArquitetura -SkillsDDC
```

**macOS** (Terminal, na pasta do repositório):

```bash
bash setup/instalar-macos.sh
# opcionais: --sketchup --rhino --archicad --bonsai --plugin-arquitetura --skills-ddc
```

Para conferir depois: `~/aec-stack/.venv/bin/python setup/verificar_stack.py` (no Windows, `%USERPROFILE%\aec-stack\.venv\Scripts\python.exe`).

## O que é instalado

| Camada | Itens |
|---|---|
| Programas abertos | Blender (+ extensão Bonsai, manual), FreeCAD, LibreCAD, Python 3.12, uv, Node, Git |
| MCPs no Claude Code | `blender` ([mcp-for-blender](https://github.com/ahujasid/blender-mcp)), `freecad` ([neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp)), `autocad` ([puran-water/autocad-mcp](https://github.com/puran-water/autocad-mcp): usa o AutoCAD se estiver aberto, senão ezdxf sem AutoCAD) |
| MCPs opcionais | SketchUp ([sketchup-mcp2](https://github.com/zinin/sketchup-mcp2)), Rhino 8 ([rhinomcp](https://github.com/jingcheng-chen/rhinomcp)), Archicad ([tapir-archicad-MCP](https://github.com/SzamosiMate/tapir-archicad-MCP)), Bonsai ([Bonsai_mcp](https://github.com/JotaDeRodriguez/Bonsai_mcp)) |
| Bibliotecas Python | ezdxf, ifcopenshell, shapely, PyNite, openseespy, ladybug, topologicpy, rhino3dm, openpyxl, pandas, matplotlib, python-docx (`setup/requirements.txt`) |
| Skills deste repositório | copiadas para `~/.claude/skills` (valem em qualquer projeto) |
| Plugins opcionais | [Arch Studio](https://github.com/AlpacaLabsLLC/skills-for-architects) (61 skills de escritório), [DDC](https://github.com/datadrivenconstruction/DDC_Skills_for_AI_Agents_in_Construction) (orçamento) |

Programas comerciais (Revit, SketchUp, Rhino, Archicad, AutoCAD) dependem de licença e não são instalados. O Revit tem MCP oficial da Autodesk em prévia técnica só no Revit 2027.2.

## Skills

| Skill | Para quê | Script |
|---|---|---|
| `orcamento-sinapi` | Busca na tabela SINAPI e gera o orçamento em Excel com etapas, BDI, fórmulas, resumo e curva ABC | `scripts/sinapi.py` |
| `acessibilidade-nbr9050` | Confere rampas, escadas, portas e sanitários pela NBR 9050, a partir de modelo IFC ou de medidas | `scripts/nbr9050.py` |
| `memorial-descritivo` | Redige o memorial por etapa e gera o .docx com capa, quadro de áreas e assinatura do RT | `scripts/gerar_memorial.py` |

Basta pedir no Claude Code, por exemplo "monta o orçamento com esta planilha SINAPI", "confere a acessibilidade deste IFC" ou "faz o memorial descritivo para a prefeitura". A skill certa é carregada sozinha.

## Passos manuais depois do instalador

1. **Blender**: Preferences > Get Extensions > "Bonsai" > Install. Para o MCP: tecla `N` na viewport 3D > aba *MCP for Blender* > *Start MCP Server*.
2. **FreeCAD**: bancada *MCP Addon* > *Start RPC Server*.
3. **DWG**: [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) para converter DXF em DWG e vice-versa.
4. **SINAPI**: baixe a planilha do mês e da UF em [caixa.gov.br/sinapi](https://www.caixa.gov.br/sinapi).

## Segurança

Os MCPs são projetos da comunidade. Vários executam código dentro do programa (Python no Blender e no FreeCAD, Ruby no SketchUp), com acesso aos seus arquivos. Use em projetos de confiança e revise o que o Claude pede para executar.
