# Guia — o gráfico de monitoramento (histórico × lote novo)

Para a Gi, 14/09. O gráfico que compara a distribuição das faixas de risco no **histórico**
(7.712 conversas de teste) com o **lote novo** (1.227 conversas da última semana, que o modelo
nunca viu).

---

## Antes de tudo: isto já estava decidido, de outro jeito

O `Guia_Painel_Modelo_Gi.md`, de 11/09, já resolve este gráfico na seção *"A página de
monitoramento — um gráfico, dois lados"*: **dois gráficos lado a lado**, mesma configuração,
fontes diferentes (`vw_painel_modelo` e `vw_painel_lote_novo`), com o eixo Y fixado de 0% a 50%.

**Se a página já está montada assim, está certa — não refaça.** Este documento não anula aquele:
descreve um caminho alternativo, de uma chamada só.

| | Caminho A — dois gráficos (guia de 11/09) | Caminho B — um gráfico (este documento) |
|---|---|---|
| Custo | nenhum script novo | rodar o `15_cria_vw_monitoramento.py` |
| Leitura | o olho salta entre dois gráficos | barras pareadas, comparação direta |
| Risco | se esquecer de fixar o eixo Y, a comparação visual mente | o percentual já vem pronto do SQL |
| Extra | — | indicadores de variação (“+10,1 pp”) prontos |

**Regra de decisão:** página já montada → fica no caminho A. Página ainda não montada → o caminho
B dá menos passos e menos chance de erro.

**Independente da escolha, vale rodar o script uma vez** (Passo 0). Ele não mexe no painel: só cria
duas views e imprime os seis números conferidos contra os documentos oficiais — o que resolve a
divergência aberta desde 11/09, em que o guia antigo registra o histórico como 26,6 / 40,5 / 32,8
e o `Numeros_Oficiais_Modelo13.md` registra 26,9 / 40,2 / 32,9.

---

## O que este gráfico responde

Uma pergunta só: **a fila que está chegando agora parece com a fila em que o modelo foi treinado?**

Se parecer, o modelo continua valendo. Se não parecer, alguém precisa olhar antes que a operação
tome decisão errada. É isso que um monitor de modelo faz — e é o que diferencia um projeto que
entrega um modelo de um projeto que entrega um modelo **em operação**.

No nosso caso a resposta é: **não parece**. A faixa Alto subiu cerca de 10 pontos. O gráfico mostra
isso, e o texto ao lado explica por quê — o que está detalhado no fim deste guia.

---

## Passo 0 — o Ilan roda um script (2 minutos)

O Looker Studio não junta duas tabelas em um gráfico só sem "mistura de dados", que é onde erro de
join acontece. E, pior, o gráfico teria que comparar 7.712 com 1.227 em valor absoluto — as barras
do lote novo sumiriam.

Então a junção e o percentual são feitos em SQL, uma vez. O script é o `15_cria_vw_monitoramento.py`:

```bash
kenzie
cd ~/MACK/3_pipeline
python3 15_cria_vw_monitoramento.py
```

Ele cria duas views na camada gold e imprime os seis números na tela, comparando com os documentos
oficiais. **Só siga para o Looker depois que a conferência passar.**

| View criada | O que tem dentro |
|---|---|
| `vw_monitoramento_faixas` | 6 linhas — 3 faixas × 2 origens. Traz `conversas`, `pct_da_fila` e `taxa_resolucao` |
| `vw_monitoramento_delta` | 3 linhas — uma por faixa, com o % nas duas origens e a variação já escrita ("+10,1 pp") |

---

## Passo 1 — criar as fontes no Looker Studio

No relatório, menu **Recurso → Gerenciar fontes de dados adicionadas → Adicionar uma fonte de
dados → BigQuery**.

1. Projeto `kenzie360` (ou o nome exato que aparecer na lista)
2. Conjunto de dados `kenzie360_gold`
3. Tabela `vw_monitoramento_faixas` → **Adicionar**
4. Repetir para `vw_monitoramento_delta`

Nas **credenciais da fonte de dados**, deixar **Credenciais do proprietário**. Assim o professor e
qualquer pessoa do grupo abrem o painel sem ter acesso ao BigQuery.

---

## Passo 2 — o gráfico principal (distribuição das faixas)

**Inserir → Gráfico de colunas → Coluna agrupada.** Fonte: `vw_monitoramento_faixas`.

| Campo do Looker | O que colocar |
|---|---|
| Dimensão | `faixa_operacional` |
| Dimensão de detalhamento | `origem` |
| Métrica | `pct_da_fila` |
| Agregação da métrica | **Média** |
| Classificar | `faixa_ordem` · **Crescente** |

Depois, três ajustes que fazem diferença:

1. **Formato da métrica.** Clique no campo `pct_da_fila` → ícone de lápis → Tipo → **Percentual**,
   1 casa decimal. O valor já vem como fração (0,269), então o Looker escreve 26,9%.
2. **Estilo → Rótulos de dados: ligado.** Com seis barras só, o número em cima de cada uma vale
   mais que o eixo.
3. **Estilo → Legenda: embaixo.** E desmarque *Mostrar total*.

> **Por que "Média" e não "Soma":** a view já vem agregada — existe **uma linha** por faixa e
> origem. Com uma linha só, soma e média dão o mesmo resultado, mas a média é à prova de erro se
> alguém acrescentar uma quebra no gráfico depois.

> **Nunca use "Contagem de registros" aqui.** São 7.712 contra 1.227: as barras do lote novo
> ficariam rasteiras e o gráfico diria a coisa errada. O percentual é o que torna as duas
> populações comparáveis.

### Cores

Séries em **Estilo → Série 1 / Série 2**:

| Série | Cor | Por quê |
|---|---|---|
| Histórico | `#57617A` cinza-azulado | é a referência, tem que ficar em segundo plano |
| Lote novo | `#9B3226` vermelho-tijolo | é o que mudou, e é a mesma cor da faixa Alto no resto do painel |

---

## Passo 3 — o segundo gráfico (a prova de que o score ainda separa)

Duplique o gráfico do Passo 2 (botão direito → Copiar / Colar) e troque **uma coisa só**: a métrica
`pct_da_fila` por **`taxa_resolucao`** (também em Média, formato Percentual).

Esse gráfico mostra que, mesmo no lote que o modelo nunca viu, a faixa Baixo continua resolvendo
mais que a Médio, que continua resolvendo mais que a Alto. É a prova de que o modelo não quebrou —
o que mudou foi a **composição** da fila, não a capacidade dele de ordenar.

Título sugerido: **“A ordenação continua valendo no lote novo”**.

---

## Passo 4 — os três indicadores de variação

**Inserir → Indicador (Scorecard)**, fonte `vw_monitoramento_delta`, métrica `delta_rotulo`.

Como `delta_rotulo` é texto (“+10,1 pp”), o Looker vai oferecer a agregação **Máx.** — use essa.
Depois duplique duas vezes e, em cada cópia, adicione um filtro:

- **Adicionar filtro → Incluir → `faixa_operacional` → Igual a → `Baixo`** (depois `Medio`, depois `Alto`)
- Em **Estilo → Título do indicador**, escreva o nome da faixa

Resultado: três números grandes lado a lado — algo como `−5,8 pp` · `−4,2 pp` · `+10,0 pp`.

> **`Medio` é sem acento** nas duas views. Se escrever "Médio" no filtro, ele volta vazio.

---

## Passo 5 — o texto que acompanha (é isso que dá nota)

Um gráfico de monitoramento sem leitura é decoração. Coloque uma caixa de texto ao lado, com este
conteúdo:

> **O monitor disparou.** A faixa Alto subiu ~10 pontos no lote novo.
>
> **E se autodiagnosticou:** o mix de assuntos ficou estável — o que subiu foi a recorrência, ou
> seja, a quantidade de clientes que já tinham conversado antes.
>
> **A conclusão:** é artefato de base finita, não deriva de população. Numa base que começa do
> zero, o contador de contatos por cliente só pode crescer com o tempo. O modelo continua válido.
>
> Um monitor que dispara sem explicar vira ruído que a operação aprende a ignorar. Este disparou
> com a causa junto.

**Cuidado na fala:** o AUC no lote novo é 0,7003, maior que os 0,6729 do histórico.
**Não apresente isso como melhora** — o lote novo é mais fácil justamente porque tem mais cliente
reincidente, que é a variável mais forte do modelo.

---

## Como conferir se ficou certo

**Conferido no BigQuery em 15/09** — o script rodou e os seis números batem com os documentos
oficiais. Estes são os valores que o painel tem que mostrar:

| | Baixo | Médio | Alto |
|---|---|---|---|
| **Histórico — 7.712** | 26,9% (2.078) | 40,2% (3.098) | 32,9% (2.536) |
| **Lote novo — 1.227** | 21,1% (259) | 36,0% (442) | 42,9% (526) |
| **Variação** | −5,8 pp | −4,1 pp | **+10,0 pp** |

E a taxa de resolução em cada faixa, que é o segundo gráfico:

| | Baixo | Médio | Alto |
|---|---|---|---|
| Histórico | 47,5% | 27,6% | 17,1% |
| Lote novo | 48,3% | 30,8% | 13,7% |

> **A ordenação se manteve no lote que o modelo nunca viu** — e ficou até um pouco mais nítida
> (34,6 pontos de distância entre a primeira e a última faixa, contra 30,4 no histórico). A leitura
> correta é *"continua separando"*, **não** *"melhorou"*: é uma semana, 1.227 conversas, e o lote
> novo é mais fácil por ter mais cliente reincidente. Mesma ressalva do AUC 0,7003.

### Sobre o 26,6% que aparece no guia antigo

O `Guia_Painel_Modelo_Gi.md` registra, na seção de monitoramento, o histórico como
26,6 / 40,5 / 32,8 — mas o **mesmo documento**, no Gráfico 1, registra 2.078 conversas na faixa
Baixo, que são 26,9%. Ou seja, ele se contradiz.

O BigQuery desempatou: **sobre as 7.712 conversas do conjunto de teste, é 26,9 / 40,2 / 32,9.**
A linha de 26,6 provavelmente veio da saída do `10_lote_novo.py`, que usa outra população como
referência. **Para o painel, vale o que a view devolve.**

**Atenção:** o `Guia_Painel_Modelo_Gi.md` de 11/09 registra a linha do histórico como
26,6 / 40,5 / 32,8. É meio ponto de diferença, e os dois documentos são nossos — então um está
errado. **O BigQuery decide.** O que o script imprimir é a verdade, e o outro documento tem que ser
corrigido antes da banca.

Se o BigQuery devolver um terceiro número, diferente dos dois, **pare** e me chame antes de
publicar: aí não é documento desatualizado, é carga com linha a mais. Não arredonde para fazer
bater.

---

## Se aparecer "Configuração inválida"

> *"As métricas de comparação não são compatíveis com a opção Agrupar em 'Outros'."*

**O que o Looker está dizendo:** esse gráfico usa um **cálculo de comparação** (o "Porcentagem do
total", que se liga na métrica) e, ao mesmo tempo, a dimensão está com **"Agrupar em 'Outros'"**
ligado. As duas coisas não convivem — o cálculo de porcentagem precisa de todas as linhas, e o
agrupamento em "Outros" junta as menores antes da conta.

Esse erro aparece no **Gráfico 1 do `Guia_Painel_Modelo_Gi.md`** (distribuição da fila) e em
qualquer gráfico que use "Porcentagem do total".

### Saída 1 — desligar o "Agrupar em Outros" (30 segundos)

Com o gráfico selecionado, procure o interruptor **"Agrupar em 'Outros'"**. Dependendo da versão do
Looker, ele está em um destes dois lugares:

- aba **Configuração** → clique no chip da dimensão (`faixa_operacional`) → o interruptor aparece no
  painel que abre; ou
- aba **Estilo** → rolar até o fim, onde ficam as opções de linhas e "Outros".

Desligue. O erro some na hora e o gráfico volta com as três faixas.

### Saída 2 — não usar cálculo de comparação (a definitiva)

O cálculo de comparação é frágil: quebra com "Outros", quebra em mistura de dados e some se alguém
trocar a métrica. **Se o percentual já for uma coluna, nada disso acontece.**

É o que a `vw_monitoramento_faixas` faz: o campo `pct_da_fila` já é o percentual, métrica comum,
sem cálculo de comparação nenhum. Peça o Passo 0 ao Ilan e o problema desaparece por construção —
inclusive no gráfico de distribuição da primeira página.

### Saída 3 — coluna empilhada 100% (sem script, sem comparação)

Se quiser resolver agora, sem esperar o script:

1. Na fonte, **Adicionar um campo** → nome `origem` → fórmula: `"Historico"` (com as aspas mesmo —
   é um texto fixo). Na fonte do lote novo, `"Lote novo"`.
2. No gráfico, tipo **Coluna empilhada 100%**
3. Dimensão `origem` · Dimensão de detalhamento `faixa_operacional` · Métrica `Contagem de registros`

Cada barra vira 100% repartido nas três faixas, sem nenhum cálculo de comparação. É a mesma leitura,
por outro caminho.

---

## Plano B — sem rodar script nenhum

Dá para fazer no Looker puro, com **Recurso → Gerenciar misturas → Adicionar uma mistura**,
juntando `vw_painel_modelo` e `vw_painel_lote_novo` por `faixa_operacional` (junção externa
completa). Funciona, mas:

- o percentual você teria que montar como campo calculado dentro do gráfico;
- a mistura quebra em silêncio se alguém renomear uma coluna;
- e não dá para reaproveitar o mesmo número em outro gráfico sem refazer tudo.

Por isso a view é o caminho recomendado. O plano B fica aqui só se o acesso ao BigQuery travar na
véspera.

---

## Onde isso entra na apresentação

Segunda página do painel, junto com o gráfico de faixas. Na fala, é o trecho do Jonathas sobre
monitoramento — e é o argumento de que o projeto não entregou só um modelo, entregou um modelo com
vigilância.
