# Guia do painel — a página de resultados do modelo

**Para a Gi · Projeto Kenzie 360 · 11/09/2026**  
Complementa o `Review_Dashboard_11set.md`. Aqui está **exatamente** qual campo usar em cada gráfico.

---

## Antes de tudo: duas coisas mudaram desde o review

**1 · Eu te passei um campo que não existe.** No review eu listei `quintil` como presente nas duas
tabelas. **Não está** na `tb_score_lote_novo` — ela tem só sete colunas. O `quintil` existe apenas
na tabela do conjunto de teste. Erro meu.

**2 · Dois dos quatro gráficos não davam para montar como eu descrevi.** O gráfico de backtest
precisa de **duração** e **abandono**, e essas colunas não estão na `tb_score_risco` — elas moram
na `vw_wide_atendimento`. E o Pareto por assunto precisa de volume e taxa de falha agregados, que
também não estavam na gold.

Em vez de te pedir para cruzar fontes dentro do Looker — que é onde erro de *join* acontece —
o Ilan vai rodar um script que faz o cruzamento em SQL, uma vez. Depois disso você tem **três
fontes prontas**, e nenhum cálculo complicado a fazer.

> **Espere o Ilan confirmar que rodou o `14_cria_gold_painel.py`** antes de começar. Sem isso,
> a `vw_painel_modelo` não existe.

---

## As três fontes de dados a criar no Looker

Em **Recurso → Gerenciar fontes de dados adicionadas → Adicionar uma fonte de dados →
BigQuery**, projeto `kenzie-360-mba`, conjunto `kenzie360_gold`:

| Fonte | Linhas | Para quê |
|---|---|---|
| **`vw_painel_modelo`** | 7.712 | gráficos 1, 2 e 3 |
| **`tb_fila_correcao`** | 10 | gráfico 4 |
| **`vw_painel_lote_novo`** | 1.227 | página de monitoramento |

**Ao criar cada fonte, confira se as credenciais são do PROPRIETÁRIO**, não do visualizador. Se
forem do visualizador, o professor abre o relatório em branco.

### Os campos que você vai usar, e o que cada um é

Na `vw_painel_modelo`:

| Campo | O que é | Como usar |
|---|---|---|
| `faixa_operacional` | Baixo · **Medio** · Alto | dimensão dos gráficos 1 e 2 |
| `faixa_ordem` | 1, 2, 3 | **é só para ordenar** — nunca mostre na tela |
| `resolveu` | 1 quando a Kenzie resolveu | métrica com agregação **Média** = taxa de resolução |
| `falhou` | o inverso de `resolveu` | evite; use `resolveu`, que lê melhor |
| `quintil` | 1 a 5 | ordenação do gráfico 3 |
| `quintil_rotulo` | "1o quintil" … "5o quintil" | dimensão do gráfico 3 |
| `duracao_min` | duração da conversa em minutos | métrica com **Média** |
| `abandonou` | 1 quando o cliente desistiu na fila | métrica com **Média** = taxa de abandono |
| `risco` | a nota, 0 a 1 | opcional, para um cartão de nota média |

> ⚠️ **A faixa do meio é `Medio`, SEM acento**, nas três fontes. Se você filtrar ou escrever
> "Médio" em algum lugar, não retorna nada.

> ⚠️ **`faixa_ordem` existe justamente para não repetir o problema do eixo dos meses.** Sem
> ordenar por ela, o Looker devolve alfabético: Alto, Baixo, Medio. Sempre que `faixa_operacional`
> for dimensão, a ordenação é por `faixa_ordem` crescente.

---

## Gráfico 1 — Como a fila se distribui pelas três faixas

**O que ele mostra.** Que o modelo não produz um monte indistinto: ele parte a fila em três
grupos de tamanhos parecidos, e cada um pede uma ação diferente.

| Configuração | Valor |
|---|---|
| Tipo | **Gráfico de colunas** |
| Fonte | `vw_painel_modelo` |
| Dimensão | `faixa_operacional` |
| Métrica | `Contagem de registros` |
| Ordenação | `faixa_ordem` · crescente |

**Para mostrar a porcentagem:** clique na métrica, e em **Cálculo de comparação** escolha
**Porcentagem do total**. Se preferir ver o número absoluto e a porcentagem juntos, adicione a
métrica duas vezes — uma crua e uma com o cálculo de comparação.

**Confira antes de seguir:** Baixo **2.078** (26,9%) · Medio **3.098** (40,2%) · Alto **2.536**
(32,9%). Se não bater, pare e avise.

**Título sugerido:** *"Como o modelo parte a fila"*

---

## Gráfico 2 — A taxa de resolução em cada faixa

**O que ele mostra.** É **a prova de que o score separa**. Se a taxa de resolução fosse parecida
nas três faixas, o modelo não estaria dizendo nada. Ela cai quase três vezes da primeira para a
última.

| Configuração | Valor |
|---|---|
| Tipo | **Gráfico de colunas** |
| Fonte | `vw_painel_modelo` |
| Dimensão | `faixa_operacional` |
| Métrica | `resolveu` |
| Agregação da métrica | **Média** |
| Formato | **Porcentagem**, 1 casa decimal |
| Ordenação | `faixa_ordem` · crescente |

**Como trocar a agregação:** clique no campo da métrica dentro do gráfico → em **Agregação**
escolha **Média**. E em **Tipo**, escolha **Porcentagem**. Como `resolveu` é 0 ou 1, a média é a
proporção — o Looker mostra 0,475 como 47,5%.

**Confira:** **47,5%** · **27,6%** · **17,1%**.

**Título sugerido:** *"A Kenzie resolve menos conforme o risco sobe"*

---

## Gráfico 3 — O backtest por quintil

**O que ele mostra, e é o argumento mais forte da página.** Duração e abandono **não são
variáveis do modelo** — ele nunca as viu. Mesmo assim, as duas acompanham a nota. Isso significa
que o score está capturando algo real da conversa, e não decorando a base.

| Configuração | Valor |
|---|---|
| Tipo | **Gráfico combinado** (barras + linhas) |
| Fonte | `vw_painel_modelo` |
| Dimensão | `quintil_rotulo` |
| Métrica 1 — barra | `duracao_min` · agregação **Média** |
| Métrica 2 — linha | `abandonou` · agregação **Média** · formato Porcentagem |
| Métrica 3 — linha | `resolveu` · agregação **Média** · formato Porcentagem |
| Ordenação | `quintil` · crescente |

No painel de **Estilo**, marque a série 1 como **Barras** e as séries 2 e 3 como **Linha**. As
duas linhas são percentuais e a barra é em minutos — coloque as linhas no **eixo direito**.

**Confira, do 1º ao 5º quintil:**

| | 1º | 2º | 3º | 4º | 5º |
|---|---|---|---|---|---|
| Resolve | 50,7% | 33,8% | 26,9% | 21,0% | 15,2% |
| Duração média | 11,1 | 13,6 | 13,5 | 14,5 | 14,7 min |
| Abandono | 2,5% | 3,6% | 5,3% | 5,2% | 4,7% |

> **Honestidade obrigatória na legenda.** A resolução cai nos cinco degraus, limpo. Mas a duração
> **tem um platô** entre o 2º e o 3º (13,6 → 13,5) e o abandono **achata** no 5º (5,2 → 4,7).
> A ordenação existe e é clara, mas **não é degrau a degrau perfeita** — dizer "sem tropeço"
> seria exagero, e o professor confere.

**Título sugerido:** *"O modelo nunca viu duração nem abandono — e as duas acompanham a nota"*

---

## Gráfico 4 — O Pareto da fila de correção

**O que ele mostra.** É o gráfico que **vira recomendação de negócio**: onde investir primeiro.
Três assuntos concentram metade de toda a falha do semestre.

| Configuração | Valor |
|---|---|
| Tipo | **Gráfico combinado** |
| Fonte | **`tb_fila_correcao`** |
| Dimensão | `categoria_assunto` |
| Métrica 1 — barra | `falhas` · agregação **Soma** |
| Métrica 2 — linha | `acumulado` · agregação **Máximo** |
| Ordenação | `falhas` · **decrescente** |

**Atenção ao formato, e este detalhe engana.** `taxa_falha` e `acumulado` já estão na escala de
**0 a 100** (85,7 e não 0,857). Se você formatar como Porcentagem, o Looker multiplica por 100 e
sai 8.574%. **Formate como Número com 1 casa** e escreva "%" no título do eixo.

**Confira:** Bloqueio TED/PIX 3.801 falhas · Onboarding 3.681 · Câmbio 3.461, e o acumulado
chegando a **49,8%** no terceiro.

> **Cuidado com o rótulo.** Esses 49,8% são a participação nas **falhas**. Os documentos do
> projeto também citam **50,1%**, que é a participação nas **horas de espera** — outra conta,
> resultado parecido. Rotule pelo que o gráfico mostra: *"49,8% de todas as falhas"*.

**Título sugerido:** *"Três assuntos concentram metade da falha"*

---

## A página de monitoramento — um gráfico, dois lados

**O que ela mostra.** O modelo treinado até 10/08 pontuando a semana seguinte, que ele nunca viu.
O monitor de deriva **disparou** — e a mesma página mostra por quê.

**Não use mesclagem de dados.** Dois gráficos lado a lado, mesma configuração, fontes diferentes —
mais simples e sem risco de erro de cruzamento:

| | Gráfico da esquerda | Gráfico da direita |
|---|---|---|
| Fonte | `vw_painel_modelo` | `vw_painel_lote_novo` |
| Título | Histórico — 7.712 conversas | Lote novo — 1.227, última semana |
| Tipo | Colunas | Colunas |
| Dimensão | `faixa_operacional` | `faixa_operacional` |
| Métrica | Contagem, **% do total** | Contagem, **% do total** |
| Ordenação | `faixa_ordem` crescente | `faixa_ordem` crescente |

**Fixe o eixo Y dos dois de 0% a 50%**, em Estilo → Eixo Y → valores mínimo e máximo. Sem isso o
Looker escala cada um por conta e a comparação visual mente.

**Confira:**

| | Baixo | Medio | Alto |
|---|---|---|---|
| Histórico | 26,6% | 40,5% | 32,8% |
| Lote novo | 21,1% | 36,0% | **42,9%** |

> **A ressalva obrigatória, e ela não é opcional.** Uma semana, 1.227 conversas, base sintética.
> A faixa Alto sobe 10 pontos, **mas isso é artefato de base finita, não deriva real**: numa base
> que começa do zero em fevereiro, o contador de contatos anteriores só cresce, então qualquer
> fatia "última semana" parece mais reincidente. O mix de assuntos ficou estável — foi assim que
> se descobriu a causa.
>
> Sugestão de legenda: *"O monitor disparou (+10 pp na faixa Alto) e se autodiagnosticou:
> recorrência média 2,49 → 5,08, mix de assuntos estável. Artefato de base finita, não deriva de
> população. Uma semana, 1.227 conversas, base sintética."*

**Título da página:** *"Monitoramento — o modelo num lote que ele nunca viu"*

---

## Um cuidado que vale para a página inteira

Os gráficos desta página são sobre as **7.712 conversas do conjunto de teste** — não sobre as
36.000 da base, nem sobre as 31.042 demandas reais. São recortes diferentes, e o painel de
diagnóstico usa outro.

**Ponha isso escrito no topo da página**, uma linha:
*"Conjunto de teste: 7.712 conversas, de 3.375 clientes que o modelo nunca viu."*

Sem essa linha, alguém vai somar 2.078 + 3.098 + 2.536, achar 7.712, comparar com os 36.000 do
cartão da primeira página e perguntar o que está errado. Nada está — são recortes diferentes, e
dizer isso antecipadamente resolve.

---

## Ordem sugerida

1. Esperar o Ilan confirmar o `14_cria_gold_painel.py`
2. Criar as três fontes e conferir as credenciais de proprietário
3. Gráficos 1 e 2 — são os mais rápidos, e já provam que a fonte está certa
4. Gráfico 3 — o combinado, que dá mais trabalho de estilo
5. Gráfico 4 — outra fonte, cuidado com o formato 0–100
6. A página de monitoramento
7. A página 2 antiga: ou virou esta, ou precisa ser ocultada antes de compartilhar

**Qualquer número que não bater com os desta folha: pare e avise antes de seguir.** É mais barato
agora do que depois de o painel estar montado em cima dele.
