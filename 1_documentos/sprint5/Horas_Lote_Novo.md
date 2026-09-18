# A deriva traduzida em horas — o lote novo

**15/09/2026.** Resultado novo, medido hoje. Responde à pergunta do Ilan: *"não conseguimos mostrar
os resultados do lote novo em tempo de horas ganhas para os clientes?"*

Conseguimos — e com tempo real de cada conversa, não com média aplicada por cima.

---

## Como a conta é feita

O `09d_tempo_ate_humano.py` já calcula, para cada conversa, o **`min_ate_humano`**: o intervalo
entre a primeira mensagem do cliente e a primeira fala do atendente. É o tempo que a pessoa passa
com a Kenzie **antes** de falar com um humano — não a duração total do atendimento.

São 13.567 conversas no semestre, média de 13,1 min, total de 2.966 h. É a base da conta de espera
evitável do Caso de Negócio.

O `16_horas_lote_novo.py` cruza esse tempo com as duas populações pontuadas pelo modelo e devolve
as horas por faixa de risco.

**A coluna que importa é `horas_por_1000`**: horas de espera a cada mil conversas que entram na
fila. Sem ela a comparação seria 744 h contra 120 h — números de populações de tamanhos diferentes,
que não dizem nada.

---

## Os números

### Espera evitável, a cada 1.000 conversas da fila

| | Baixo | Médio | **Alto** | Total |
|---|---|---|---|---|
| **Histórico** — 7.712 conversas | 20 h | 39 h | **37 h** | 96 h |
| **Lote novo** — 1.227, última semana | 15 h | 33 h | **50 h** | 98 h |
| Variação | −5 h | −6 h | **+13 h (+35%)** | +2 h |

### O que sustenta cada linha

| | Histórico | Lote novo |
|---|---|---|
| conversas que chegam a um humano | 3.414 (44,3%) | 550 (44,8%) |
| espera total medida | 744 h | 120 h |
| tempo médio de menu | 13,1 min | 13,1 min |
| precisão da faixa Alto | 82,9% | **86,3%** |
| falsos alarmes na faixa Alto | 434 | 72 |

---

## A leitura — e é melhor do que parecia

**A espera total praticamente não mudou: 96 h → 98 h por mil conversas.** O que mudou foi **onde**
ela está. Treze horas migraram das faixas Baixo e Médio para a faixa Alto.

Ou seja: a fila não ficou mais lenta. Ela ficou **mais concentrada** — e concentrada exatamente no
grupo que o modelo manda encaminhar primeiro.

Três consequências, e as três são boas para a defesa:

1. **A política de encaminhar a faixa Alto rende mais nessa semana:** devolve 50 h por mil
   conversas, contra 37 h no histórico. Mesmo esforço operacional, 35% mais espera devolvida.
2. **Com menos gente incomodada à toa:** a precisão da faixa Alto subiu de 82,9% para 86,3%.
   O trade-off melhorou nas duas pontas.
3. **O monitor deixa de ser abstrato.** "A faixa Alto subiu 10 pontos" é uma frase de cientista de
   dados. "Treze horas de espera a cada mil conversas migraram para o grupo de maior risco" é a
   mesma coisa em linguagem de operação.

### Consistência com os números oficiais

As 284 h da faixa Alto no conjunto de teste, escaladas pelo fator de 4,03 (teste → semestre), dão
1.145 h — contra as **1.142 h** publicadas no `Numeros_Oficiais_Modelo13.md`. A diferença é
arredondamento do fator. **O método reproduz o número oficial**, o que é a melhor evidência de que
a conta nova está certa.

---

## As ressalvas, que continuam valendo

- **Uma semana, 1.227 conversas, base sintética.** Nada aqui é projeção anual.
- **O lote novo é mais fácil** por ter mais cliente reincidente — mesma ressalva do AUC 0,7003.
  A precisão maior da faixa Alto tem a mesma origem, e isso precisa ser dito junto.
- **Os 13,1 min são tempo de menu**, não duração do atendimento (essa é 24,5 min). Confundir os dois
  infla a conta em quase o dobro.
- A espera **evitável** pressupõe que encaminhar direto elimina o tempo de menu. Na prática elimina
  a maior parte, não tudo.

---

## No painel

Fonte nova: **`vw_monitoramento_horas`** (6 linhas).

**Gráfico**, ao lado do de distribuição:

| Campo | Valor |
|---|---|
| Tipo | Coluna agrupada |
| Dimensão | `faixa_operacional` |
| Dimensão de detalhamento | `origem` |
| Métrica | `horas_por_1000` · agregação **Média** |
| Classificar | `faixa_ordem` crescente |
| Classificação secundária | `origem_ordem` crescente |

Título: *"A espera evitável migrou para a faixa Alto"*.

**Indicador:** métrica `horas_por_1000`, filtros `faixa_operacional = Alto` e `origem_ordem = 2`.
Dá 50 h — o número que resume a página.

> **Nunca** use a coluna `horas_espera` num gráfico que compare as duas origens: 744 h contra 120 h
> é comparação entre populações de tamanhos diferentes. A coluna comparável é `horas_por_1000`.

---

## Na apresentação

Uma frase, no slide de monitoramento:

> *"O monitor não disparou só em percentual. Em horas: a cada mil conversas, treze horas de espera
> migraram para a faixa de maior risco — e encaminhar essa faixa passou a devolver 50 horas em vez
> de 37, com precisão maior. A fila não ficou mais lenta; ficou mais concentrada onde o modelo
> aponta."*
