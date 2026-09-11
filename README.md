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

## O que está construído

| Camada | Estado |
|---|---|
| Data Lake medalhão no BigQuery (bronze → silver → gold) | Implementado — 11 views na gold, Star Schema e Wide Table |
| Análise exploratória e teste da hipótese | Concluída, com auditoria e revisão |
| Infraestrutura como código (Terraform) e CI/CD (GitHub Actions + Workload Identity Federation) | Implementado e exercitado de ponta a ponta |
| Modelo — estágio 1, classificação de intenção | Treinado e avaliado |
| **Modelo — estágio 2, risco de não resolução** | **Congelado, avaliado e publicado na gold** |
| **Carga incremental com monitor de deriva** | **Demonstrada de ponta a ponta** |
| Agendamento da carga em produção (Cloud Scheduler + Cloud Run Jobs) | Desenhado, a implementar |
| Dashboard no Looker Studio | Protótipo funcional, consumindo a saída do modelo |

---

## O modelo, e como ler os números

O modelo tem dois estágios. O estágio 1 classifica a intenção do cliente pela primeira mensagem. O estágio 2 estima, **no momento em que a conversa abre**, o risco de ela terminar sem resolução pelo bot.

| | Estágio 1 | **Estágio 2** |
|---|---|---|
| Baseline (classe majoritária) | 14,48% | 70,5% |
| Teto medido antes do treino | 100,00% | **AUC 0,6736** |
| Resultado obtido | acurácia 99,99% · F1 macro 99,93% | **AUC 0,6729 · Gini 0,3457 · acurácia 72,8%** |
| Distância do teto | no limite | **99,6% do teto capturado** |

**Por que medir o teto antes de treinar.** Sem essa referência, 99,99% pareceria um resultado extraordinário e 0,6729 pareceria fraco. Medido o teto, a leitura se inverte: o estágio 1 é um problema fácil resolvido até o limite, e o estágio 2 captura **99,6% de todo o sinal que existe na base**. Por isso o número de manchete do estágio 2 é o **AUC**, e não a acurácia — que fica apenas 2,3 pontos acima do baseline e, sozinha, não diz nada.

**Como o teto foi obtido.** A linha 484 do gerador sorteia o desfecho da conversa com probabilidade que depende de três variáveis: assunto, contatos prévios e reabertura. Isso permite calcular o AUC de um modelo onisciente — um que conhecesse a fórmula do sorteio. Esse modelo daria 0,6736. O nosso dá 0,6729. O que falta não é modelo: é ruído irredutível.

> O teto de **0,750** publicado na Sprint 3 foi substituído. Aquele número era uma estimativa anterior ao alvo final e à depuração da população; o 0,6736 é derivado da fórmula do gerador, sobre a população já corrigida. Onde os dois aparecerem, **vale o 0,6736** — ver `1_documentos/` e a Ficha do Modelo.

**Um modelo mais complexo não melhora.** Foram testados sete: random forest (0,6684), árvores de profundidade 6 e 12, GBM e XGBoost padrão e regularizado. **Nenhum supera a regressão logística.** O limite não é o algoritmo, é a informação disponível na abertura da conversa.

**E três variáveis entregam o mesmo que treze.** Assunto, contatos prévios e reabertura sozinhos dão 0,6727, contra 0,6729 das treze. São exatamente as três que o gerador usa para sortear o desfecho — o teste de importância **redescobriu a fórmula do gerador sem conhecê-la**.

### O que o modelo devolve à operação

A saída não é uma classificação, é uma **nota de risco** entre 0 e 1, na mesma lógica de um score de crédito. Ela vira decisão em três faixas, cujos cortes são escolha de negócio tirada da capacidade real da operação — não da estatística:

| Faixa | Corte | % da fila | A Kenzie resolve |
|---|---|---|---|
| Baixo | < 0,65 | 26,9% | 47,5% |
| Médio | 0,65 – 0,80 | 40,2% | 27,6% |
| Alto | > 0,80 | 32,9% | 17,1% |

Médio + Alto somam 73,1% — praticamente os 73,8% que a operação já escalona hoje. **O modelo não pede mais gente: pede que a mesma fila seja atendida na ordem certa.**

O impacto medido, sobre o tempo que o cliente passa com a Kenzie antes de chegar a um humano: a faixa Alto concentra **1.142 das 2.966 horas** de espera evitáveis do semestre, com 82,9% de precisão.

---

## Carga incremental e monitoramento

`3_pipeline/10_lote_novo.py` segura a última semana da base, treina só com o histórico anterior e pontua o lote novo — que o treino nunca viu. É a demonstração do primeiro estágio do ciclo de aprendizado.

O monitor de deriva **disparou**: a faixa Alto saltou de 32,8% para 42,9% (+10,0 pp). E o script se autodiagnosticou: o mix de assuntos ficou estável, só a recorrência subiu (2,49 → 5,08 contatos médios). **Artefato de base finita, não deriva de população** — numa base sintética que começa do zero, o contador de contatos anteriores só cresce.

Daí saiu uma decisão de engenharia que vale registrar: *a referência de um monitor tem que ser um período comparável, não a base inteira desde o início.*

> **Atenção de leitura:** o AUC no lote novo é 0,7003, maior que os 0,6729 de referência. **Isso não é melhora.** O lote novo é mais fácil porque tem mais cliente reincidente, e recorrência é a segunda variável mais forte do modelo.

A mudança para carga incremental em produção é **uma linha** em `01_carga_bronze.py`: `WRITE_TRUNCATE` → `WRITE_APPEND`. A silver já deduplica por chave de negócio e a gold são views — nada mais precisa mudar.

---

## Duas tabelas na camada gold

O modelo entrega para o painel por duas tabelas, com os mesmos nomes de campo de propósito:

| Tabela | Linhas | Separação | Consumo |
|---|---|---|---|
| `kenzie360_gold.tb_score_risco` | 7.712 | por **cliente** | página de resultados do modelo |
| `kenzie360_gold.tb_score_lote_novo` | 1.227 | por **tempo** | página de monitoramento |

Publicadas por `11_carga_score_gold.py` e `13_carga_lote_novo_gold.py`. Os dois scripts conferem a distribuição das faixas contra os números oficiais depois de gravar, e avisam se divergir.

---

## Defesas metodológicas

1. **Divisão treino/teste por cliente, não por conversa.** Clientes reincidentes têm conversas parecidas; separar por conversa colocaria o mesmo cliente dos dois lados e inflaria o resultado. No estágio 2: 10.372 clientes no treino e 3.375 no teste, **zero em comum**.
2. **População depurada antes do treino.** Das 36.000 conversas, **4.958 são disparo ativo do banco e ruído** — nunca geram atendimento. Com elas dentro, o AUC subia para 0,703 separando "não é demanda", uma decisão que ninguém precisa de modelo para tomar. Ficam de fora: restam **31.042 demandas reais**.
3. **Vazamento bloqueado na origem.** `08_modelo_estagio1.py` carrega uma lista de 18 colunas proibidas e **aborta com erro fatal** se alguma chegar ao conjunto de treino. O estágio 2 usa apenas o que se conhece na abertura da conversa — nada de duração, número de mensagens ou desfecho.
4. **Alvo descartado por medição.** O candidato mais óbvio era classificar o motivo da transferência. A auditoria do gerador mostrou que esse campo é sorteado uniformemente entre 5 valores — teto de 20%, sinal zero. Descartado antes de qualquer treino.
5. **Backtest com variáveis que o modelo nunca viu.** Duração e abandono não são variáveis do modelo, e mesmo assim acompanham a nota: do quintil de menor risco ao de maior, a resolução cai de 50,7% para 15,2%.

Detalhes em [`1_documentos/sprint3/Features_e_Vazamento.md`](1_documentos/sprint3/Features_e_Vazamento.md).

---

## Como rodar

```bash
git clone https://github.com/MACK-Hand-on/MACK.git
cd MACK

pip install -r requirements.txt

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
python3 08_modelo_estagio1.py        # estágio 1 — classificação de intenção
python3 09_modelo_risco_bot.py       # estágio 2 — o modelo de risco, grava score_risco.csv
python3 09d_tempo_ate_humano.py      # as 2.966 h de espera evitáveis
python3 10_lote_novo.py              # carga incremental + monitor de deriva
python3 11_carga_score_gold.py       # publica tb_score_risco na gold
python3 13_carga_lote_novo_gold.py   # publica tb_score_lote_novo na gold
```

O `09_modelo_risco_bot.py` roda direto do CSV, sem GCP, em cerca de 10 segundos — é a forma mais rápida de reproduzir os números deste README. Os scripts `11_` e `13_` precisam de credencial no GCP.

**O notebook** `3_pipeline/Kenzie360_Modelo_Risco.ipynb` percorre o estágio 2 em 17 seções explicadas, lendo do BigQuery ou de CSV por um interruptor na primeira célula. É o caminho recomendado para entender o modelo.

**O simulador** `3_pipeline/simulador.html` abre no navegador com dois cliques — sem servidor e sem internet. Os 49 coeficientes estão embutidos, e a conta é a mesma do notebook. Em Câmbio, o mesmo cliente sai de 0,701 no primeiro contato para 0,848 na sexta volta: cruza de faixa sem que nada além do histórico mude.

Projeto e região saem de `3_pipeline/config_kenzie.py` (`kenzie-360-mba`, `us-central1`). Cada script valida a própria saída e falha alto se algo divergir.

---

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `1_documentos/` | Briefing consolidado (seções 1 a 12), arquitetura, EDA, definição de produto e memoriais técnicos, organizados por sprint |
| `2_dados/` | A base sintética comprimida e duas amostras em CSV aberto |
| `3_pipeline/` | Os scripts `00` a `13`, o notebook do modelo de risco, o simulador e os testes `prof2_*` — mais os DDLs em `sql/` |
| `4_gerador_da_base/` | O gerador do gêmeo estatístico (v7 e v8), o comparador entre versões e o QA |
| `5_resultados_eda/` | As 22 saídas das consultas, uma por análise |
| `6_dashboard/` | O protótipo do painel do Looker Studio, em PDF |
| `7_modelo/` | Métricas, predições do conjunto de teste e o modelo treinado |
| `infra/` | Terraform: módulo do Data Lake e ambientes dev e prod |
| `.github/workflows/` | A esteira que valida e aplica a infraestrutura |
| `docs/` | Proposta de esteira para a camada de aplicação |

Por onde começar: **`1_documentos/Briefing_Projeto_Kenzie360_Consolidado.pdf`** — o projeto inteiro em 26 páginas.

---

## Decisões que vale a pena ler

**A camada gold é feita de views, não de uma tabela grande.** São nove grãos distintos de agregação, e uma tabela por conversa não consegue produzir o que a jornada de sentimento exige (405.073 mensagens). Mais importante: a definição de cada métrica vive em um lugar só. Isso foi testado na prática — corrigir um denominador na gold acertou o dashboard sem que ninguém precisasse editá-lo.

**Um erro de denominador foi encontrado e corrigido.** A taxa de falha do atendimento humano era calculada sobre as conversas com área registrada — um conjunto que exclui três em cada cinco casos resolvidos. O número publicado estava inflado em 2,01×: 32,0% viraram **15,9%**. Duas conclusões caíram junto, e estão registradas como retratadas: "Cartões é a pior área" (X² = 14,86, gl = 8, **p = 0,062** — ruído amostral) e a tese dos "dois modos de falha" (artefato do mesmo denominador). Ver [Seção 10 do briefing](1_documentos/Briefing_Projeto_Kenzie360_Consolidado.pdf).

**O classificador de intenção com 99,99% foi despromovido a diagnóstico.** Quando perguntaram como chegamos nesse número, fomos verificar: o modelo lia o assunto a partir de um texto gerado por template — recuperava uma coluna que já existia na base. O número era real e não significava nada. Trocamos por um alvo que a base sustenta de verdade, com resultado bem mais modesto e defensável inteiro. **Regra que ficou: quando o modelo acerta quase tudo, desconfie da variável.**

**O texto livre foi testado e descartado por medição.** Só colunas: 0,665. Só o texto da primeira mensagem: 0,648. Os dois juntos: 0,662 — o texto **piora**. Ele não acrescenta nada porque a única coisa que informa é o assunto, que já é uma coluna. *(Medição feita sobre a versão de 12 variáveis; a conclusão não muda com 13.)*

**Cloud Scheduler + Cloud Run Jobs em vez de Cloud Composer.** O Composer custa cerca de US$ 525/mês em operação contínua e não tem free tier. Ele permanece documentado como arquitetura-alvo para um ambiente bancário de produção, com o trade-off explicitado — a escolha é consciente, não uma limitação técnica.

**Workload Identity Federation em vez de chave de service account.** Não existe credencial de longa duração dentro do GitHub para vazar: o GCP confia numa identidade emitida pelo GitHub, e apenas para este repositório. Ver `infra/README.md`.

---

## Limitações declaradas

- **A base é sintética.** Reproduz a operação em nível agregado, mas o texto das mensagens é gerado a partir de templates — o desempenho do estágio 1 (99,99%) reflete essa regularidade e **não deve ser lido como expectativa para dados reais**. O estágio 2 demonstra o método, não a magnitude: trocar por dados reais é trocar o arquivo de entrada, e a pipeline não muda.
- **A espiral de recorrência é uma premissa modelada**, com parâmetros publicados no gerador v8, não um achado empírico. Está declarada como tal na Seção 6.8.
- **A demanda que nunca chega a ninguém — 27% do total — vem de um parâmetro do gerador**, declarado como premissa e não como medição. O que a sustenta é observação de produção: o bot real não escalona sozinho.
- **A carga incremental foi demonstrada, não colocada em produção.** O agendamento não faz parte da entrega.
- **O dashboard é um protótipo.** Os ajustes de leitura pendentes estão mapeados.
- **Retreino automático não está implementado.** O ciclo está desenhado e o gatilho definido; a execução automática fica para depois.

---

## Licença e uso

Trabalho acadêmico. A base não contém dado real de cliente e o nome do banco não é citado em nenhum artefato.
