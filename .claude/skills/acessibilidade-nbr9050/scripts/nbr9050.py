#!/usr/bin/env python3
"""Verificações da ABNT NBR 9050:2020 para projeto residencial.

Subcomandos
  rampa   dimensiona ou confere rampa (tabela de inclinação × desnível × segmentos)
  escada  dimensiona ou confere escada (espelho, piso, Blondel, patamar)
  ifc     lê um modelo IFC e confere portas, lances de escada/rampa e sanitários

Situações: OK | NÃO CONFORME | VERIFICAR (dado ausente ou depende de leitura humana).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys

# (inclinação máx. %, desnível máx. por segmento m, nº máx. de segmentos ou None = sem limite)
RAMPAS = [(5.00, 1.50, None), (6.25, 1.00, None), (8.33, 0.80, 15)]
RAMPAS_REFORMA = [(10.00, 0.20, 4), (12.50, 0.075, 1)]
PATAMAR = 1.20


def m(v: float) -> str:
    return f"{v:.2f} m".replace(".", ",")


def pct(v: float) -> str:
    return f"{v:.2f}%".replace(".", ",")


def linha(item, exig, proj, sit):
    print(f"  {sit:<13} {item:<34} exigência: {exig:<28} projeto: {proj}")


# ---------------------------------------------------------------- rampa
def classe_rampa(i: float, reforma: bool):
    for lim, dmax, nmax in RAMPAS + (RAMPAS_REFORMA if reforma else []):
        if i <= lim + 1e-9:
            return lim, dmax, nmax
    return None


def dimensionar_rampa(h: float, i: float, dmax: float):
    segmentos = max(1, math.ceil(h / dmax - 1e-9))
    comp_rampas = h * 100 / i
    patamares_inter = segmentos - 1
    comp_total = comp_rampas + patamares_inter * PATAMAR
    return segmentos, comp_rampas, patamares_inter, comp_total


def cmd_rampa(a):
    h = a.desnivel
    print(f"\nRAMPA: desnível {m(h)}  (NBR 9050:2020, tabela de dimensionamento de rampas)\n")
    if a.inclinacao is None:
        print(f"  {'inclinação':<12}{'segmentos':>10}{'rampa (proj.)':>15}{'patamares int.':>16}{'total s/ patamares extremos':>30}")
        for lim, dmax, nmax in RAMPAS:
            s, cr, pi, ct = dimensionar_rampa(h, lim, dmax)
            obs = "" if nmax is None or s <= nmax else f"  ← excede {nmax} segmentos"
            print(f"  {pct(lim):<12}{s:>10}{m(cr):>15}{pi:>16}{m(ct):>30}{obs}")
        print(f"\n  + patamares de início e fim com {m(PATAMAR)} cada. Largura: mínimo 1,20 m, recomendável 1,50 m.")
        print("  Inclinação transversal: ≤ 2% (interna) / ≤ 3% (externa). Corrimão duplo a 0,92 m e 0,70 m nos dois lados.")
        return
    i = a.inclinacao
    c = classe_rampa(i, a.reforma)
    if c is None:
        teto = "12,50% (reforma)" if a.reforma else "8,33% (obra nova)"
        linha("Inclinação", f"≤ {teto}", pct(i), "NÃO CONFORME")
        return
    lim, dmax, nmax = c
    s, cr, pi, ct = dimensionar_rampa(h, i, dmax)
    linha("Inclinação", f"≤ {pct(lim)}", pct(i), "OK" if lim <= 8.33 else "VERIFICAR")
    linha("Desnível por segmento", f"≤ {m(dmax)}", f"{m(h / s)} ({s} segmento(s))", "OK")
    if nmax is not None:
        linha("Número de segmentos", f"≤ {nmax}", str(s), "OK" if s <= nmax else "NÃO CONFORME")
    linha("Comprimento (projeção)", "—", f"{m(cr)} de rampa + {pi} patamar(es) intermediário(s)", "OK")
    linha("Comprimento total", "—", f"{m(ct + 2 * PATAMAR)} incluindo patamares extremos", "OK")
    if lim > 8.33:
        print("  ! Inclinação acima de 8,33% só é admitida em REFORMA, esgotadas as alternativas.")
    if a.largura is not None:
        sit = "OK" if a.largura >= 1.50 else ("OK (mínimo)" if a.largura >= 1.20 else "NÃO CONFORME")
        linha("Largura livre", "≥ 1,20 m (recom. 1,50 m)", m(a.largura), sit)


# ---------------------------------------------------------------- escada
def avaliar_degrau(e: float, p: float):
    res = []
    res.append(("Espelho (e)", "0,16 a 0,18 m", m(e), "OK" if 0.16 - 1e-9 <= e <= 0.18 + 1e-9 else "NÃO CONFORME"))
    res.append(("Piso (p)", "0,28 a 0,32 m", m(p), "OK" if 0.28 - 1e-9 <= p <= 0.32 + 1e-9 else "NÃO CONFORME"))
    b = p + 2 * e
    res.append(("Blondel (p + 2e)", "0,63 a 0,65 m", m(b), "OK" if 0.63 - 1e-9 <= b <= 0.65 + 1e-9 else "NÃO CONFORME"))
    return res


def cmd_escada(a):
    H = a.altura
    print(f"\nESCADA: altura a vencer {m(H)}  (NBR 9050:2020)\n")
    nmin, nmax = math.ceil(H / 0.18 - 1e-9), math.floor(H / 0.16 + 1e-9)
    if nmin > nmax:
        print("  Nenhum número inteiro de espelhos cabe entre 0,16 e 0,18 m. Revise a altura.")
        return
    print(f"  {'espelhos':>9}{'e':>9}{'piso ideal (Blondel 0,64)':>28}{'faixa de piso válida':>24}{'projeção (lance reto)':>24}")
    for n in range(nmin, nmax + 1):
        e = H / n
        p_ideal = 0.64 - 2 * e
        lo, hi = max(0.28, 0.63 - 2 * e), min(0.32, 0.65 - 2 * e)
        faixa = f"{m(lo)} – {m(hi)}" if lo <= hi else "nenhuma"
        p_usar = min(max(p_ideal, 0.28), 0.32)
        print(f"  {n:>9}{m(e):>9}{m(p_ideal):>28}{faixa:>24}{m((n - 1) * p_usar):>24}")
    if H > 3.20:
        print(f"\n  ! Altura acima de 3,20 m: prever patamar intermediário (≥ 1,20 m na direção do movimento).")
    if a.piso is not None:
        n = a.espelhos or round(H / 0.17)
        e = H / n
        print(f"\n  Conferência com {n} espelhos e piso {m(a.piso)}:")
        for r in avaliar_degrau(e, a.piso):
            linha(*r)
    if a.largura is not None:
        sit = "OK" if a.largura >= 1.20 else "VERIFICAR"
        linha("Largura (rota acessível)", "≥ 1,20 m", m(a.largura), sit)
        if a.largura < 1.20:
            print("    (em casa unifamiliar a largura mínima costuma vir do código de obras municipal)")
    print("\n  Corrimão dos dois lados a 0,92 m e 0,70 m, prolongado 0,30 m; guarda-corpo ≥ 1,10 m (NBR 14718).")


# ---------------------------------------------------------------- ifc
MOLHADOS = re.compile(r"banh|wc|sanit|lavabo|toilet|bath|ducha", re.I)


def cmd_ifc(a):
    try:
        import ifcopenshell
        import ifcopenshell.util.element as ue
        import ifcopenshell.util.unit as uu
    except ImportError:
        sys.exit("Instale o ifcopenshell:  pip install ifcopenshell")
    f = ifcopenshell.open(a.arquivo)
    esc = uu.calculate_unit_scale(f)  # unidade do modelo → metros
    resultados = []

    def reg(cat, nome, item, exig, valor, sit, nota=""):
        resultados.append(dict(categoria=cat, elemento=nome, item=item, exigencia=exig,
                               projeto=valor, situacao=sit, nota=nota))

    def pavimento(el):
        c = ue.get_container(el) or ue.get_aggregate(el)  # IfcSpace fica agregado ao pavimento
        return c.Name if c is not None and getattr(c, "Name", None) else "—"

    def nome(el):
        return f"{el.Name or el.is_a()} ({pavimento(el)}) #{el.id()}"

    for d in f.by_type("IfcDoor"):
        w = d.OverallWidth * esc if d.OverallWidth else None
        h = d.OverallHeight * esc if d.OverallHeight else None
        if w is None:
            reg("Porta", nome(d), "Largura", "vão livre ≥ 0,80 m", "sem OverallWidth", "VERIFICAR")
        elif w < 0.80:
            reg("Porta", nome(d), "Largura", "vão livre ≥ 0,80 m", m(w), "NÃO CONFORME")
        elif w < 0.90:
            reg("Porta", nome(d), "Largura", "vão livre ≥ 0,80 m", m(w), "VERIFICAR",
                "largura total entre 0,80 e 0,90 m: o vão livre pode ficar abaixo de 0,80 m")
        else:
            reg("Porta", nome(d), "Largura", "vão livre ≥ 0,80 m", m(w), "OK")
        if h is not None:
            reg("Porta", nome(d), "Altura", "≥ 2,10 m", m(h), "OK" if h >= 2.10 - 1e-6 else "NÃO CONFORME")

    for s in f.by_type("IfcStairFlight"):
        ps = ue.get_psets(s).get("Pset_StairFlightCommon", {})
        e = getattr(s, "RiserHeight", None) or ps.get("RiserHeight")
        p = getattr(s, "TreadLength", None) or ps.get("TreadLength")
        if e and p:
            for item, exig, val, sit in avaliar_degrau(e * esc, p * esc):
                reg("Escada", nome(s), item, exig, val, sit)
        else:
            reg("Escada", nome(s), "Espelho/piso", "e 0,16–0,18; p 0,28–0,32", "não informado no modelo", "VERIFICAR")

    for r in f.by_type("IfcRampFlight"):
        ps = ue.get_psets(r).get("Pset_RampFlightCommon", {})
        ang = ps.get("Slope")
        largura = ps.get("ClearWidth")
        if ang is not None:
            # Slope é ângulo; heurística: < 0,3 → radianos, senão graus
            rad = ang if abs(ang) < 0.3 else math.radians(ang)
            i = math.tan(rad) * 100
            sit = "OK" if i <= 8.33 + 1e-6 else ("VERIFICAR" if i <= 12.5 else "NÃO CONFORME")
            nota = "acima de 8,33% só em reforma" if sit == "VERIFICAR" else ""
            reg("Rampa", nome(r), "Inclinação", "≤ 8,33% (obra nova)", pct(i), sit, nota)
        else:
            reg("Rampa", nome(r), "Inclinação", "≤ 8,33%", "Slope não informado", "VERIFICAR")
        if largura is not None:
            lw = largura * esc
            reg("Rampa", nome(r), "Largura livre", "≥ 1,20 m (recom. 1,50)", m(lw), "OK" if lw >= 1.20 else "NÃO CONFORME")

    for sp in f.by_type("IfcSpace"):
        rot = " ".join(filter(None, [sp.Name, getattr(sp, "LongName", None)]))
        if MOLHADOS.search(rot or ""):
            q = ue.get_psets(sp).get("Qto_SpaceBaseQuantities", {})
            area = q.get("NetFloorArea") or q.get("GrossFloorArea")
            val = f"{area * esc * esc:.2f} m²".replace(".", ",") if area else "área não informada"
            reg("Sanitário", f"{rot} ({pavimento(sp)}) #{sp.id()}", "Checklist sanitário acessível",
                "giro Ø1,50; transferência 0,80×1,20; barras; lavatório", val, "VERIFICAR",
                "conferir em planta com references/parametros.md")

    if not resultados:
        print("Nenhuma porta, escada, rampa ou sanitário encontrado no modelo.")
        return
    cont = {}
    for r in resultados:
        cont[r["situacao"]] = cont.get(r["situacao"], 0) + 1
    print(f"\nIFC: {a.arquivo}  (schema {f.schema}, unidade → m × {esc:g})")
    print("Resumo: " + ", ".join(f"{k}: {v}" for k, v in sorted(cont.items())) + "\n")
    ordem = {"NÃO CONFORME": 0, "VERIFICAR": 1, "OK": 2}
    for r in sorted(resultados, key=lambda r: (ordem.get(r["situacao"], 3), r["categoria"])):
        print(f"  {r['situacao']:<13} {r['categoria']:<10} {r['elemento'][:45]:<45} {r['item']:<20} {r['projeto']:<14} (exig.: {r['exigencia']})")
        if r["nota"]:
            print(f"  {'':<13} ↳ {r['nota']}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(resultados, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON salvo em {a.json}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rampa")
    r.add_argument("--desnivel", type=float, required=True, help="desnível total em metros")
    r.add_argument("--inclinacao", type=float, help="inclinação em %%")
    r.add_argument("--largura", type=float)
    r.add_argument("--reforma", action="store_true", help="admite inclinações de reforma (até 12,5%%)")
    r.set_defaults(func=cmd_rampa)
    e = sub.add_parser("escada")
    e.add_argument("--altura", type=float, required=True, help="altura total a vencer (piso a piso), m")
    e.add_argument("--piso", type=float, help="piso (pisada) pretendido, m")
    e.add_argument("--espelhos", type=int, help="número de espelhos pretendido")
    e.add_argument("--largura", type=float)
    e.set_defaults(func=cmd_escada)
    i = sub.add_parser("ifc")
    i.add_argument("arquivo")
    i.add_argument("--json", help="salvar resultados em JSON")
    i.set_defaults(func=cmd_ifc)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
