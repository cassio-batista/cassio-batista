---
name: memorial-descritivo
description: Redige o memorial descritivo de obra residencial (especificações técnicas por etapa: fundações, estrutura, vedações, cobertura, instalações, acabamentos) e gera o documento Word (.docx) com capa, quadro de áreas e campo de assinatura do responsável técnico. Use quando pedirem memorial descritivo, especificação técnica, caderno de encargos, descritivo de acabamentos ou memorial para prefeitura, banco ou financiamento.
---

# Memorial descritivo: residência

O memorial descreve **o que** será construído e **com quais materiais e padrões**. Ele acompanha o projeto na prefeitura, no financiamento (Caixa e bancos) e no contrato com a construtora. Precisa ser coerente com as pranchas e com o orçamento.

## 1. Colete os dados (pergunte o que faltar; não invente)

- **Identificação**: obra, finalidade (aprovação, financiamento, contratação), proprietário, endereço, matrícula/lote/quadra, município/UF.
- **Responsável técnico**: nome, CAU/CREA e número do RRT/ART.
- **Áreas**: terreno, construída por pavimento, permeável; taxa de ocupação e coeficiente de aproveitamento se exigidos.
- **Padrão de acabamento**: baixo, normal ou alto (classificação da NBR 12721 / CUB).
- **Sistemas construtivos**: fundação, estrutura, vedação e cobertura.
- **Fontes**: se houver modelo IFC, DXF, orçamento (skill `orcamento-sinapi`) ou lista de acabamentos do cliente, use. Leia o IFC com ifcopenshell para tirar ambientes, áreas, portas e janelas.

## 2. Estrutura

Siga `references/estrutura.md`, que lista as seções e o que especificar em cada uma. Para cada serviço informe:

- **material e especificação** (dimensão, classe ou resistência, acabamento);
- **norma aplicável** quando houver (ex.: concreto conforme NBR 6118, instalações elétricas conforme NBR 5410);
- **referência de marca** sempre com "ou equivalente técnico", para não restringir o fornecedor;
- **onde se aplica** (ambientes), de preferência numa tabela por ambiente para pisos, paredes e tetos.

Se houver orçamento SINAPI, o memorial precisa descrever os **mesmos** serviços. Aponte divergências ao usuário, não corrija sozinho.

## 3. Gere o .docx

Monte um JSON e rode `scripts/gerar_memorial.py` (requer `python-docx`):

```bash
python scripts/gerar_memorial.py memorial.json --saida Memorial_Descritivo.docx
```

Formato do JSON (exemplo completo em `references/exemplo.json`):

```json
{
  "titulo": "MEMORIAL DESCRITIVO",
  "obra": "Residência Unifamiliar",
  "finalidade": "Aprovação de projeto na Prefeitura de ...",
  "identificacao": {"Proprietário": "...", "Endereço": "...", "Lote/Quadra": "..."},
  "areas": [["Terreno", 360.0], ["Pavimento térreo", 142.5], ["Área permeável", 90.0]],
  "secoes": [
    {"titulo": "Fundações", "texto": ["parágrafo..."], "itens": ["item com marcador..."],
     "tabela": {"cabecalho": ["Ambiente", "Piso", "Rodapé"], "linhas": [["Sala", "Porcelanato 90x90", "Poliestireno 7 cm"]]}}
  ],
  "responsavel": {"nome": "...", "registro": "CAU A00000-0", "rrt": "RRT nº ..."},
  "local_data": "Cidade, dd de mês de aaaa"
}
```

O script numera as seções, cria a capa, o quadro de áreas com total e o bloco de assinatura. Depois de gerar, informe o caminho e liste as **lacunas** (dados que ficaram como "a definir").

## Regras

- Nunca preencha nome, registro profissional, RRT/ART ou matrícula com dados fictícios. Deixe `[a preencher]`.
- Linguagem técnica e impessoal ("será executado", "serão assentados").
- O memorial é de responsabilidade do RT, que revisa e assina. Diga isso ao entregar.
