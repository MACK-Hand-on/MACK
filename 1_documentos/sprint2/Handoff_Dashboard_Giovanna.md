# Protótipo do Dashboard — ponto de partida

**Projeto Kenzie 360 · Sprint 2 · Card 4**
Para: Giovanna · De: Ilan
Fonte de dados: `kenzie-360-mba.kenzie360_gold` (BigQuery, região `us-central1`)

---

## 1. Você já pode começar — e não depende de mais nada

A camada **gold está pronta**, com 9 views e uma dimensão. São elas que o Looker Studio consome. Não é preciso escrever SQL: cada view já entrega o dado agregado e pronto para arrastar.

**Acesso:** peça ao Ilan para incluir seu e-mail Google no IAM do projeto com os papéis *BigQuery Data Viewer* e *BigQuery Job User*.

---

## 2. O que cada view responde

| View | Pergunta de negócio | Onde usar |
|---|---|---|
| `vw_kpi_diario` | Como o atendimento evoluiu dia a dia? | Aba 1 — série temporal e KPIs de topo |
| `vw_espiral_recorrencia` | O cliente que insiste é pior atendido? | Aba 4 — **o achado mais forte da análise** |
| `vw_autonomia_por_tipo_demanda` | Por que o bot resolve pouco? | Aba 3 — evidência central da hipótese |
| `vw_funil_e_modos_de_falha` | Onde o atendimento vaza? | Aba 3 — funil |
| `vw_desempenho_areas_internas` | Quais áreas devolvem o caso sem resolver? | Aba 3 |
| `vw_desfecho_e_custo` | Quanto custa cada tipo de desfecho? | Aba 1 — cartões de custo |
| `vw_jornada_sentimento` | Em que ponto da conversa o cliente se frustra? | Aba 4 |
| `vw_dores_priorizadas` | Em qual dor investir primeiro? | Aba 2 — ranking |
| `vw_features_nlp` | (insumo da Fase 4, não vai ao dashboard) | — |
| `vw_dim_assunto` | Dimensão: classifica assunto por tipo de ação | Filtros |

---

## 3. Estrutura proposta — 4 abas

Sugestão, não regra. Se você enxergar melhor de outro jeito, discutimos.

### Aba 1 · Visão executiva  *(público: diretoria)*

Seis cartões no topo, período de 17/02 a 17/08/2026:

| KPI | Valor atual | Fonte |
|---|---:|---|
| Conversas no período | 36.000 | `vw_kpi_diario` |
| Autonomia do bot | 25,2% | `SUM(resolvidas_bot)/SUM(conversas)` |
| Resolução total | 56,9% | `SUM(resolvidas_total)/SUM(conversas)` |
| Fila abandonada | 4,1% | `SUM(fila_abandonada)/SUM(conversas)` |
| Horas humanas | 5.553 h | `SUM(horas_humanas)` |
| CSAT | 3,74 | `vw_desfecho_e_custo` |

Abaixo: série temporal de conversas por dia (linha) com a taxa de autonomia sobreposta.

> ⚠️ **Não use "CSAT médio" como indicador principal.** A satisfação é **bimodal**: quem tem o problema resolvido dá entre 3,94 e 4,34; quem não tem dá entre 1,75 e 1,87. Não existe nenhum desfecho no meio. Prefira mostrar **% de conversas resolvidas** e, se quiser o CSAT, quebre por cluster usando o campo `cluster` da `vw_desfecho_e_custo`.

### Aba 2 · Dores e produtos  *(público: produto)*

- Ranking de dores pela `vw_dores_priorizadas`, ordenado por `score_dor` (não por volume — volume sozinho aponta a prioridade errada)
- Mapa de calor: categoria × segmento, colorido por `pct_negativo`
- Recorte para CDB e cartão de crédito (nosso portfólio é só isso)

### Aba 3 · Performance da Kenzie  *(público: operação)*

- **Gráfico principal:** autonomia por tipo de demanda — informacional 45,9% → misto 33,8% → transacional 20,9%. Essa queda é a evidência da hipótese do projeto
- Funil do atendimento etapa a etapa (`vw_funil_atendimento`) — **atualizado em 28/08.** Substitui a antiga `vw_funil_e_modos_de_falha`, que separava as conversas por "com/sem motivo classificado" — recorte que a revisão da EDA identificou como artefato do gerador. A view antiga continua existindo e passou a repassar esta, então nada quebra; mas use o nome novo. São **contagens**: calcule taxas com `SUM(x)/SUM(y)`, nunca com a média de percentuais já prontos
- Tabela de áreas internas (`vw_desempenho_areas_internas`)

### Aba 4 · Cliente CDE e recorrência  *(público: estratégia)*

- **A espiral** (`vw_espiral_recorrencia`): resolução cai de 29,9% no primeiro contato para 15,4% a partir do quinto, enquanto a insatisfação sobe de 22,0% para 36,6%
- Jornada do sentimento pelos quintos da conversa — o pico de frustração está no 3º quinto (54,5% de falas negativas)
- Comparativo CDE × nacional

---

## 4. Como conectar o Looker Studio

1. Abra https://lookerstudio.google.com → **Criar** → **Fonte de dados**
2. Escolha o conector **BigQuery**
3. Projeto `kenzie-360-mba` → Dataset `kenzie360_gold` → escolha a view
4. **Conectar**

Repita para cada view que a aba precisar. Uma fonte de dados por view é o mais simples de manter.

---

## 5. Cuidados que economizam dinheiro e retrabalho

**Filtre sempre por data.** As tabelas de origem são particionadas por `data_ref`. Um filtro de período faz o BigQuery ler só as partições necessárias — sem ele, cada atualização do painel varre a base inteira. A franquia é de 1 TiB por mês e hoje o projeto usa menos de 0,1% dela, mas um painel sem filtro consome rápido.

**Ligue o cache do Looker Studio.** Em Configurações da fonte de dados, deixe a atualização em 12 horas. O dado é histórico e não muda.

**Não recrie cálculos que a view já traz.** Todos os percentuais já vêm prontos e conferidos. Refazer no Looker é onde os números começam a divergir do relatório.

---

## 6. Onde estão os números para conferir

O relatório `EDA_Kenzie360.md` (na pasta do projeto) traz todos os achados com os valores. Se algum número do painel não bater com ele, é sinal de erro na montagem — vale conferir antes de seguir.

**Base:** v8 do gêmeo estatístico (recalibrada — ver `Calibracao_Gemeo_v8.md`). A v7 continua consultável nas tabelas com sufixo `_v7`, caso queira comparar.

---

## 7. O que fica para a Sprint 4

Este card é **protótipo e especificação**. O painel definitivo no Looker Studio, com identidade visual e acesso para a área de negócio, é entrega da Sprint 4. Aqui o objetivo é validar quais visões contam a história certa.
