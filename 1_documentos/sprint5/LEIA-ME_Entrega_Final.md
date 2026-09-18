# Kenzie 360 — Entrega Final

**MBA em Engenharia de Dados · Universidade Presbiteriana Mackenzie · 2026**
Ilan David Schapira · Giovanna Caetano Protti · Jonathas Borges
Orientação: Prof. Gustavo Ferreira

---

## O que é este projeto

O **Kenzie 360** é a camada de inteligência da assistente virtual de um banco. O caso de uso: o
Banco Kenzie atende pelo WhatsApp clientes **não residentes**, que mantêm no Brasil uma conta de
domiciliado no exterior (CDE). A assistente, **Kenzia**, funciona e não tem memória — cada conversa
começa do zero e nenhuma vira aprendizado.

O projeto não é um bot novo. É o cérebro que o bot consulta: uma camada que guarda o histórico por
cliente, estima **no minuto zero da conversa** a chance de a Kenzia não resolver, e publica essa nota
para a operação usar como ordem de fila.

> **A base é 100% sintética.** Foi gerada por script do próprio grupo, calibrada por indicadores
> agregados de uma operação real (volume, curva horária, capacidade da equipe). Nenhuma conversa de
> cliente real foi usada. O trabalho demonstra o **método**, não a magnitude.

---

## Onde está cada item do escopo

| Item do escopo (`MACK_HANDS_00.pdf`) | Onde está nesta entrega |
|---|---|
| **1 · Visão de negócio** | `2_documentos/Briefing_Projeto_Kenzie360_Consolidado.pdf` e `Definicao_Produto_MVP.md` |
| **2 · Storytelling + modelo preditivo** | `1_apresentacao/` · `2_documentos/Numeros_Oficiais_Modelo13.md` · `3_pipeline/09_modelo_risco_bot.py` |
| **3 · Boas práticas de governança** | `2_documentos/Item3_Governanca.md` |
| **4 · Arquitetura Lake / Lakehouse** | `2_documentos/Kenzie360_Arquitetura_Lambda_GCP_v2.pdf` · `3_pipeline/01_` a `06_` · repositório (`infra/`) |
| **5 · Trilhas de carreira e atuação dos perfis** | `2_documentos/Item5_Trilhas_de_Carreira.md` |

---

## Os números oficiais

A fonte única da verdade é `2_documentos/Numeros_Oficiais_Modelo13.md`. **Qualquer documento que
discorde dele está desatualizado.** Os principais:

| | |
|---|---|
| Base | 36.000 conversas · 405.073 mensagens · 17/02 a 17/08/2026 |
| População do modelo | **31.042** demandas reais (excluídos 4.958 de disparo ativo e ruído) |
| Treino / teste | 23.330 / 7.712 · separados **por cliente** · zero clientes em comum |
| Baseline / acurácia @0,50 | 70,5% / 72,8% |
| **AUC / Gini** | **0,6729** / 0,3457 |
| **Teto teórico da base** | **0,6736** → **99,6%** do sinal capturado |
| Faixas operacionais | Baixo 26,9% · Médio 40,2% · Alto 32,9% |
| Resolução por faixa | 47,5% · 27,6% · 17,1% |
| Espera evitável | 2.966 h no semestre · **1.142 h** encaminhando a faixa Alto |
| Custo dessa decisão | precisão 82,9% · 434 falsos alarmes |

O modelo foi **reproduzido em duas máquinas diferentes**, com resultado idêntico até a quarta casa
decimal.

---

## Estrutura do pacote

```
Entrega_Final_Kenzie360/
├── LEIA-ME_Entrega_Final.md        ← este arquivo
├── 1_apresentacao/                 deck da banca e roteiro
├── 2_documentos/                   briefing, os 5 itens do escopo, números e decisões
├── 3_pipeline/                     todos os scripts, em ordem de execução, + notebook
├── 4_modelo/                       coeficientes e scores publicados
├── 5_simulador/                    a demonstração do MVP (abre no navegador, sem servidor)
└── 6_painel/                       o painel no Looker Studio (PDF e link)
```

### Como rodar a pipeline, na ordem

Todos os scripts usam caminhos relativos e são idempotentes — podem rodar mais de uma vez.

| Ordem | Script | O que faz |
|---|---|---|
| 1 | `00_teste_conexao.py` | confere credencial e acesso ao projeto |
| 2 | `01_carga_bronze.py` | envia os CSVs ao Cloud Storage e carrega a bronze, acrescentando `_ingestion_ts` e `_source_file` |
| 3 | `02_cria_silver.py` | tipa, deduplica por chave de negócio e mascara |
| 4 | `06_cria_gold.py` | cria as views da camada gold |
| 5 | `09_modelo_risco_bot.py` | treina o modelo de 13 variáveis e grava o score |
| 6 | `09c_` / `09d_` | fila de correção por assunto e tempo até o humano |
| 7 | `10_lote_novo.py` | carga incremental e monitor de deriva |
| 8 | `11_` a `16_` | publicam score, painel e monitoramento na gold |

**Pré-requisitos:** Python 3, `pip install -r requirements.txt`, e
`gcloud auth application-default login`.

---

## O que este trabalho declara como limite

Está escrito em todos os documentos e foi dito na apresentação:

- **A base é sintética.** O projeto demonstra o método, não a magnitude que apareceria no banco.
- **O desgaste acumulado do cliente** (a autonomia caindo de 30,9% para 22,5%) é **premissa modelada
  no gerador**, publicada como parâmetro — não é achado empírico.
- **Os 27% de conversas que não chegam a ninguém** vêm de um parâmetro do gerador. Como a base
  escalona ~72% dos casos não resolvidos, 27% é piso, não teto.
- **A carga incremental foi demonstrada**, não posta em produção.
- **O retreino automático está desenhado**, não implementado.
- **O ambiente está descrito em Terraform**, com `plan` verde; o `apply` não foi executado. Os
  recursos foram criados no início do projeto e o Terraform os adota via `terraform import`.
- **Um modelo de NLP treinado sobre texto sintético aprende o padrão do gerador**, não o do cliente.
  Foi por isso que o texto livre não entrou no modelo, e é por isso que o classificador de intenção
  é o próximo passo, não parte desta entrega.

---

## Dois erros que corrigimos publicamente

Registrados porque fazem parte do método, não apesar dele.

**O classificador de 99,99%.** O primeiro modelo do projeto tinha 99,99% de acurácia. Ele lia o
assunto da conversa num texto que o próprio sistema havia escrito a partir do assunto — recuperava
uma resposta que já estava na tabela. O número era real e não significava nada. Foi descartado. A
regra que ficou: **quando o modelo acerta quase tudo, desconfie da variável.**

**O denominador dos 32%.** A taxa de falha do atendimento humano foi publicada como 32,0% com um
denominador que excluía três em cada cinco casos resolvidos. Corrigida para 15,9% — e **duas
conclusões que dependiam dela foram retratadas.**

---

## Repositório

O código-fonte, a infraestrutura como código e a esteira de CI/CD estão no repositório do projeto,
descrito em `2_documentos/Repositorio_GitHub.md`. O que está lá e não neste pacote:

- `infra/` — Terraform dos três datasets e do bucket, com módulo e ambientes
- `.github/workflows/` — a esteira que valida, simula e espera aprovação humana
- histórico de commits e pull requests das cinco sprints
