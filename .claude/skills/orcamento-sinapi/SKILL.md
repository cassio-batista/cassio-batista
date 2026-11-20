---
name: orcamento-sinapi
description: Monta orçamento de obra residencial com a tabela SINAPI da Caixa — busca composições e insumos por palavra-chave, lê planilhas de quantitativos e gera planilha orçamentária em Excel com etapas, BDI, totais por fórmula e curva ABC. Use quando pedirem orçamento, planilha orçamentária, custo da obra, composição SINAPI, preço de serviço, curva ABC, BDI ou "quanto custa construir".
---

# Orçamento com SINAPI

O SINAPI (Caixa/IBGE) é a referência oficial de custos da construção civil no Brasil. A Caixa publica os relatórios todo mês, por estado, em XLSX, em https://www.caixa.gov.br/sinapi. Esta skill **não baixa** a tabela: o site da Caixa costuma bloquear acesso automatizado. Peça ao usuário o arquivo do mês e do estado da obra.

## Antes de começar, confirme com o usuário

1. **Arquivo SINAPI**: mês de referência e UF. Pode ser o relatório de composições sintéticas, o de insumos ou o arquivo único "SINAPI_Referência" (formato novo, com colunas por UF).
2. **Desonerado ou não desonerado**: obra particular normalmente usa **não desonerado**. Se o arquivo tiver as duas versões, use a combinada.
3. **BDI**: obra residencial particular costuma ficar entre 20% e 30%. Se o usuário não informar, pergunte e não invente.
4. **Quantitativos**: planilha com etapa, código e quantidade. Se não houver, ajude a levantar a partir do projeto (IFC, DXF ou descrição) e deixe claro o que é estimativa.

## Ferramenta: `scripts/sinapi.py`

Requer `pandas` e `openpyxl` (instalados pela stack). O script detecta sozinho a linha de cabeçalho e as colunas de código, descrição, unidade e preço. O layout da Caixa muda com o tempo, por isso a detecção é automática. Se ela errar, use `--coluna-preco` e `--aba`.

```bash
# 1. Buscar composições e insumos por palavra-chave (todas as palavras precisam aparecer)
python scripts/sinapi.py buscar SINAPI_SP_2026_10.xlsx "alvenaria bloco ceramico 14" --uf SP
python scripts/sinapi.py buscar SINAPI_SP_2026_10.xlsx --codigo 103328

# 2. Gerar um modelo de planilha de quantitativos para preencher
python scripts/sinapi.py modelo quantitativos.csv

# 3. Montar o orçamento (aceita várias bases: composições + insumos)
python scripts/sinapi.py orcar quantitativos.csv \
    --base SINAPI_Composicoes_SP_2026_10.xlsx --base SINAPI_Insumos_SP_2026_10.xlsx \
    --uf SP --bdi 25 --obra "Residência Unifamiliar – Lote 12" \
    --data-base "10/2026 – SP – não desonerado" --saida orcamento.xlsx
```

A planilha de quantitativos (CSV ou XLSX) precisa das colunas `etapa`, `codigo` e `quantidade`. As colunas `descricao`, `unidade` e `custo_unitario` são opcionais e servem para itens fora do SINAPI, como cotações de mercado ou composições próprias. Quando `custo_unitario` vem preenchido, ele prevalece sobre o SINAPI.

### O que sai em `orcamento.xlsx`

- **Orçamento**: itens numerados por etapa (1.1, 1.2…), subtotal por etapa, custo unitário com BDI e total geral. Tudo em fórmulas, então editar uma quantidade recalcula a planilha.
- **Resumo por etapa**: valor e percentual de cada etapa, útil para o cronograma físico-financeiro.
- **Curva ABC**: itens ordenados por valor, com faixas A (até 80%), B (80% a 95%) e C.
- **Pendências**: códigos não encontrados na base. Nunca deixe um item sem preço passar em silêncio.

## Etapas típicas de uma residência

Use estas etapas na coluna `etapa`, nesta ordem, adaptando ao projeto:

1. Serviços preliminares (canteiro, locação, ligações provisórias)
2. Movimento de terra
3. Fundações
4. Estrutura (superestrutura)
5. Alvenaria e vedações
6. Cobertura
7. Impermeabilização
8. Instalações hidrossanitárias
9. Instalações elétricas e lógica
10. Esquadrias
11. Revestimentos de parede e teto
12. Pisos
13. Pintura
14. Louças, metais e acessórios
15. Serviços complementares e limpeza final

## Regras

- **Cite sempre a data-base** (mês/ano, UF, desoneração) no cabeçalho do orçamento e na resposta.
- SINAPI é **referência**, não preço de mercado. Para acabamentos de padrão médio/alto (porcelanatos, esquadrias de alumínio, metais), recomende cotação e marque esses itens como "cotação" na coluna de fonte.
- Não some custos de bases com datas ou UFs diferentes sem avisar.
- Se o usuário quiser estimativa paramétrica rápida (R$/m²), use o **CUB/m² do Sinduscon do estado** (NBR 12721) e deixe claro que é ordem de grandeza, não orçamento.
- Ao terminar, mostre o total, as 3 etapas mais caras e o caminho do arquivo gerado.
