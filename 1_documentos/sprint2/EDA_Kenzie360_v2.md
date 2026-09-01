# Análise Exploratória — Projeto Kenzie 360

**Sprint 2 · Trilha A · 24 de agosto de 2026** · **revisão v2 em 28/08/2026 (Seções 1 e 4)**
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
| **(c)** O encaminhamento interno falha | ✅ **Confirmado** | **15,9%** dos casos atendidos por um humano terminam sem resolução, consumindo 1.770 h/ano — e outros **1.481 clientes** desistem na fila antes de serem atendidos |

A base não permite comparar o desempenho entre as áreas internas — a Seção 4.4 explica por quê e o que seria necessário para testá-lo. O que ela sustenta com solidez é o **tamanho** da perda, não a sua distribuição.

A base v8 acrescentou ainda uma **premissa modelada** que a v7 não continha — o atrito acumulado por recorrência. Ela não é um achado da análise, e sim uma estrutura introduzida de propósito no gerador; a Seção 6 declara os parâmetros e separa o que ela permite afirmar do que não permite.

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

## 4. Teste (c) — O encaminhamento interno falha, e a falha é uniforme

> **Nota de revisão (28/08/2026).** Esta seção foi reescrita. A primeira versão calculava a taxa de falha sobre as conversas com **área registrada**, e esse conjunto não é uma amostra imparcial: no gerador da base, o caso resolvido registra a área em apenas 40% das vezes, enquanto o caso não resolvido a registra sempre. O denominador excluía três em cada cinco sucessos e nenhum fracasso — o que inflava a taxa de falha em exatamente 2,01×. A seção abaixo refaz o cálculo sobre a base correta e revê as conclusões que dependiam dele. A auditoria que localizou o problema está documentada em `Decisoes_Sprint3.md`.

### 4.1 A taxa de falha do atendimento humano

O denominador correto é o conjunto de conversas em que **um atendente humano efetivamente assumiu o caso** — 13.567 conversas, e não as 6.744 que trazem área registrada.

| Indicador | Conversas |
|---|---:|
| Transferência iniciada | 15.048 |
| — cliente abandonou antes do atendimento | 1.481 |
| **Humano atendeu** | **13.567** |
| — resolveu | 11.409 |
| — **não resolveu** | **2.158** |

**15,9% dos casos que chegam ao atendimento humano terminam sem resolução.** São 2.158 conversas ao ano em que o cliente foi atendido, ocupou 24,4 minutos de um atendente — praticamente o mesmo tempo de um caso resolvido, 24,6 minutos — e saiu sem solução.

**O que isso significa.** Não há economia de esforço no fracasso: o caso que falha custa o mesmo que o caso que dá certo. São **1.770 horas por ano**, ou 15,8% de todo o tempo de atendimento humano, gastas em conversas que não produziram resolução.

### 4.2 A falha é uniforme entre as áreas

A área de destino é determinada pelo assunto da demanda, o que permite atribuí-la a todas as conversas atendidas — inclusive àquelas cujo registro de área ficou em branco.

| Área interna | Atendidas | Não resolvidas | % resolvido | Horas/ano | CSAT |
|---|---:|---:|---:|---:|---:|
| Cadastro/Onboarding | 3.322 | 507 | 84,7% | 2.750 | 3,85 |
| Prevenção a Fraude | 2.369 | 366 | 84,6% | 1.959 | 3,85 |
| Câmbio/Backoffice | 2.125 | 352 | 83,4% | 1.746 | 3,83 |
| Suporte Técnico | 1.585 | 260 | 83,6% | 1.302 | 3,80 |
| Mesa de Limites | 1.512 | 228 | 84,9% | 1.257 | 3,81 |
| Cartões | 1.358 | 249 | 81,7% | 1.116 | 3,74 |
| Investimentos | 719 | 114 | 84,1% | 594 | 3,75 |
| Backoffice | 473 | 70 | 85,2% | 388 | 3,90 |
| Atendimento PJ | 104 | 12 | 88,5% | 86 | 3,80 |
| **Total** | **13.567** | **2.158** | **84,1%** | **11.197** | — |

A amplitude é de 6,8 pontos percentuais, e ela **não sobrevive a um teste de significância**. Medido o desvio de cada área em relação à média geral, oito das nove ficam dentro de 1,25 desvio-padrão. A única exceção é Cartões, a 2,41 desvios — que, em nove comparações simultâneas, é o que se espera do acaso.

**Nenhuma área se distingue das demais.** A afirmação da versão anterior de que "Cartões é a área com pior desempenho" era ruído amostral e foi removida.

### 4.3 O limite do que esta base permite concluir

Vale ser explícito sobre por que a uniformidade aparece, porque a resposta é metodológica e não empírica.

No gerador do gêmeo estatístico, a probabilidade de o atendente humano resolver o caso é uma **constante única, igual para todas as áreas**. A taxa medida de 84,1% recupera essa constante com duas casas de precisão — o que é uma boa notícia sobre o método, já que o cálculo corrigido reproduz um parâmetro conhecido, e uma limitação clara sobre o alcance da conclusão.

**Portanto: esta base não permite testar se existe diferença de desempenho entre áreas internas.** Ela não foi construída com essa diferença. Afirmar que "o problema está no processo e não nas equipes" seria apresentar uma decisão de modelagem como descoberta empírica.

O que o Teste (c) sustenta, e sustenta bem:

- Uma parcela relevante do atendimento humano — **15,9%** — não produz resolução
- Esse fracasso custa o mesmo que o sucesso: **1.770 horas por ano**, 24,4 minutos por caso
- **1.481 clientes ao ano** pedem atendimento humano, entram na fila e desistem antes de serem atendidos

O terceiro item é o mais acionável dos três, e não depende de nenhuma hipótese sobre as áreas internas: é uma fila que perde 1.481 pessoas por ano.

### 4.4 O que esperar de uma base real

A uniformidade da Seção 4.2 é uma propriedade do gêmeo estatístico, não uma afirmação sobre a operação. **Na operação real, a expectativa é a oposta: que as áreas difiram, e de forma relevante.** As razões são estruturais e conhecidas de quem opera:

- **Dependência de terceiros.** Câmbio/Backoffice depende de contrapartes externas e de janelas de liquidação; Cadastro/Onboarding depende de fila de análise documental. Áreas cujo prazo não está sob controle próprio tendem a devolver mais.
- **Restrição regulatória.** Prevenção a Fraude opera sob regras que limitam o que pode ser resolvido no primeiro contato, por desenho e não por ineficiência.
- **Acesso a sistema.** O mesmo gradiente do Teste (a) — informacional contra transacional — vale dentro do banco: áreas sem permissão de escrita nos sistemas de origem dependem de uma terceira equipe para concluir.
- **Dimensionamento e maturidade.** Tamanho de equipe, rotatividade e tempo de treinamento variam entre áreas e afetam a taxa de resolução diretamente.

Nenhum desses fatores foi modelado no gêmeo, e é por isso que a base os apaga.

**A consequência prática é um requisito de captura de dado, não de análise.** O método da Seção 4.2 já está pronto para separar as áreas — ele só precisa que a área seja registrada em **100% dos encaminhamentos**, e não nos 40% de hoje. Registrar a área apenas quando o caso dá errado produz exatamente o viés que esta revisão corrigiu, e produziria o mesmo viés numa base real.

Esse é um requisito concreto para a V2, e um dos primeiros que a camada de inteligência deve impor à operação: **o encaminhamento só é válido com área e motivo preenchidos.** É barato de implementar no fluxo e é a diferença entre poder e não poder responder "qual área precisa de reforço" quando a pergunta vier.

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

## 6. O atrito acumulado — uma premissa modelada e dimensionada

> **Nota de revisão (28/08/2026).** Esta seção foi reescrita. A versão anterior apresentava o efeito da recorrência como *"o achado de maior consequência para o negócio"* e *"o argumento de urgência do projeto"*. Isso confundia premissa com evidência: o efeito não foi descoberto nos dados, foi **deliberadamente introduzido no gerador v8** para corrigir a limitação L5. O texto abaixo separa as duas coisas — o que a equipe assumiu, o que isso produz, e o que se pode legitimamente afirmar a partir daí.

### 6.1 A premissa, declarada

A EDA da v7 encontrou algo que não se sustenta sobre nenhuma operação real: **ser reabertura não mudava nada no desfecho**. Um cliente na quarta tentativa do mesmo problema era atendido exatamente como um estreante — resolução entre 24,3% e 25,8% em todas as faixas de recorrência, CSAT entre 3,67 e 3,83.

Isso não era um achado, era uma lacuna do gerador. A v8 a corrigiu introduzindo a premissa de que **o atrito acumula**, com parâmetros explícitos:

| Parâmetro | Valor | Efeito |
|---|---:|---|
| `atrito_por_contato` | 0,07 | Reduz a chance de resolução pelo bot em 7% a cada contato prévio (teto de 6) |
| `atrito_reabertura` | 0,18 | Redução adicional de 18% quando a conversa é reabertura |
| `atrito_piso` | 0,45 | A resolução nunca cai abaixo de 45% do valor base |
| `abandono_por_contato` | 0,10 | Eleva a chance de abandono em 10% a cada contato prévio |
| `abandono_reabertura` | 0,30 | Elevação adicional de 30% quando é reabertura |

Duas travas de calibração — `calib_p_bot = 1,185` e `calib_abandono = 0,80` — preservam os níveis **agregados** ancorados na operação real (resolução de 25,2%, abandono de 17,3%). O que a v8 mudou foi a distribuição interna, não os totais.

### 6.2 A magnitude que a premissa produz

| Contatos prévios | Conversas | Reabertura | Bot resolve | Sentimento negativo | CSAT |
|---|---:|---:|---:|---:|---:|
| 0 (primeiro contato) | 15.000 | 0,0% | **29,9%** | 22,0% | **3,82** |
| 1 | 5.974 | 24,4% | 26,6% | 25,0% | 3,76 |
| 2 | 4.258 | 29,3% | 24,7% | 26,8% | 3,71 |
| 3 | 3.022 | 30,5% | 22,1% | 29,6% | 3,69 |
| 4 | 1.974 | 31,9% | 20,4% | 30,8% | 3,62 |
| 5 ou mais | 5.772 | **37,5%** | **15,4%** | **36,6%** | **3,54** |

E o corte por trajetória:

| Situação da conversa | Conversas | Bot resolve | Negativo | CSAT |
|---|---:|---:|---:|---:|
| Primeiro contato do cliente | 15.000 | **29,9%** | 22,0% | **3,82** |
| Novo contato (o anterior resolveu) | 14.579 | 24,0% | 27,5% | 3,71 |
| **Reabertura** (o anterior não resolveu) | 6.421 | **17,2%** | **34,7%** | **3,57** |

A resolução cai pela metade entre o primeiro contato e a quinta tentativa. A reabertura resolve 17,2% contra 29,9% de um estreante.

**Estes números não são uma descoberta — são a consequência aritmética dos parâmetros da Seção 6.1.** O que eles entregam é a *magnitude*: quanto custaria o ciclo de atrito, caso ele tenha na operação real a intensidade que foi modelada aqui.

### 6.3 Por que a premissa é defensável

Não porque os dados a confirmem — eles não podem, já que foi a equipe quem a escreveu. E sim porque:

- **A alternativa é claramente falsa.** A v7 assumia atrito zero, e nenhuma operação de atendimento se comporta assim. Entre um modelo com atrito e um sem, o primeiro é mais fiel mesmo sem saber a intensidade exata.
- **Os níveis agregados continuam ancorados.** Resolução, abandono, transferência e CSAT permanecem calibrados contra os indicadores reais da operação, com desvio máximo de 0,3 p.p. A premissa redistribui, não inventa volume.
- **A direção é consensual, só a intensidade é incerta.** Que o cliente reincidente seja atendido pior é observação corrente de operação; o que não se sabe, sem dado real, é se a queda é de 7% ou de 3% por contato.

### 6.4 O que se pode e o que não se pode afirmar

**Pode:** que a análise dimensiona corretamente o custo do atrito dada a sua intensidade; e que o método detecta o efeito quando ele existe — o mesmo cálculo aplicado à v7 corretamente não encontrava nada, porque lá não havia nada.

**Não pode:** afirmar que a operação real da Kenzie apresenta esta magnitude. Medir isso exige a base real.

**E há um requisito que sobrevive independentemente da magnitude:**

> O histórico de contatos do cliente precisa estar disponível **na abertura da conversa**, e não ser descoberto no meio dela. Um cliente na terceira tentativa do mesmo assunto deveria entrar direto na fila humana, com contexto, em vez de repetir a jornada de bot que já falhou duas vezes.

Essa recomendação não depende de o atrito cair 7% ou 3% por contato. Depende apenas de ele existir e de a direção ser conhecida — e as duas coisas são verdadeiras em qualquer operação. É, também, o insumo direto do estágio 2 do modelo preditivo (Seção 9): `contatos_previos` e `reabertura` só têm valor como features se estiverem disponíveis no momento em que a conversa começa.

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
| Fila abandonada — escalou e desistiu antes do atendimento | 1.526 | 1.481 |
| Resolução do atendimento humano, uniforme entre áreas | 83,9% | 84,1% |
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
| `vw_funil_atendimento` | Teste (c) | ✅ **Revisada em 28/08.** Funil etapa a etapa: bot resolveu → pediu humano → desistiu na fila → humano atendeu → resolveu / não resolveu. A antiga `vw_funil_e_modos_de_falha` virou repasse desta |
| `vw_desempenho_areas_internas` | Teste (c) | ✅ **Revisada em 28/08.** Denominador passou a ser "o humano atendeu"; a área vem de `vw_dim_assunto.area_padrao` |
| `vw_desfecho_e_custo` | 5.1, Teste (b) | Distribuição por cluster e horas por desfecho, no lugar do CSAT médio |
| `vw_jornada_sentimento` | 5.2 | Quintos da conversa |
| **`vw_espiral_recorrencia`** | **Seção 6** | Por faixa de contatos prévios: resolução, sentimento, reabertura, CSAT. Dimensiona a premissa de atrito — ver a nota de revisão da Seção 6 |
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
