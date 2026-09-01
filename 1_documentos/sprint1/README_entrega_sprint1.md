# Projeto Kenzie 360 — Hands-On MBA Mackenzie (Engenharia de Dados)

Grupo: **Ilan David Schapira**, **Giovanna Caetano Protti** e **Jonathas Borges**.
Caso de uso: V2 da **Kenzie**, assistente virtual de atendimento aos correntistas
(foco no público CDE), com um "cérebro" analítico capaz de reter o histórico
conversacional e gerar insights de negócio.

## Conteúdo desta pasta

| Arquivo | Descrição |
|---|---|
| `Briefing_Projeto_Kenzie360_Sprint1.docx` | Briefing com as Seções 1 a 4 preenchidas. |
| `Fluxo_Conversacional_Kenzie360.md` | **Especificação do fluxo** (máquina de estados, desfechos, LGPD). |
| `Relatorio_RaioX_Base_Kenzie360.docx` | Relatório de qualidade de dados (46 checagens). |
| `gerar_dataset_cde.py` | Script que gera as duas bases (parametrizado no bloco `CONFIG`). |
| `dataset_kenzie360_atendimentos.csv` | **Conversas**: 36.000 linhas × 30 colunas. |
| `dataset_kenzie360_mensagens.csv` | **Mensagens** (histórico turno a turno): 404.092 linhas × 12 colunas. |
| `Arquitetura_Lambda_GCP.md` | Arquitetura Lambda na GCP (Batch/Speed/Serving). |
| `Justificativa_Stack_Tecnologica.md` | Justificativa da stack (GCP + Python/SQL + Looker Studio). |
| `qa_dataset.py` | Varredura automatizada de QA (46 checagens). |

## As duas tabelas

- **Conversas** (`..._atendimentos.csv`): uma linha por atendimento, com perfil do cliente
  (`segmento_cliente`, `arquetipo`, `idioma`), `origem` (Receptivo/Ativo), desfecho
  (`status_conversa`, `resolvida`), flags de transferência (`transferencia_iniciada`,
  `humano_atendeu`), triagem (`area_encaminhada`), recorrência (`contatos_previos`,
  `reabertura`), `csat` e a `transcricao_completa`.
- **Mensagens** (`..._mensagens.csv`): uma linha por turno, com `ordem`, `timestamp`,
  `remetente` (**Cliente / Kenzie / Atendente Humano**), `texto`, `sentimento`,
  `tipo_midia` e `contem_dado_mascarado`.

## Características da base

15.000 clientes distintos (39,9% com mais de um atendimento), 9 arquétipos de cliente,
3 idiomas (PT/EN/ES), 3 segmentos (CDE 70% · Nacional 27% · PJ 3%), mídia de WhatsApp
(texto/imagem/áudio) e 10 desfechos possíveis — incluindo abandono, opt-out e ruído.
O **sentimento é derivado do texto** das mensagens (sem *data leakage*).
O fluxo completo está descrito em `Fluxo_Conversacional_Kenzie360.md`.

## Natureza dos dados e LGPD

Base **100% sintética** (fictícia), construída como *gêmeo estatístico* da operação real
e calibrada com seus indicadores (resolução do bot ~25%, CSAT humano 3,8, WhatsApp como
canal do bot). **Nenhum dado pessoal ou registro real de cliente é utilizado.**
Reproduzindo um export real, dados que o cliente digitaria no chat aparecem **mascarados**
(`[CPF]`, `[TELEFONE]`, `[EMAIL]`, `[CONTA]`) e o `id_cliente` é pseudonimizado por hash.

## Como gerar as bases

```bash
pip install pandas numpy
python gerar_dataset_cde.py     # gera os dois CSVs
python qa_dataset.py            # roda as 46 checagens de qualidade
```

Todos os parâmetros de calibração (volume, mix de segmentos, arquétipos, taxa de
resolução, ruído, PII) ficam no bloco `CONFIG`, no topo do script.

## Stack
Cloud: Google Cloud Platform (Free Tier) · Linguagens: Python / SQL · Dataviz: Looker Studio
