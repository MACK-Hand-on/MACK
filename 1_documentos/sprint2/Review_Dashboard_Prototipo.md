# Review do protótipo do dashboard — Kenzie 360

**Relatório:** "Trab Kenzie 360" (Looker Studio) · versão de 25/08/2026 23:14
**Autoria:** Giovanna Caetano Protti
**Revisão:** conferência numérica contra a base v8 + leitura de forma

---

## Veredito

**Os números estão todos certos.** Conferi cada indicador do relatório direto contra o CSV da base v8, sem passar pelo BigQuery, e bateu tudo — inclusive nas casas exatas.

| Indicador no dashboard | Valor exibido | Conferido na base | |
|---|---|---|---|
| Total de Conversas | 36.000 | 36.000 | ✔ |
| Total de Conversas Resolvidas | 20.493 | 20.493 | ✔ |
| Conversas resolvidas pelo bot (soma mensal) | ~9.183 | 9.084 | ✔ (arredondamento dos rótulos "mil") |
| Fila abandonada (soma mensal) | ~1.481 | 1.481 | ✔ |
| Série mensal de conversas | 2,2 / 5,9 / 5,9 / 5,8 / 6,2 / 6,5 / 3,6 mil | 2.173 / 5.891 / 5.899 / 5.785 / 6.163 / 6.483 / 3.606 | ✔ |

Modelagem e ligação com o BigQuery estão corretas. O que segue é sobre **o que os gráficos contam**, não sobre estarem certos.

---

## 1. O achado mais importante: a história está nos dados, mas invisível no gráfico

Os gráficos mostram **volumes absolutos**. Como o volume de conversas cresce ao longo do período, as linhas de resolvidas parecem estáveis — e o dashboard passa a impressão de um bot com desempenho constante.

Quando se olha a **taxa**, aparece exatamente o contrário:

| Mês | Conversas | % resolvido pelo bot | % abandono do cliente |
|---|---|---|---|
| fev/26* | 2.173 | **30,9%** | 12,9% |
| mar/26 | 5.891 | 26,8% | 15,4% |
| abr/26 | 5.899 | 26,7% | 16,5% |
| mai/26 | 5.785 | 25,8% | 16,5% |
| jun/26 | 6.163 | 23,6% | 18,9% |
| jul/26 | 6.483 | 23,1% | 19,5% |
| ago/26* | 3.606 | **22,5%** | **19,1%** |

\* meses parciais — ver item 2.

**A autonomia do bot cai 8,4 pontos percentuais** enquanto o volume sobe. E o abandono do cliente sobe de 12,9% para 19,1% no mesmo período.

Isso é a hipótese do projeto aparecendo no dado: o script atual não escala. Ele não piora em número absoluto — ele deixa de dar conta do crescimento, e a diferença transborda para o atendimento humano e para o abandono.

**Recomendação:** trocar (ou acrescentar) uma série de **taxa** ao lado das de volume. É o gráfico que sustenta a narrativa da entrega.

> **Cuidado técnico ao montar.** A view `vw_kpi_diario` já traz `pct_autonomia` e `pct_resolucao_total`, mas esses campos são **percentuais diários**. Se você arrastar `pct_autonomia` como métrica em um gráfico mensal, o Looker vai calcular a *média das taxas diárias* — que não é a taxa do mês (dias de sábado, com pouquíssimo volume, pesariam igual a uma terça cheia).
>
> O certo é criar um **campo calculado** no Looker (Adicionar campo → Campo calculado):
>
> ```
> Nome: Taxa de autonomia
> Fórmula: SUM(resolvidas_bot) / SUM(conversas)
> Tipo: Número → Percentual
> ```
>
> E o equivalente para resolução total:
>
> ```
> Nome: Taxa de resolução
> Fórmula: SUM(resolvidas_total) / SUM(conversas)
> ```

---

## 2. Fevereiro e agosto são meses parciais — e isso engana

A base começa em **17/02/2026** e termina em **17/08/2026**. Os dois meses das pontas têm cerca de metade dos dias.

No gráfico, agosto aparece como uma queda de 6,5 mil para 3,6 mil. Qualquer pessoa da banca vai ler isso como "o volume despencou em agosto" — e não despencou, o mês só está pela metade.

**Três saídas, da mais simples para a mais completa:**

1. Filtrar o período para **01/03 a 31/07** (cinco meses cheios) nos gráficos mensais.
2. Manter os sete meses e escrever, abaixo do gráfico: *"fev e ago são meses parciais (base: 17/02 a 17/08)"*.
3. Trocar o eixo mensal por **média diária do mês** — imune ao problema, mas menos intuitivo para a banca.

A opção 1 é a mais segura para apresentação. A 2 preserva o dado inteiro.

---

## 3. O gráfico "Resolvidas X Resolvidas Bot" está somando duas vezes

Esse gráfico está com barras **empilhadas**: `resolvidas_bot` embaixo, `resolvidas_total` em cima.

O problema é conceitual: **`resolvidas_bot` é um subconjunto de `resolvidas_total`**. Toda conversa resolvida pelo bot também é uma conversa resolvida. Empilhando, março vira uma coluna de altura 1,6 + 3,4 = 5,0 mil — um número que não existe e não significa nada.

**Correção — duas opções:**

| Opção | Como | O que comunica |
|---|---|---|
| **A** *(recomendada)* | Trocar para **barras agrupadas** (lado a lado) | Compara o tamanho do bot contra o total, sem inventar soma |
| B | Manter empilhado, mas criar o campo `resolvidas_humano = resolvidas_total - resolvidas_bot` e empilhar **bot + humano** | Aí a soma é legítima e a altura vira o total de resolvidas |

A opção B é mais elegante e responde "quem resolveu o quê" numa olhada só. No Looker: Adicionar campo → Campo calculado → `SUM(resolvidas_total) - SUM(resolvidas_bot)`.

O gráfico ao lado ("Conversas X Abandonada") já está com barras agrupadas e por isso não tem esse problema.

---

## 4. "Fila abandonada" não é o abandono do cliente — e a diferença é grande

O campo `fila_abandonada` da view `vw_kpi_diario` é:

```sql
COUNTIF(transferencia_iniciada AND NOT humano_atendeu)
```

Ou seja: **conversas que o bot transferiu e nenhum humano chegou a atender**. É o abandono *na fila* — 1.481 conversas, 4,1% do total.

O abandono do cliente, em qualquer ponto da jornada, é `status_conversa = 'Abandonada pelo cliente'` — **6.229 conversas, 17,3% do total**, mais de quatro vezes maior.

Nenhum dos dois está errado; eles medem coisas diferentes. Mas o gráfico se chama "Conversas X Abandonada", e quem lê vai entender "abandono" no sentido amplo — e sair com 4,1% na cabeça quando o número real da dor é 17,3%.

**Duas correções, e vale fazer as duas:**

1. Renomear o gráfico para **"Abandono na fila de atendimento humano — Mensal"**.
2. Acrescentar um gráfico ou KPI do abandono do cliente (17,3%), que é a métrica com peso de negócio.

---

## 5. Ajustes de forma (rápidos, mas visíveis)

| Item | Situação | Ajuste |
|---|---|---|
| **Foto de perfil no cabeçalho** | Há um avatar pessoal no canto superior direito | Trocar pelo logo do projeto ou remover — numa entrega à banca, foto pessoal desloca o tom |
| **Quarto cartão de KPI** | Está vazio | Preencher (sugestão: **Taxa de autonomia do bot**, o indicador-chave) ou remover |
| **Página 2 ("Visão")** | Só tem cabeçalho, dois filtros e dois retângulos vazios | Terminar ou ocultar antes da entrega |
| **Texto do cabeçalho da página 2** | "Visão" e os dois filtros estão em cor escura sobre a faixa vinho — ilegíveis | Texto branco |
| **Nomes das páginas** | As duas se chamam "Página sem título" | Ex.: "Visão Executiva" e "Detalhamento" |
| **Título do relatório** | "Trab Kenzie 360" / "DashBoard Kenzie 360" | "Kenzie 360 — Painel de Atendimento". E a grafia é "Dashboard", não "DashBoard" |
| **Redundância** | Os dois primeiros gráficos mostram a mesma barra de conversas, mudando só a linha | Dá para consolidar num só com as duas linhas, liberando espaço para o gráfico de taxa |

---

## 6. Uma verificação de permissão antes da entrega

Abrindo o link de fora, ele exige login do Google — o que está certo, o relatório não deve ficar público.

Mas vale conferir **como a fonte de dados foi credenciada**: em Recursos → Gerenciar fontes de dados adicionadas, cada fonte é "Credenciais do proprietário" ou "Credenciais do visualizador".

- **Credenciais do proprietário** → quem abrir vê os dados usando o acesso da Giovanna. É o que a banca precisa.
- **Credenciais do visualizador** → cada pessoa precisa ter IAM no projeto `kenzie-360-mba`. O Prof. Gustavo não tem, e veria o relatório em branco.

Se estiver na segunda opção, é um clique para trocar — e é o tipo de coisa que só se descobre na hora da apresentação.

---

## Resumo priorizado

| # | Item | Impacto | Esforço |
|---|---|---|---|
| 1 | Acrescentar gráfico de **taxa** (autonomia caindo 30,9% → 22,5%) | **Alto** — é a narrativa da entrega | 30 min |
| 2 | Corrigir empilhamento de "Resolvidas X Resolvidas Bot" | **Alto** — número exibido não existe | 10 min |
| 3 | Renomear "Abandonada" e acrescentar o abandono do cliente (17,3%) | **Alto** — evita subestimar a dor em 4x | 20 min |
| 4 | Tratar meses parciais (fev e ago) | Médio | 10 min |
| 5 | Conferir credenciais da fonte de dados | Médio — mas quebra a apresentação se estiver errado | 2 min |
| 6 | Ajustes de forma (avatar, KPI vazio, contraste, nomes) | Médio | 30 min |
| 7 | Terminar ou ocultar a página 2 | Médio | — |

Nada aqui exige refazer o trabalho. A base está certa, a conexão está certa e os números batem — o que falta é fazer os gráficos contarem a história que os dados já têm.
