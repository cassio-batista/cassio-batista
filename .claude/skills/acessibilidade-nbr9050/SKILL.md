---
name: acessibilidade-nbr9050
description: Verifica acessibilidade de projeto residencial pela ABNT NBR 9050 — rampas, escadas, portas, circulações, áreas de manobra, sanitário acessível e alturas de comandos. Lê modelos IFC, calcula rampas e escadas e gera relatório de conformidade. Use quando pedirem checagem de acessibilidade, NBR 9050, casa acessível, adaptável, para idoso ou cadeirante, rampa, escada, largura de porta, banheiro PCD ou desenho universal.
---

# Acessibilidade: NBR 9050

## Quando a norma é obrigatória

- **Edificação de uso coletivo ou público e áreas comuns de condomínios**: obrigatória.
- **Unidades de habitação multifamiliar**: a Lei 13.146/2015 (LBI, art. 58), regulamentada pelo Decreto 9.451/2018, exige unidades **adaptáveis**, e uma parte delas adaptada quando o comprador pedir. Confirme a versão vigente do decreto antes de afirmar percentuais.
- **Residência unifamiliar**: a norma não é obrigatória por lei federal, mas é a referência técnica para casa acessível ou para envelhecer em casa. Diga isso ao usuário e confira o código de obras do município, que pode exigir mais.

## Fluxo

1. Descubra o que existe: modelo **IFC** (melhor caso), **DXF/DWG**, imagem ou PDF da planta, ou só a descrição.
2. Rode as verificações automáticas que se aplicam, com `scripts/nbr9050.py`.
3. Percorra o checklist em `references/parametros.md` para o que o script não mede: sanitário, alcance, maçanetas e pisos.
4. Entregue o relatório no formato abaixo.

## Ferramenta: `scripts/nbr9050.py`

```bash
# Rampa: desnível em metros. Sem --inclinacao, mostra as opções da tabela da norma.
python scripts/nbr9050.py rampa --desnivel 0.45
python scripts/nbr9050.py rampa --desnivel 0.45 --inclinacao 6.25 --largura 1.20

# Escada: altura total a vencer (piso a piso). Calcula espelho, piso e Blondel.
python scripts/nbr9050.py escada --altura 2.88
python scripts/nbr9050.py escada --altura 2.88 --piso 0.28 --largura 1.10

# Modelo IFC: portas, lances de escada e rampa, ambientes molhados (requer ifcopenshell)
python scripts/nbr9050.py ifc projeto.ifc
python scripts/nbr9050.py ifc projeto.ifc --json relatorio.json
```

O script devolve `OK`, `NÃO CONFORME` ou `VERIFICAR` para cada item. `VERIFICAR` significa que o dado não está no modelo ou exige leitura humana, como o vão livre da porta, que é menor que a largura total do caixilho.

## Formato do relatório

```
## Acessibilidade NBR 9050: <nome do projeto>
Escopo: <unifamiliar | multifamiliar (unidade adaptável) | área comum>
Fonte dos dados: <IFC / DXF / planta / descrição>

| Item | Exigência | Projeto | Situação |
|------|-----------|---------|----------|
| Porta banheiro térreo | vão livre ≥ 0,80 m | 0,70 m | NÃO CONFORME |
...

### Correções sugeridas (em ordem de impacto)
### Itens que não puderam ser verificados
```

## Regras

- Cite a norma pelo número e pela versão consultada (NBR 9050:2020). Os valores em `references/parametros.md` foram compilados da norma. Se o usuário tiver a norma atualizada, ela prevalece. Nunca invente um valor que não esteja na referência: marque como "conferir na norma".
- Guarda-corpo segue a **NBR 14718** (altura mínima de 1,10 m), não a 9050.
- Piso tátil segue a **NBR 16537** e raramente se aplica dentro de casa.
- Verificação automática não substitui a responsabilidade técnica do arquiteto (RRT) ou do engenheiro (ART).
