# Documentos do Projeto Kenzie 360

Índice dos documentos versionados aqui, e a regra que decide o que entra.

## A regra

**No Git fica a fonte da versão válida.** Concretamente:

| entra | não entra |
|---|---|
| markdown, `.docx` e o `.pptx` do deck | PDF que é render de um markdown daqui |
| a versão atual de cada documento | versões superadas por uma posterior |
| documento que é entrega ou decisão | material de trabalho interno do time |

Os PDFs dos documentos vão no **pacote de entrega** (o zip do Moodle), não no
repositório: `mkpdf.py` os reconstrói a partir do markdown, e
`3_pipeline/17_organiza_entrega_final.py` monta o pacote inteiro.

    python mkpdf.py sprint5/Horas_Lote_Novo.md Kenzie360_Horas_Lote_Novo.pdf \
        "Kenzie 360 - Horas do lote novo"

Duas exceções, declaradas: o **`.pptx`** do deck é fonte (não tem markdown por
trás) e o **PDF do deck** não sai do `.pptx` sem PowerPoint — nenhum dos dois é
reproduzível a partir daqui, então os dois ficam.

## O briefing acadêmico

`Briefing_Projeto_Kenzie360_Consolidado.docx` — **é este o briefing válido.**
Reúne as seções 1 a 12 entregues ao longo das sprints 1, 2 e 3. O texto das
seções 5 a 12 é idêntico ao dos briefings originais de cada sprint; nas seções 1
a 4 há três pontos atualizados, e o próprio documento diz quais. Os briefings
por sprint saíram do repositório por isso — as versões entregues estão no
Moodle, com data.

## Por sprint

| documento | o que é |
|---|---|
| **sprint1** | |
| `Fluxo_Conversacional_Kenzie360.md` | desenho do fluxo de atendimento |
| `Justificativa_Stack_Tecnologica.md` | por que GCP, BigQuery, Looker |
| `Relatorio_RaioX_Base_Kenzie360.docx` | qualidade da base sintética — 46 de 46 checagens |
| **sprint2** | |
| `Calibracao_Gemeo_v8.md` | como a base sintética foi calibrada, e contra o quê |
| `Definicao_Produto_MVP.md` | o que a Kenzie 360 é, e o que ela explicitamente não é |
| `EDA_Kenzie360_v2.md` | análise exploratória — **a v2 é a válida** |
| `Modelagem_Camadas_BigQuery.md` | bronze, silver, gold: regra de cada camada |
| `Setup_GCP_Kenzie360.md` | como o ambiente na GCP foi construído |
| `Runbook_CICD_Kenzie360.md` | operação da esteira: rodar, conferir, reverter |
| `Memorial_CICD_Sprint2.md` | memorial da infraestrutura como código |
| **sprint3** | |
| `Ciclo_Aprendizado_Kenzie360.md` | o ciclo de aprendizado — a tese do projeto |
| `Kenzie360_Arquitetura_Lambda_GCP_v2.docx` | arquitetura Lambda na GCP — **a v2 é a válida** |
| **sprint5** | |
| `LEIA-ME_Entrega_Final.md` | índice do pacote de entrega final |
| `Item3_Governanca.md` | governança de dados |
| `Item5_Trilhas_de_Carreira.md` | trilhas de carreira |
| `Features_e_Vazamento.md` | quais colunas podem entrar no modelo, e por quê |
| `Horas_Lote_Novo.md` | a deriva do lote novo traduzida em horas de espera |
| `Kenzie360_Apresentacao.pptx` / `.pdf` | deck da banca de 17/09/2026 |

## O que não está aqui, de propósito

**Material de trabalho interno** — guias de painel escritos para uma pessoa do
time, handoffs, revisões internas, roteiros de apresentação, briefs de reunião.
É processo, não produto: fica na pasta do projeto, fora do Git.

**Versões superadas.** Quando um documento é revisado, a versão anterior sai. O
registro do que foi entregue em cada data está no Moodle, não aqui — o
repositório guarda o estado válido, com o histórico de commits contando como
chegou nele.

**Os números do modelo** estão em `Numeros_Oficiais_Modelo13.md`, dentro do
pacote de entrega. Qualquer documento que discorde dele está desatualizado.
