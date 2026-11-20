#!/usr/bin/env python3
"""Gera o memorial descritivo (.docx) a partir de um JSON.

    python gerar_memorial.py memorial.json --saida Memorial_Descritivo.docx

Veja o formato em ../SKILL.md e o exemplo em ../references/exemplo.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
except ImportError:
    sys.exit("Instale o python-docx:  pip install python-docx")

FALTA = "[a preencher]"


def area_fmt(v) -> str:
    try:
        return f"{float(v):,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(v)


def sombrear(celula, cor="D9D9D9"):
    tcPr = celula._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), cor)
    tcPr.append(shd)


def tabela(doc, cabecalho, linhas, larguras=None):
    t = doc.add_table(rows=1, cols=len(cabecalho))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, txt in zip(t.rows[0].cells, cabecalho):
        c.text = ""
        r = c.paragraphs[0].add_run(str(txt))
        r.bold = True
        sombrear(c)
    for ln in linhas:
        cells = t.add_row().cells
        for c, txt in zip(cells, ln):
            c.text = "" if txt is None else str(txt)
    if larguras:
        for row in t.rows:
            for c, w in zip(row.cells, larguras):
                c.width = Cm(w)
    doc.add_paragraph()
    return t


def gerar(dados: dict, saida: str) -> list[str]:
    lacunas: list[str] = []
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Arial"
    estilo.font.size = Pt(11)
    for sec in doc.sections:
        sec.top_margin = sec.bottom_margin = Cm(2.5)
        sec.left_margin, sec.right_margin = Cm(3), Cm(2)

    # Capa
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(dados.get("titulo", "MEMORIAL DESCRITIVO"))
    r.bold, r.font.size = True, Pt(22)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(dados.get("obra") or FALTA)
    r.font.size = Pt(16)
    if dados.get("finalidade"):
        p = doc.add_paragraph(dados["finalidade"])
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for _ in range(8):
        doc.add_paragraph()
    p = doc.add_paragraph(dados.get("local_data") or FALTA)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_break(WD_BREAK.PAGE)

    n = 0

    # Identificação
    ident = dados.get("identificacao") or {}
    if ident:
        n += 1
        doc.add_heading(f"{n}. IDENTIFICAÇÃO", level=1)
        linhas = []
        for k, v in ident.items():
            if not v or FALTA in str(v):
                lacunas.append(f"Identificação: {k}")
            linhas.append([k, v or FALTA])
        tabela(doc, ["Campo", "Informação"], linhas, [5, 11])

    # Áreas
    areas = dados.get("areas") or []
    if areas:
        n += 1
        doc.add_heading(f"{n}. QUADRO DE ÁREAS", level=1)
        linhas = [[nome, area_fmt(v)] for nome, v in areas]
        tabela(doc, ["Descrição", "Área"], linhas, [11, 5])
        for nome, v in areas:
            if v in (None, "", FALTA):
                lacunas.append(f"Área: {nome}")

    # Seções técnicas
    for sec in dados.get("secoes", []):
        n += 1
        doc.add_heading(f"{n}. {sec.get('titulo', 'SEÇÃO').upper()}", level=1)
        for par in sec.get("texto", []):
            doc.add_paragraph(par).paragraph_format.first_line_indent = Cm(1.25)
            if FALTA in par or "a definir" in par.lower():
                lacunas.append(f"{sec.get('titulo')}: {par[:60]}…")
        for k, sub in enumerate(sec.get("subsecoes", []), 1):
            doc.add_heading(f"{n}.{k}. {sub.get('titulo', '')}", level=2)
            for par in sub.get("texto", []):
                doc.add_paragraph(par).paragraph_format.first_line_indent = Cm(1.25)
            for it in sub.get("itens", []):
                doc.add_paragraph(it, style="List Bullet")
        for it in sec.get("itens", []):
            doc.add_paragraph(it, style="List Bullet")
            if FALTA in it or "a definir" in it.lower():
                lacunas.append(f"{sec.get('titulo')}: {it[:60]}…")
        tab = sec.get("tabela")
        if tab:
            tabela(doc, tab["cabecalho"], tab["linhas"])
            for ln in tab["linhas"]:
                if any(FALTA in str(c) or "a definir" in str(c).lower() for c in ln):
                    lacunas.append(f"{sec.get('titulo')} (tabela): {' | '.join(map(str, ln))[:60]}…")

    # Assinatura
    rt = dados.get("responsavel") or {}
    doc.add_paragraph()
    p = doc.add_paragraph(dados.get("local_data") or FALTA)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for _ in range(3):
        doc.add_paragraph()
    for txt in ["_" * 45, rt.get("nome") or FALTA, rt.get("registro") or FALTA,
                rt.get("rrt") or FALTA, "Responsável Técnico"]:
        p = doc.add_paragraph(txt)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
    for campo in ("nome", "registro", "rrt"):
        if not rt.get(campo) or FALTA in str(rt.get(campo)):
            lacunas.append(f"Responsável técnico: {campo}")
    if not dados.get("local_data"):
        lacunas.append("Local e data")

    # Rodapé com numeração
    rodape = doc.sections[0].footer.paragraphs[0]
    rodape.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = rodape.add_run()
    for tipo, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tipo)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = txt
        run._r.append(el)

    doc.save(saida)
    return lacunas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json")
    ap.add_argument("--saida", default="Memorial_Descritivo.docx")
    a = ap.parse_args()
    dados = json.loads(Path(a.json).read_text(encoding="utf-8"))
    lacunas = gerar(dados, a.saida)
    print(f"Memorial gerado: {a.saida}")
    if lacunas:
        print(f"\nLacunas ({len(lacunas)}):")
        for l in lacunas:
            print(f"  - {l}")


if __name__ == "__main__":
    main()
