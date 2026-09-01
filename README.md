# Kenzie 360

**A camada de inteligência da V2 da Kenzie** — a assistente virtual de atendimento de um banco, com foco em clientes CDE (Conta de Domiciliado no Exterior, não residentes).

Projeto integrador do MBA em Engenharia de Dados da **Universidade Presbiteriana Mackenzie**, sob mentoria do Prof. Gustavo Ferreira.
**Grupo:** Ilan David Schapira · Giovanna Caetano Protti · Jonathas Borges

---

## O problema

A Kenzie V1 opera sem memória: cada conversa é tratada isoladamente e nenhuma vira conhecimento. O banco não enxerga padrões nas dores da própria base, e o atendimento humano absorve o que o bot não resolve.

A hipótese do projeto foi testada em três eixos e **confirmada nos três**:

| Eixo | Evidência |
|---|---|
| **(a)** O bot sabe informar, não sabe executar | Resolução cai de **45,9%** em demandas informacionais para **20,9%** em transacionais — e 47,7% de toda a demanda é transacional |
| **(b)** A operação depende cronicamente do humano | **11.106 horas humanas/ano** (6,3 FTE) para uma autonomia de 25,2%. Cada 10 p.p. de autonomia devolvem 1,3 FTE |
| **(c)** O próprio atendimento humano falha | **15,9%** dos casos que chegam ao humano terminam sem solução — e as 9 áreas internas falham na mesma proporção, o que aponta para o processo, não para nenhuma equipe |

**O que este projeto não é:** um bot novo. É o cérebro que o bot consulta — a camada que retém histórico, classifica intenção, estima risco de não resolução e devolve isso à operação.

---

## O que já está construído

| Camada | Estado |
|---|---|
| Data Lake medalhão no BigQuery (bronze → silver → gold) | Implementado — 11 views na gold, Star Schema e Wide Table |
| Análise exploratória e teste da hipótese | Concluída, com auditoria e revisão |
| Infraestrutura como código (Terraform) e CI/CD (GitHub Actions + Workload Identity Federation) | Implementado e exercitado de ponta a ponta |
| Modelo NLP — estágio 1, classificação de intenção | Treinado e avaliado |
| Modelo NLP — estágio 2, risco de não resolução | Teto medido; modelo a treinar |
| Ingestão incremental (Cloud Scheduler + Cloud Run Jobs) | Desenhada, a implementar |
| Dashboard no Looker Studio | Protótipo funcional |

---

## O modelo, e como ler os números

O modelo tem dois estágios. O estágio 1 classifica a intenção do cliente pela primeira mensagem. O estágio 2 estima o risco de a conversa terminar sem resolução.

| | Estágio 1 (entregue) | Estágio 2 (a construir) |
|---|---|---|
| Baseline (classe majoritária) | 14,48% | 74,77% |
| **Teto medido antes do treino** | **100,00%** | 76,88% como classificador · **AUC 0,750** como score de risco |
| Resultado obtido | **acurácia 99,99% · F1 macro 99,93%** | — |

**Por que medir o teto antes de treinar.** Sem essa referência, 99,99% pareceria um resultado extraordinário e 76% pareceria fraco. Medido o teto, a leitura se inverte: o estágio 1 é um problema fácil resolvido até o limite, e o estágio 2 estaria a 2,1 pontos percentuais do máximo teórico como classificador — inútil nesse formato, valioso como score de risco. É por isso que o número de manchete do estágio 2 será o **AUC**, e não a acurácia.

**Três defesas metodológicas** ([detalhes](1_documentos/sprint3/Features_e_Vazamento.md)):

1. **Divisão treino/teste por cliente, não por conversa.** Clientes reincidentes têm conversas parecidas; separar por conversa colocaria o mesmo cliente dos dois lados e inflaria o resultado. Zero sobreposição entre os 25.415 de treino e os 8.383 de teste.
2. **Vazamento bloqueado na origem.** `08_modelo_estagio1.py` carrega uma lista de 18 colunas proibidas e **aborta com erro fatal** se alguma chegar ao conjunto de treino.
3. **Alvo descartado por medição.** O candidato mais óbvio era classificar o motivo da transferência. A auditoria do gerador mostrou que esse campo é sorteado uniformemente entre 5 valores — teto de 20%, sinal zero. Descartado antes de qualquer treino.

---

## Como rodar

```bash
git clone https://github.com/MACK-Hand-on/MACK.git
cd MACK

pip install google-cloud-bigquery google-cloud-storage pandas scikit-learn joblib

# descompactar a base (ver 2_dados/LEIA-ME.md)
cd 2_dados/atual_v8 && gzip -dk *.gz && cd ../..

cd 3_pipeline
python3 00_teste_conexao.py          # valida credenciais e projeto
python3 01_carga_bronze.py           # Cloud Storage -> bronze
python3 02_cria_silver.py            # bronze -> silver
python3 03_eda.py                    # 16 consultas da análise
python3 03_eda.py 04_hipotese.sql    # os testes de hipótese
python3 06_cria_gold.py              # as 11 views da camada gold
python3 07_cria_star_schema.py       # modelo dimensional
python3 08_modelo_estagio1.py        # treina e avalia o estágio 1
```

Projeto e região saem de `3_pipeline/config_kenzie.py` (`kenzie-360-mba`, `us-central1`). Cada script valida a própria saída e falha alto se algo divergir.

---

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `1_documentos/` | Briefing consolidado (seções 1 a 12), arquitetura, EDA, definição de produto e memoriais técnicos, organizados por sprint |
| `2_dados/` | A base sintética comprimida e duas amostras em CSV aberto |
| `3_pipeline/` | Os scripts de ingestão, transformação, análise e modelagem — mais os DDLs em `sql/` |
| `4_gerador_da_base/` | O gerador do gêmeo estatístico (v7 e v8), o comparador entre versões e o QA |
| `5_resultados_eda/` | As 22 saídas das consultas, uma por análise |
| `6_dashboard/` | O protótipo do painel do Looker Studio, em PDF |
| `7_modelo/` | Métricas, predições do conjunto de teste e o modelo treinado |
| `infra/` | Terraform: módulo do Data Lake e ambientes dev e prod |
| `.github/workflows/` | A esteira que valida e aplica a infraestrutura |

Por onde começar: **`1_documentos/Briefing_Projeto_Kenzie360_Consolidado.pdf`** — o projeto inteiro em 26 páginas.

---

## Decisões que vale a pena ler

**A camada gold é feita de views, não de uma tabela grande.** São nove grãos distintos de agregação, e uma tabela por conversa não consegue produzir o que a jornada de sentimento exige (405.073 mensagens). Mais importante: a definição de cada métrica vive em um lugar só. Isso foi testado na prática — corrigir um denominador na gold acertou o dashboard sem que ninguém precisasse editá-lo.

**Um erro de denominador foi encontrado e corrigido.** A taxa de falha do atendimento humano era calculada sobre as conversas com área registrada — um conjunto que exclui três em cada cinco casos resolvidos. O número publicado estava inflado em 2,01×: 32,0% viraram **15,9%**. Duas conclusões caíram junto, e estão registradas como retratadas: "Cartões é a pior área" (X² = 14,86, gl = 8, **p = 0,062** — ruído amostral) e a tese dos "dois modos de falha" (artefato do mesmo denominador). Ver [Seção 10 do briefing](1_documentos/Briefing_Projeto_Kenzie360_Consolidado.pdf).

**Cloud Scheduler + Cloud Run Jobs em vez de Cloud Composer.** O Composer custa cerca de US$ 525/mês em operação contínua e não tem free tier. Ele permanece documentado como arquitetura-alvo para um ambiente bancário de produção, com o trade-off explicitado — a escolha é consciente, não uma limitação técnica.

**Workload Identity Federation em vez de chave de service account.** Não existe credencial de longa duração dentro do GitHub para vazar: o GCP confia numa identidade emitida pelo GitHub, e apenas para este repositório. Ver `infra/README.md`.

---

## Limitações declaradas

- **A base é sintética.** Reproduz a operação em nível agregado, mas o texto das mensagens é gerado a partir de templates — o desempenho do estágio 1 (99,99%) reflete essa regularidade e **não deve ser lido como expectativa para dados reais**.
- **A espiral de recorrência é uma premissa modelada**, com parâmetros publicados no gerador v8, não um achado empírico. Está declarada como tal na Seção 6.8.
- **O dashboard é um protótipo.** Dois ajustes de leitura estão mapeados e pendentes.

---

## Licença e uso

Trabalho acadêmico. A base não contém dado real de cliente e o nome do banco não é citado em nenhum artefato.
