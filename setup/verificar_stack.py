#!/usr/bin/env python3
"""Confere se a stack AEC está instalada: bibliotecas, programas, MCPs e skills."""
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

LIBS = ["ezdxf", "ifcopenshell", "shapely", "Pynite", "openseespy.opensees", "ladybug",
        "topologicpy", "rhino3dm", "openpyxl", "pandas", "matplotlib", "docx"]
PROGRAMAS = {
    "uv": ["uv"], "uvx": ["uvx"], "git": ["git"], "node": ["node"], "claude": ["claude"],
    "blender": ["blender"], "freecad": ["freecad", "FreeCAD", "freecadcmd", "FreeCADCmd"],
}
CAMINHOS_EXTRAS = {
    "blender": [r"C:\Program Files\Blender Foundation", "/Applications/Blender.app"],
    "freecad": [r"C:\Program Files", "/Applications/FreeCAD.app"],
}
SKILLS = ["orcamento-sinapi", "acessibilidade-nbr9050", "memorial-descritivo"]


def ok(msg):
    print(f"  [OK]    {msg}")


def falha(msg):
    print(f"  [FALTA] {msg}")


def main():
    problemas = 0
    print(f"\nPython {sys.version.split()[0]} em {sys.executable}\n\nBibliotecas:")
    for lib in LIBS:
        try:
            m = importlib.import_module(lib)
            ok(f"{lib} {getattr(m, '__version__', '')}")
        except Exception as e:  # noqa: BLE001
            falha(f"{lib}  ({e.__class__.__name__})")
            problemas += 1

    print("\nProgramas:")
    for nome, cmds in PROGRAMAS.items():
        achado = next((shutil.which(c) for c in cmds if shutil.which(c)), None)
        if not achado:
            for base in CAMINHOS_EXTRAS.get(nome, []):
                p = Path(base)
                if p.exists() and (nome != "freecad" or p.suffix == ".app" or any(p.glob("FreeCAD*"))):
                    achado = str(p)
                    break
        (ok if achado else falha)(f"{nome}: {achado or 'não encontrado'}")
        problemas += 0 if achado else 1

    print("\nServidores MCP no Claude Code:")
    if shutil.which("claude"):
        try:
            out = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=120).stdout
            for nome in ("blender", "freecad", "autocad"):
                (ok if nome in out else falha)(nome)
                problemas += 0 if nome in out else 1
        except Exception as e:  # noqa: BLE001
            falha(f"não consegui rodar 'claude mcp list' ({e})")
    else:
        falha("Claude Code não encontrado no PATH")

    print("\nSkills (~/.claude/skills):")
    base = Path(os.path.expanduser("~/.claude/skills"))
    for s in SKILLS:
        existe = (base / s / "SKILL.md").exists()
        (ok if existe else falha)(s)
        problemas += 0 if existe else 1

    print(f"\n{'Tudo certo.' if not problemas else f'{problemas} pendência(s).'}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
