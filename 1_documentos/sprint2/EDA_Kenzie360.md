# Análise Exploratória — Projeto Kenzie 360

**Sprint 2 · Trilha A · 24 de agosto de 2026**
Base: **v8** — 36.000 atendimentos e 405.073 mensagens · período de 17/02 a 17/08/2026
Fonte: camada `kenzie360_silver` no BigQuery · 22 consultas SQL versionadas em `sql/03_eda.sql` e `sql/04_hipotese.sql`

> **Versão da base.** Esta análise roda sobre a **v8** do gêmeo estatístico, recalibrada após a primeira rodada da EDA (ver `Calibracao_Gemeo_v8.md`). A v7 continua consultável no BigQuery nas tabelas com sufixo `_v7`. Todos os achados estruturais foram reconfirmados na base nova — a Seção 7 detalha o que mudou.

> **Sobre a origem dos dados.** A base é 100% sintética, construída como *gêmeo estatístico* da operação real e calibrada por indicadores agregados. Nenhum dado pessoal foi utilizado. Onde um resultado reflete limitação do gerador e não comportamento do negócio, isso está dito explicitamente na Seção 6.

---

## 1. A hipótese e o veredito

O projeto parte de uma tese sobre **por que** a Kenzie V1 não entrega:

> **(a)** O script do bot não resolve por conta própria — ele sabe informar, não sabe executar.
> **(b)** Por isso a operação depende cronicamente do atendimento humano.
> **(c)** E o próprio atendimento humano falha, porque a demanda circula entre áreas internas do banco.

A EDA testou os três eixos separadamente. **Os três se confirmam**, e o terceiro revela algo que a formulação original não previa.

| Eixo | Veredito | Evidência central |
|---|---|---|
| **(a)** O script não resolve sozinho | ✅ **Confirmado** | A resolução do bot cai de 45,9% em demandas informacionais para 20,9% em transacionais — 2,2× de queda. E 47,7% de toda a demanda é transacional |
| **(b)** Dependência crônica do humano | ✅ **Confirmado** | 11.106 horas humanas por ano (6,3 postos em tempo integral) para uma autonomia de apenas 25,2% |
| **(c)** O encaminhamento interno falha | ✅ **Confirmado, e é sistêmico** | Das 6.744 demandas encaminhadas a áreas internas, **32,0% voltam sem solução** — e as 9 áreas falham na mesma proporção |

A descoberta que refina a hipótese: **não existe uma área culpada**. Cadastro/Onboarding resolve 69,3%, Prevenção a Fraude 68,5%, Suporte Técnico 67,5%, Câmbio/Backoffice 66,3%. Todas ficam entre 64,0% e 69,6%. Quando o desempenho é uniformemente ruim, a causa não está em nenhuma equipe — está no desenho do processo de encaminhamento.

E a base v8 acrescentou um quarto achado que a v7 era incapaz de mostrar: **o cliente que insiste entra numa espiral**. A resolução cai de 29,9% no primeiro contato para 15,4% a partir do quinto, enquanto a insatisfação sobe de 22,0% para 36,6%. A Seção 7 trata disso.

---

## 2. Teste (a) — O script não resolve porque não pode agir

A classificação por assunto esconde o padrão. Reclassificando as demandas pelo **tipo de ação que exigem**, ele aparece:

| Tipo de demanda | Conversas | % do total | Bot resolve | Pede humano | Duração | CSAT |
|---|---:|---:|---:|---:|---:|---:|
| **Informacional** (só consultar) | 6.622 | 18,4% | **45,9%** | 37,0% | 11,6 min | 3,87 |
| **Misto** (consulta + ação leve) | 7.241 | 20,1% | **33,8%** | 45,0% | 12,8 min | 3,76 |
| **Transacional** (exige sistema) | 17.179 | 47,7% | **20,9%** | 54,4% | 14,4 min | 3,65 |

Quatro indicadores se movem juntos e na mesma direção. A resolução cai, o pedido de humano sobe, a conversa fica mais longa e a satisfação cai — monotonicamente, do informacional ao transacional.

**Vendo por categoria, a mesma coisa:** Saldo e Extrato 61,1% · Investimentos CDB 49,4% · Cartão de Crédito 36,2% · Onboarding 17,4% · **Bloqueio de TED/PIX 14,3%**.

**O que isso significa.** O problema da Kenzie V1 não é compreensão de linguagem. Ela entende o pedido — o que ela não tem é **permissão de escrita nos sistemas do banco**. Desbloquear um PIX, aprovar um documento, alterar um limite: todas exigem executar uma transação, e o bot só sabe devolver texto.

E aqui está o número que dimensiona o problema: **47,7% de toda a demanda é transacional**. Quase metade da operação chega pedindo algo que o script, por desenho, é incapaz de fazer.

**Consequência para a V2:** o ganho de automação não virá de treinar melhor o modelo de linguagem. Virá de **dar ao bot acesso transacional aos sistemas internos**, com as travas de segurança correspondentes. É decisão de arquitetura e de apetite a risco, não de NLP.

---

## 3. Teste (b) — O custo da dependência

| Indicador | Valor |
|---|---:|
| Autonomia atual do bot | **25,2%** |
| Duração média — bot | 5,2 min |
| Duração média — humano | 24,6 min |
| Horas humanas consumidas por ano | **11.106 h** = 6,3 FTE |
| Horas humanas **desperdiçadas** por ano | **1.756 h** = 1,0 FTE |

"Desperdiçadas" são as horas gastas em conversas que o humano atendeu por 24,5 minutos e mesmo assim não resolveu — o cliente saiu com CSAT 1,78.

### O que cada ponto de autonomia vale

O bot é 4,7× mais rápido que o humano **e** deixa o cliente mais satisfeito (CSAT 4,34 contra 4,19). Não há trade-off entre custo e qualidade nesta operação — automatizar melhora os dois.

| Cenário de autonomia | Ganho anual | Equivalente |
|---|---:|---:|
| +10 p.p. (25,2% → 35,2%) | 2.328 h | 1,3 FTE |
| Chegar a 40% | 3.445 h | 2,0 FTE |
| **Chegar a 50%** | **5.773 h** | **3,3 FTE** |
| Chegar a 60% | 8.101 h | 4,6 FTE |

**Este é o business case da V2 em uma linha:** cada 10 pontos percentuais de autonomia devolvem 1,3 posto de atendimento em tempo integral. E, pelo Teste (a), sabemos exatamente onde esses pontos estão — nos 47,7% de demanda transacional hoje bloqueada.

---

## 4. Teste (c) — O encaminhamento interno falha, e falha sistemicamente

### 4.1 Existem dois modos de falha, não um

| Caminho | Conversas | O que acontece |
|---|---:|---|
| **Sem motivo classificado** | 8.398 (56%) | **18,2% nunca são atendidas.** Mas quando são, resolvem em 100% dos casos |
| **Com motivo classificado** | 6.599 (44%) | **100% são atendidas.** Mas 32,9% voltam sem solução |

São falhas de natureza oposta, e confundi-las leva à ação errada:

- As **não classificadas** são casos simples — o humano resolve sempre que chega a atendê-los. O problema é de **roteamento**: sem motivo registrado, a demanda não sabe para qual fila ir, e 1.481 conversas se perdem.
- As **classificadas** chegam à área certa e ainda assim **um terço volta sem solução** — 2.158 conversas. O problema aqui não é roteamento, é **capacidade de resolução da área**.

Juntas, as duas falhas somam **3.639 conversas (10,1% da operação)** que consumiram atendimento e não entregaram nada.

### 4.2 Nenhuma área é a culpada

| Área interna | Recebidas | Resolveu | Atendeu e não resolveu | % resolvido | CSAT |
|---|---:|---:|---:|---:|---:|
| Cadastro/Onboarding | 1.653 | 1.146 | 507 | **69,3%** | 3,50 |
| Prevenção a Fraude | 1.163 | 797 | 366 | 68,5% | 3,48 |
| Câmbio/Backoffice | 1.044 | 692 | 352 | 66,3% | 3,44 |
| Suporte Técnico | 801 | 541 | 260 | 67,5% | 3,46 |
| Mesa de Limites | 751 | 523 | 228 | 69,6% | 3,41 |
| Cartões | 692 | 443 | 249 | **64,0%** | **3,29** |
| Investimentos | 359 | 245 | 114 | 68,2% | 3,35 |
| Backoffice | 228 | 158 | 70 | 69,3% | 3,54 |
| Atendimento PJ | 53 | 41 | 12 | 77,4% | 3,33 |
| **Total** | **6.744** | **4.586** | **2.158** | **68,0%** | — |

Excluindo Atendimento PJ (n=53, amostra pequena demais), as oito áreas restantes ficam entre **64,0% e 69,6%** — uma amplitude de 5,6 pontos percentuais.

**O que isso significa.** Se uma área resolvesse 90% e outra 40%, o problema seria de equipe — treinamento, dimensionamento, ferramenta. Mas todas resolvem em torno de 68%. Um desempenho uniformemente medíocre aponta para uma causa comum a todas: **o processo de encaminhamento em si**.

A leitura mais plausível é que a demanda chega à área sem o contexto necessário para ser resolvida de uma vez. O atendente recebe o caso, trabalha 24,4 minutos — a mesma duração de um caso resolvido — e ainda assim precisa devolver ou repassar.

Essas nove áreas consomem **5.516 horas por ano**, e um terço disso não produz resolução.

### 4.3 Cartões é a área com pior desempenho

64,0% de resolução e CSAT 3,29, o mais baixo entre as áreas com volume relevante (692 casos). Fica quase 6 pontos abaixo de Cadastro/Onboarding. Vale investigar se há causa específica — e é um dos poucos pontos em que a leitura mudou entre a v7 e a v8, o que sugere sensibilidade a ruído. Tratar como indicativo, não conclusivo.

---

## 5. Achados complementares

### 5.1 A satisfação é bimodal — o CSAT médio não descreve ninguém

| Desfecho | Conversas | CSAT |
|---|---:|---:|
| Pediu humano e não foi atendido | 1.526 | **1,62** |
| Abandonada pelo cliente | 6.141 | **1,69** |
| Humano atendeu e não resolveu | 2.172 | **1,78** |
| Encerrada sem resolução | 2.239 | **1,79** |
| Resolvida por humano | 11.299 | **4,19** |
| Resolvida pelo bot | 9.119 | **4,35** |

Não existe nenhum desfecho entre 1,79 e 4,09. A média de 3,72 é um artefato aritmético de dois grupos opostos.

**E daí:** o KPI de satisfação deve ser **"% de conversas no cluster de resolução"**, não CSAT médio. Uma meta de "subir o CSAT para 3,9" é, matematicamente, uma meta de mover conversas entre clusters — melhor declarar assim.

### 5.2 A conversa tem um vale no meio

| Quinto da conversa | Positivo | Neutro | Negativo |
|---|---:|---:|---:|
| 1º | 0,7% | 52,9% | 46,4% |
| 2º | 0,9% | 48,2% | 50,9% |
| **3º** | 0,5% | 45,0% | **54,5%** |
| 4º | 0,1% | 53,9% | 46,0% |
| **5º** | **38,4%** | 29,0% | 32,6% |

Do primeiro ao quarto quinto, o sentimento positivo nunca passa de 1%. O humor só vira no trecho final, quando o problema é (ou não é) resolvido. O pico de frustração está no **terço médio**, e na base v8 ele é ainda mais agudo: **54,5% das falas do 3º quinto são negativas** (era 45,3% na v7), porque os clientes reincidentes agora chegam mais irritados.

**E daí:** esperar o cliente pedir humano é esperar tarde demais. Um gatilho de escalada baseado em sentimento no 3º quinto é funcionalidade concreta para a V2 — e conecta diretamente com o Teste (a): é ali que o cliente percebe que o bot não vai conseguir agir.

### 5.3 Não há barreira de idioma — o que reforça que a falha é estrutural

| Idioma · segmento | Conversas | Bot resolve | Transferência | CSAT |
|---|---:|---:|---:|---:|
| EN · CDE | 10.073 | 24,9% | 41,9% | 3,73 |
| ES · CDE | 4.070 | 24,0% | 42,0% | 3,71 |
| PT · CDE | 10.935 | 24,7% | 41,7% | 3,69 |
| PT · Correntista Nacional | 9.678 | 27,4% | 40,6% | 3,74 |

A variação entre idiomas dentro do segmento CDE é de 0,9 ponto percentual.

**E daí:** este resultado **fortalece** a hipótese do projeto ao eliminar a explicação concorrente mais fácil. A Kenzie não atende mal porque o cliente é estrangeiro — ela atende igualmente mal em todos os idiomas e nos dois segmentos. A causa é o script e o encaminhamento, exatamente como a hipótese afirma.

**O que de fato distingue o cliente CDE é o produto:** Câmbio tem resolução de 25,8% e figura entre os piores CSAT da base (3,70), e é praticamente exclusivo desse público. Câmbio é demanda transacional pura.

*Nota:* na v7 havia um sinal de que clientes nacionais atendidos em inglês reabriam mais. Na v8 esse sinal desaparece (17,9% contra 17,4% dos atendidos em português), confirmando que era ruído de amostra pequena.

### 5.4 O sentimento inicial não prediz o desfecho

Cliente que abre a conversa irritado tem chance de resolução praticamente idêntica à de um cliente neutro.

**Uma exceção com poder preditivo real:** os 1.275 casos de opt-out/descadastro ocorrem **exclusivamente** entre clientes que iniciaram com sentimento negativo. Prever descadastro é viável; prever resolução a partir do humor inicial, não.

---

## 6. A espiral de recorrência — o que só a v8 consegue mostrar

Este achado não existia no relatório anterior. Não porque tenha passado despercebido, mas porque **a base v7 era incapaz de produzi-lo**: nela, o desfecho de uma conversa dependia apenas da categoria do assunto, e o histórico do cliente não entrava na conta. A v8 corrigiu isso, e o resultado é o achado de maior consequência para o negócio.

| Contatos prévios | Conversas | Reabertura | Bot resolve | Sentimento negativo | CSAT |
|---|---:|---:|---:|---:|---:|
| 0 (primeiro contato) | 15.000 | 0,0% | **29,9%** | 22,0% | **3,82** |
| 1 | 5.974 | 24,4% | 26,6% | 25,0% | 3,76 |
| 2 | 4.258 | 29,3% | 24,7% | 26,8% | 3,71 |
| 3 | 3.022 | 30,5% | 22,1% | 29,6% | 3,69 |
| 4 | 1.974 | 31,9% | 20,4% | 30,8% | 3,62 |
| 5 ou mais | 5.772 | **37,5%** | **15,4%** | **36,6%** | **3,54** |

*Na base v7, todas essas linhas eram estatisticamente indistinguíveis: resolução entre 24,3% e 25,8%, CSAT entre 3,67 e 3,83.*

**Todos os indicadores pioram juntos e de forma monotônica.** A resolução pelo bot cai pela metade — de 29,9% para 15,4%. A insatisfação sobe de 22,0% para 36,6%. E a taxa de reabertura sobe de 0% para 37,5%, o que fecha o ciclo: não resolver gera retorno, e retorno gera menos resolução ainda.

### 6.1 A comparação decisiva

| Situação da conversa | Conversas | Bot resolve | Negativo | CSAT |
|---|---:|---:|---:|---:|
| Primeiro contato do cliente | 15.000 | **29,9%** | 22,0% | **3,82** |
| Novo contato (o anterior resolveu) | 14.579 | 24,0% | 27,5% | 3,71 |
| **Reabertura** (o anterior não resolveu) | 6.421 | **17,2%** | **34,7%** | **3,57** |

Repare na linha do meio: mesmo o cliente cujo problema *foi* resolvido antes já volta com desempenho pior que o de um estreante. Voltar, por si só, já custa. E quando volta por falha — a reabertura — a resolução despenca para 17,2%, quase metade da do primeiro contato.

**E daí:** este é o argumento de urgência do projeto. Cada conversa não resolvida não custa apenas as suas próprias horas — ela produz um cliente que volta pior e é atendido pior. O custo de uma falha é maior que o custo daquela conversa, e a operação não enxerga isso hoje porque não mede o cliente ao longo do tempo, só ticket a ticket.

**Consequência direta para a V2:** o histórico de contatos precisa estar disponível **na abertura da conversa**, não descoberto no meio dela. Um cliente na terceira tentativa do mesmo assunto deveria entrar direto na fila humana, com contexto — não repetir a jornada do bot que já falhou duas vezes.

---

## 7. Limitações remanescentes da base

A recalibração da v8 (documentada em `Calibracao_Gemeo_v8.md`) resolveu três das cinco limitações levantadas na primeira rodada da EDA.

### 7.1 Corrigidas

| # | Limitação | Situação na v8 |
|---|---|---|
| **L1** | Volume diário plano (variação de 7,7%) | ✅ Variação de **30,6%**. Segunda-feira com 269 conversas em média contra 110 no domingo (2,4×). Picos de incidente e tendência de crescimento presentes |
| **L3** | 90% do volume no horário comercial de Brasília | ✅ Caiu para **76,3%**, e a madrugada dobrou para 10,1%. Clientes CDE agora se distribuem pelos fusos onde moram |
| **L5** | Reabertura sem efeito sobre o desfecho | ✅ Corrigida — é o achado da Seção 6 |

### 7.2 Remanescentes

**L2 — O canal de entrada é 100% WhatsApp.** Mantido de propósito: a operação real da Kenzie roda sobre Take Blip/WhatsApp, então o dado é fiel. Análises por canal continuam impossíveis, mas isso reflete a realidade, não um defeito do gerador.

**L4 — A regra de mascaramento não encontra PII.** Zero das 405.073 mensagens foram alteradas pelo regex aplicado na transição bronze→silver, porque a base já nasce mascarada por construção. A regra permanece implementada como rede de segurança para quando a origem for um export real, em que a garantia não existe.

### 7.3 Nota metodológica sobre a robustez dos achados

Todos os achados estruturais foram reconfirmados na base recalibrada:

| Achado | v7 | v8 |
|---|---|---|
| Gradiente informacional → transacional | 46,2% → 21,2% | 45,9% → 20,9% |
| Fila abandonada concentrada em transferências sem motivo | 1.528 previstas / 1.526 medidas | 1.478 previstas / 1.481 medidas |
| Falha uniforme entre áreas internas | ~67% | ~68% |
| Ausência de barreira de idioma | 0,9 p.p. de variação | 0,5 p.p. |
| CSAT bimodal | sim | sim |
| Ganho por 10 p.p. de autonomia | 2.326 h/ano | 2.328 h/ano |

Um achado que sobrevive a uma mudança na dinâmica interna da base é mais confiável do que um que só aparece numa versão. Esta tabela é evidência de robustez, e vale a pena levá-la à apresentação.

**O que mudou de leitura:** na v7, Atendimento PJ parecia a pior área (58,6%, CSAT 2,67); na v8 é Cartões (64,0%, CSAT 3,29). Ambos têm volume baixo, e a inversão mostra que a comparação entre áreas pequenas é sensível a ruído — trate como indicativo, não como ranking.

---

## 8. O que isso define para a camada gold

| View | Justificada por | Observação |
|---|---|---|
| `vw_autonomia_por_tipo_demanda` | Teste (a) | Informacional/misto/transacional é o corte que explica a operação |
| `vw_funil_e_modos_de_falha` | Teste (c) | Separa os dois modos: não roteado × roteado e não resolvido |
| `vw_desempenho_areas_internas` | Teste (c) | Por área: recebidas, resolvidas, devolvidas, horas consumidas |
| `vw_desfecho_e_custo` | 5.1, Teste (b) | Distribuição por cluster e horas por desfecho, no lugar do CSAT médio |
| `vw_jornada_sentimento` | 5.2 | Quintos da conversa |
| **`vw_espiral_recorrencia`** | **Seção 6** | **Promovida a prioridade.** Por faixa de contatos prévios: resolução, sentimento, reabertura, CSAT. Era inviável na v7 |
| `vw_dores_priorizadas` | Teste (a) | Ordena por dor composta (volume × insatisfação × custo) |
| `vw_features_nlp` | 5.4 | Sem variável alvo fixada (regra 5 do handoff) |

**Views do roadmap que os dados agora justificam:** `vw_kpi_diario` com série temporal volta a fazer sentido — com L1 corrigida, a série tem sazonalidade real, efeito de dia da semana e tendência. Deixa de ser ruído e passa a ser análise.

---

## 9. O que isso sugere para a Fase 4 (sem decidir nada)

A escolha do alvo continua com o grupo — a regra 5 do handoff permanece. Mas os dados ordenam as opções:

**Favorecida — prever risco de escalada na abertura.** *(Nova, e agora a mais forte.)* Pela Seção 6, o histórico de contatos prevê o desfecho com folga: 29,9% de resolução no primeiro contato contra 17,2% em reabertura. Um modelo que estime, na primeira mensagem, a probabilidade de a conversa falhar teria sinal forte e ação clara — encaminhamento direto ao humano com contexto.

**Favorecida — classificar o motivo de transferência.** 55,2% das transferências saem sem motivo, e é delas que vem a fila abandonada. Ataca a causa diagnosticada no Teste (c), com alvo bem definido.

**Favorecida — prever opt-out/descadastro.** Os 1.275 casos ocorrem exclusivamente entre clientes de sentimento inicial negativo, o que dá sinal limpo.

**Desfavorecida — prever resolução a partir do sentimento inicial isolado.** Por 5.4, o sinal é fraco quando a variável é usada sozinha.

---

## Anexo — Consultas e arquivos

Todas as consultas estão em `sql/03_eda.sql` (16, exploratórias) e `sql/04_hipotese.sql` (5, teste de hipótese), executáveis por `03_eda.py`. Resultados em `eda_resultados/`.

| Arquivo | Alimenta |
|---|---|
| `h1_informar_vs_executar.csv` | **Teste (a)** — Seção 2 |
| `h2_motivos_por_natureza.csv` | **Teste (c)** — Seção 4.1 |
| `h3_falha_por_area.csv` | **Teste (c)** — Seção 4.2 |
| `h4_custo_da_dependencia.csv` | **Teste (b)** — Seção 3 |
| `h5_reabertura_e_resolucao_primeiro_contato.csv` | Contexto de trajetórias |
| `h6_reabertura_causa_ou_consequencia.csv` | **Seção 6** — a espiral de recorrência |
| `a7_recorrencia.csv` | **Seção 6** — gradiente por contatos prévios |
| `a9_custo_por_desfecho.csv` | 5.1 |
| `a6_jornada_sentimento.csv` | 5.2 |
| `a8_barreira_idioma.csv` | 5.3 |
| `a6_sentimento_por_desfecho.csv` | 5.4 |
| `a3_dores_categoria.csv` · `a4_performance_bot.csv` | Seção 2 (detalhe por categoria) |
| `a2_volumetria_diaria.csv` · `a2_volumetria_hora_semana.csv` | L1, L3 |
| `a1_*.csv` · `a9_arquetipo_perfil.csv` | Contexto e L4 |

**Custo total de execução:** 89 MB varridos, 34 segundos, 0,008% da franquia mensal do BigQuery.

**Base:** v8 (`kenzie360_silver`). A v7 permanece consultável em `kenzie360_silver.atendimentos_v7` e `kenzie360_silver.mensagens_v7`.
