#!/usr/bin/env python3
"""Orçamento de obra com a tabela SINAPI (Caixa).

Subcomandos
  buscar  procura composições e insumos por palavras-chave ou por código
  modelo  cria uma planilha-modelo de quantitativos (CSV com ';', abre direto no Excel)
  orcar   monta o orçamento em XLSX: etapas, BDI, totais em fórmula, resumo e curva ABC

O layout dos relatórios da Caixa muda com o tempo; por isso o cabeçalho e as
colunas são detectados automaticamente. Use --aba e --coluna-preco se errar.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
    "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}


# ---------------------------------------------------------------- utilidades
def norm(texto) -> str:
    """Maiúsculas, sem acentos, espaços simples."""
    if texto is None or (isinstance(texto, float) and math.isnan(texto)):
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def numero(valor) -> float | None:
    """Converte '1.234,56', 'R$ 10,00', 12.5 etc. em float."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).replace("R$", "").replace("\xa0", "").strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def texto(valor) -> str:
    """Texto limpo; células vazias (None/NaN) viram ''."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    return str(valor).strip()


def codigo_limpo(valor) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    s = str(valor).strip()
    return s[:-2] if re.fullmatch(r"\d+\.0", s) else s


def arred(v: float) -> float:
    """Arredonda como o ROUND do Excel (meio para cima)."""
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def moeda(v: float | None) -> str:
    if v is None:
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- leitura da base
@dataclass
class Item:
    codigo: str
    descricao: str
    unidade: str
    preco: float | None
    tipo: str
    origem: str


def _detectar(df: pd.DataFrame, uf: str | None, coluna_preco: str | None):
    """Devolve (linha_dados, col_codigo, col_desc, col_unid, col_preco, tipo) ou None."""
    limite = min(40, len(df))
    for i in range(limite):
        linha = [norm(x) for x in df.iloc[i].tolist()]
        descs = [j for j, c in enumerate(linha) if c.startswith("DESCRI")]
        cods = [j for j, c in enumerate(linha) if "CODIGO" in c]
        if not descs or not cods:
            continue
        # código: prefira "CÓDIGO DA COMPOSIÇÃO"/"CÓDIGO DO INSUMO" a "CÓDIGO DA AGLUTINADA" etc.
        preferidos = [j for j in cods if "COMPOSI" in linha[j] or "INSUMO" in linha[j]]
        col_cod = preferidos[0] if preferidos else cods[0]
        # descrição: a primeira coluna "DESCRIÇÃO…" à direita do código (ignora "DESCRIÇÃO DA CLASSE")
        depois = [j for j in descs if j > col_cod]
        col_desc = depois[0] if depois else descs[0]
        unids = [j for j, c in enumerate(linha) if c.startswith("UNID") or c in {"UN", "UND"}]
        col_unid = unids[0] if unids else None
        cab = linha[col_cod] + " " + linha[col_desc]
        tipo = "Composição" if "COMPOSI" in cab else ("Insumo" if "INSUMO" in cab else "")

        col_preco, inicio = None, i + 1
        if coluna_preco:
            alvo = norm(coluna_preco)
            for k in range(i, min(i + 4, len(df))):
                hits = [j for j, c in enumerate(norm(x) for x in df.iloc[k].tolist()) if alvo == c or alvo in c]
                if hits:
                    col_preco, inicio = hits[0], k + 1
                    break
        elif uf:
            for k in range(i, min(i + 4, len(df))):
                hits = [j for j, c in enumerate(norm(x) for x in df.iloc[k].tolist()) if c == uf]
                if hits:
                    col_preco, inicio = hits[0], k + 1
                    break
        if col_preco is None and not coluna_preco:
            prioridade = ("CUSTO TOTAL", "PRECO MEDIANO", "CUSTO", "PRECO", "VALOR")
            for chave in prioridade:
                hits = [j for j, c in enumerate(linha) if chave in c and "%" not in c and "ORIGEM" not in c]
                if hits:
                    col_preco = hits[0]
                    break
        if col_preco is None:
            tem_uf = any(norm(x) in UFS for k in range(i, min(i + 4, len(df))) for x in df.iloc[k].tolist())
            motivo = "colunas por UF: informe --uf" if tem_uf else "coluna de preço não encontrada (use --coluna-preco)"
            return ("erro", motivo)
        return inicio, col_cod, col_desc, col_unid, col_preco, tipo
    return None


def carregar_base(arquivos: list[str], uf: str | None, aba: str | None = None,
                  coluna_preco: str | None = None, verboso: bool = True) -> dict[str, Item]:
    base: dict[str, Item] = {}
    uf = uf.upper() if uf else None
    for arq in arquivos:
        caminho = Path(arq)
        if not caminho.exists():
            sys.exit(f"Arquivo não encontrado: {arq}")
        abas = pd.read_excel(caminho, sheet_name=aba if aba else None, header=None, dtype=object)
        if isinstance(abas, pd.DataFrame):
            abas = {aba: abas}
        for nome, df in abas.items():
            if not aba and "ANALIT" in norm(nome):
                continue  # relatórios analíticos repetem códigos; use --aba se precisar deles
            det = _detectar(df, uf, coluna_preco)
            if det is None:
                continue
            if det[0] == "erro":
                if verboso:
                    print(f"  ! {caminho.name} [{nome}]: {det[1]}", file=sys.stderr)
                continue
            inicio, cc, cd, cu, cp, tipo = det
            n = 0
            for linha in df.iloc[inicio:].itertuples(index=False):
                cod = codigo_limpo(linha[cc])
                desc = linha[cd]
                if not cod or not isinstance(desc, str) or not desc.strip():
                    continue
                if not re.fullmatch(r"[A-Za-z0-9./_-]{2,20}", cod):
                    continue
                preco = numero(linha[cp])
                atual = base.get(cod)
                if atual is None or (atual.preco is None and preco is not None):
                    unidade = texto(linha[cu]) if cu is not None else ""
                    base[cod] = Item(cod, desc.strip(), unidade, preco, tipo, f"{caminho.name} [{nome}]")
                    n += 1
            if verboso and n:
                print(f"  • {caminho.name} [{nome}]: {n} itens ({tipo or 'tipo não identificado'})", file=sys.stderr)
    if not base:
        sys.exit("Nenhum item SINAPI reconhecido. Confira o arquivo, --aba, --uf ou --coluna-preco.")
    return base


# ---------------------------------------------------------------- buscar
def cmd_buscar(a):
    base = carregar_base([a.arquivo] + (a.base or []), a.uf, a.aba, a.coluna_preco)
    if a.codigo:
        achados = [base[c] for c in a.codigo if c in base]
        faltando = [c for c in a.codigo if c not in base]
    else:
        palavras = norm(" ".join(a.termos)).split()
        if not palavras:
            sys.exit("Informe palavras-chave ou --codigo.")
        achados = [it for it in base.values() if all(p in norm(it.descricao) for p in palavras)]
        faltando = []
    for it in achados[: a.limite]:
        print(f"{it.codigo:>10} | {it.tipo[:4]:4} | {it.unidade[:6]:6} | {moeda(it.preco):>14} | {it.descricao[:110]}")
    print(f"\n{len(achados)} resultado(s)" + (f", mostrando {a.limite}" if len(achados) > a.limite else ""))
    for c in faltando:
        print(f"Código não encontrado: {c}")


# ---------------------------------------------------------------- modelo
ETAPAS = [
    "Serviços preliminares", "Movimento de terra", "Fundações", "Estrutura",
    "Alvenaria e vedações", "Cobertura", "Impermeabilização", "Instalações hidrossanitárias",
    "Instalações elétricas", "Esquadrias", "Revestimentos de parede e teto", "Pisos",
    "Pintura", "Louças, metais e acessórios", "Serviços complementares e limpeza",
]


def cmd_modelo(a):
    linhas = ["etapa;codigo;quantidade;descricao;unidade;custo_unitario;fonte"]
    for e in ETAPAS:
        linhas.append(f"{e};;;;;;")
    linhas.append("Pisos;;45,0;Porcelanato 90x90 (cotação loja X);m2;189,90;Cotação")
    Path(a.saida).write_text("\n".join(linhas) + "\n", encoding="utf-8-sig")
    print(f"Modelo criado: {a.saida}  (separador ';', decimal com vírgula)")


# ---------------------------------------------------------------- orcar
def ler_quantitativos(caminho: str) -> pd.DataFrame:
    p = Path(caminho)
    if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        df = pd.read_excel(p, dtype=object)
    else:
        df = pd.read_csv(p, sep=None, engine="python", dtype=object, encoding="utf-8-sig")
    df.columns = [norm(c).lower().replace(" ", "_") for c in df.columns]
    falta = {"etapa", "codigo", "quantidade"} - set(df.columns)
    if falta:
        sys.exit(f"Faltam colunas em {caminho}: {', '.join(sorted(falta))}")
    return df


def cmd_orcar(a):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    bdi = a.bdi / 100 if a.bdi > 1 else a.bdi
    base = carregar_base(a.base, a.uf, a.aba, a.coluna_preco) if a.base else {}
    df = ler_quantitativos(a.quantitativos)

    etapas: dict[str, list[dict]] = {}
    pendencias = []
    for _, r in df.iterrows():
        etapa = texto(r.get("etapa")) or "Sem etapa"
        cod = codigo_limpo(r.get("codigo"))
        qtd = numero(r.get("quantidade"))
        if qtd is None or qtd == 0:
            continue  # linha vazia do modelo
        it = base.get(cod) if cod else None
        custo_proprio = numero(r.get("custo_unitario")) if "custo_unitario" in df.columns else None
        desc = texto(r.get("descricao"))
        unid = texto(r.get("unidade"))
        fonte_col = texto(r.get("fonte"))
        if custo_proprio is not None:
            custo, fonte = custo_proprio, fonte_col or "Própria"
        elif it is not None and it.preco is not None:
            custo, fonte = it.preco, fonte_col or "SINAPI"
        else:
            custo, fonte = None, fonte_col or ("SINAPI" if it else "?")
            pendencias.append((etapa, cod, desc or (it.descricao if it else ""),
                               "sem preço na base" if it else "código não encontrado"))
        etapas.setdefault(etapa, []).append({
            "codigo": cod, "fonte": fonte, "qtd": qtd, "custo": custo,
            "desc": desc or (it.descricao if it else "(descrição não encontrada)"),
            "unid": unid or (it.unidade if it else ""),
        })
    if not etapas:
        sys.exit("Nenhuma linha com quantidade na planilha de quantitativos.")

    wb = Workbook()
    ws = wb.active
    ws.title = "Orçamento"
    negrito = Font(bold=True)
    cinza = PatternFill("solid", fgColor="D9D9D9")
    amarelo = PatternFill("solid", fgColor="FFF2CC")
    fino = Side(style="thin", color="999999")
    borda = Border(left=fino, right=fino, top=fino, bottom=fino)
    num = "#,##0.00"

    ws["A1"] = "PLANILHA ORÇAMENTÁRIA"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"], ws["C2"] = "Obra:", a.obra or ""
    ws["A3"], ws["C3"] = "Data-base:", a.data_base or "(informe mês/ano, UF e desoneração)"
    ws["A4"], ws["C4"] = "BDI:", bdi
    ws["C4"].number_format = "0.00%"
    ws["A5"], ws["C5"] = "Gerado em:", date.today().strftime("%d/%m/%Y")
    for c in ("A2", "A3", "A4", "A5"):
        ws[c].font = negrito

    cab = ["Item", "Código", "Fonte", "Descrição", "Unid.", "Quant.", "Custo unit. (R$)",
           "Unit. c/ BDI (R$)", "Total (R$)"]
    LIN_CAB = 7
    for j, t in enumerate(cab, 1):
        c = ws.cell(LIN_CAB, j, t)
        c.font, c.fill, c.border = negrito, cinza, borda
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    linha = LIN_CAB + 1
    linhas_etapa = []
    resumo_py = []
    itens_abc = []
    for n_et, (etapa, itens) in enumerate(etapas.items(), 1):
        le = linha
        linhas_etapa.append((etapa, le))
        ws.cell(le, 1, str(n_et)).font = negrito
        ws.cell(le, 4, etapa.upper()).font = negrito
        for j in range(1, 10):
            ws.cell(le, j).fill = cinza
            ws.cell(le, j).border = borda
        linha += 1
        primeira = linha
        soma_et = 0.0
        for n_it, it in enumerate(itens, 1):
            r = linha
            vals = [f"{n_et}.{n_it}", it["codigo"], it["fonte"], it["desc"], it["unid"], it["qtd"], it["custo"]]
            for j, v in enumerate(vals, 1):
                ws.cell(r, j, v).border = borda
            ws.cell(r, 4).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(r, 6).number_format = "#,##0.000"
            ws.cell(r, 7).number_format = num
            ws.cell(r, 8, f"=ROUND(G{r}*(1+$C$4),2)").number_format = num
            ws.cell(r, 9, f"=ROUND(F{r}*H{r},2)").number_format = num
            ws.cell(r, 8).border = ws.cell(r, 9).border = borda
            if it["custo"] is None:
                for j in range(1, 10):
                    ws.cell(r, j).fill = amarelo
            else:
                unit_bdi = arred(it["custo"] * (1 + bdi))
                total = arred(it["qtd"] * unit_bdi)
                soma_et += total
                itens_abc.append((it["codigo"], it["desc"], it["fonte"], total))
            linha += 1
        c = ws.cell(le, 9, f"=SUM(I{primeira}:I{linha - 1})")
        c.number_format, c.font = num, negrito
        resumo_py.append((etapa, soma_et))

    ultima_item = linha - 1
    linha += 1
    soma_etapas = "+".join(f"I{le}" for _, le in linhas_etapa)
    ws.cell(linha, 4, "CUSTO DIRETO (sem BDI)").font = negrito
    ws.cell(linha, 9, f"=SUMPRODUCT(F{LIN_CAB + 1}:F{ultima_item},G{LIN_CAB + 1}:G{ultima_item})").number_format = num
    linha += 1
    ws.cell(linha, 4, "TOTAL GERAL (com BDI)").font = Font(bold=True, size=12)
    tot = ws.cell(linha, 9, f"={soma_etapas}")
    tot.number_format, tot.font = num, Font(bold=True, size=12)
    linha_total = linha

    for j, w in enumerate([7, 10, 10, 70, 7, 11, 15, 15, 16], 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = f"A{LIN_CAB + 1}"

    # Resumo por etapa
    rs = wb.create_sheet("Resumo por etapa")
    for j, t in enumerate(["Etapa", "Valor c/ BDI (R$)", "%"], 1):
        c = rs.cell(1, j, t)
        c.font, c.fill, c.border = negrito, cinza, borda
    for i, (etapa, le) in enumerate(linhas_etapa, 2):
        rs.cell(i, 1, etapa)
        rs.cell(i, 2, f"='Orçamento'!I{le}").number_format = num
        rs.cell(i, 3, f"=IF('Orçamento'!$I${linha_total}=0,0,B{i}/'Orçamento'!$I${linha_total})").number_format = "0.00%"
    fim = len(linhas_etapa) + 2
    rs.cell(fim, 1, "TOTAL").font = negrito
    rs.cell(fim, 2, f"=SUM(B2:B{fim - 1})").number_format = num
    rs.column_dimensions["A"].width, rs.column_dimensions["B"].width = 40, 20

    # Curva ABC (valores calculados na geração)
    abc = wb.create_sheet("Curva ABC")
    abc["A1"] = "Valores calculados na geração do arquivo. Gere de novo após alterar quantidades."
    abc["A1"].font = Font(italic=True, color="666666")
    for j, t in enumerate(["Código", "Descrição", "Fonte", "Total c/ BDI (R$)", "%", "% acumulado", "Classe"], 1):
        c = abc.cell(3, j, t)
        c.font, c.fill, c.border = negrito, cinza, borda
    total_py = sum(t for *_, t in itens_abc) or 1.0
    acum = 0.0
    for i, (cod, desc, fonte, t) in enumerate(sorted(itens_abc, key=lambda x: -x[3]), 4):
        perc = t / total_py
        classe = "A" if acum < 0.80 else ("B" if acum < 0.95 else "C")
        acum += perc
        for j, v in enumerate([cod, desc, fonte, t, perc, acum, classe], 1):
            abc.cell(i, j, v)
        abc.cell(i, 4).number_format = num
        abc.cell(i, 5).number_format = abc.cell(i, 6).number_format = "0.00%"
    abc.column_dimensions["B"].width, abc.column_dimensions["D"].width = 70, 18

    if pendencias:
        pd_ws = wb.create_sheet("Pendências")
        for j, t in enumerate(["Etapa", "Código", "Descrição", "Problema"], 1):
            c = pd_ws.cell(1, j, t)
            c.font, c.fill = negrito, amarelo
        for i, p in enumerate(pendencias, 2):
            for j, v in enumerate(p, 1):
                pd_ws.cell(i, j, v)
        pd_ws.column_dimensions["C"].width = 60

    wb.save(a.saida)

    total = sum(v for _, v in resumo_py)
    print(f"\nOrçamento gerado: {a.saida}")
    print(f"BDI: {bdi:.2%}   Itens: {sum(len(v) for v in etapas.values())}   Etapas: {len(etapas)}")
    print(f"TOTAL GERAL (com BDI): {moeda(total)}")
    print("Etapas mais caras:")
    for etapa, v in sorted(resumo_py, key=lambda x: -x[1])[:3]:
        print(f"  {etapa}: {moeda(v)} ({v / (total or 1):.1%})")
    if pendencias:
        print(f"\nATENÇÃO: {len(pendencias)} item(ns) sem preço — veja a aba 'Pendências' (linhas em amarelo).")


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def opcoes_base(p):
        p.add_argument("--uf", help="UF da coluna de preço (arquivos com colunas por estado)")
        p.add_argument("--aba", help="ler só esta aba da planilha")
        p.add_argument("--coluna-preco", help="nome (ou parte) do cabeçalho da coluna de preço")

    b = sub.add_parser("buscar", help="procura por palavras-chave ou código")
    b.add_argument("arquivo")
    b.add_argument("termos", nargs="*")
    b.add_argument("--base", action="append", help="arquivo SINAPI adicional")
    b.add_argument("--codigo", nargs="+")
    b.add_argument("--limite", type=int, default=30)
    opcoes_base(b)
    b.set_defaults(func=cmd_buscar)

    m = sub.add_parser("modelo", help="cria planilha-modelo de quantitativos")
    m.add_argument("saida", nargs="?", default="quantitativos.csv")
    m.set_defaults(func=cmd_modelo)

    o = sub.add_parser("orcar", help="gera o orçamento em XLSX")
    o.add_argument("quantitativos")
    o.add_argument("--base", action="append", help="arquivo SINAPI (repita para várias bases)")
    o.add_argument("--bdi", type=float, required=True, help="BDI em %% (ex.: 25)")
    o.add_argument("--obra", default="")
    o.add_argument("--data-base", default="")
    o.add_argument("--saida", default="orcamento.xlsx")
    opcoes_base(o)
    o.set_defaults(func=cmd_orcar)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
