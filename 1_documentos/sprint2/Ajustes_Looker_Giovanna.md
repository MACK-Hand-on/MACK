# Os três ajustes do painel — passo a passo

**Para:** Giovanna · **Fonte de dados:** `kenzie360_gold.vw_kpi_diario`
**Base do que está aqui:** `Review_Dashboard_Prototipo.md`

Os números do protótipo estão **certos** — foram conferidos contra a base e batem exatamente. O que segue é sobre o que os gráficos contam, não sobre estarem corretos.

---

## Passo 0 — atualizar a fonte de dados

O Ilan acrescentou uma coluna nova à view (`abandono_cliente`). Ela **não aparece sozinha** no Looker.

1. Recursos → Gerenciar fontes de dados adicionadas
2. Clicar em **Editar** na fonte da `vw_kpi_diario`
3. Botão **Atualizar campos**, no canto inferior esquerdo
4. Confirmar que `abandono_cliente` apareceu na lista
5. **Concluído**

Se essa coluna não aparecer, os passos seguintes não funcionam.

---

## Passo 1 — criar quatro campos calculados

Ainda dentro do editor da fonte de dados: **Adicionar um campo → Campo calculado**.

| Nome do campo | Fórmula | Formato |
|---|---|---|
| `Taxa de autonomia` | `SUM(resolvidas_bot) / SUM(conversas)` | Percentual |
| `Taxa de resolução` | `SUM(resolvidas_total) / SUM(conversas)` | Percentual |
| `Taxa de abandono do cliente` | `SUM(abandono_cliente) / SUM(conversas)` | Percentual |
| `Resolvidas por humano` | `SUM(resolvidas_total) - SUM(resolvidas_bot)` | Número |

> ### Por que `SUM/SUM` e não o campo `pct_autonomia` que já existe
>
> A view já traz `pct_autonomia`, mas ele é **percentual diário**. Se você arrastar esse campo para um gráfico mensal, o Looker calcula a **média das taxas diárias** — e aí um sábado com 40 conversas pesa igual a uma terça com 300.
>
> `SUM(resolvidas_bot) / SUM(conversas)` soma primeiro e divide depois. É a taxa do mês de verdade.
>
> A diferença não é pequena e não é visível olhando o gráfico. É o tipo de erro que passa despercebido até alguém conferir na mão.

---

## Ajuste 1 — o gráfico de taxa *(prioridade máxima)*

**O problema.** Os gráficos atuais mostram volume absoluto. Como o volume cresce ao longo do período, o bot *parece* estável. Em taxa, ele está piorando — e isso é a narrativa do projeto.

**Montar assim:**

| Configuração | Valor |
|---|---|
| Tipo de gráfico | **Gráfico de linhas** |
| Dimensão | `mes` |
| Métrica 1 | `Taxa de autonomia` |
| Métrica 2 | `Taxa de resolução` |
| Eixo Y | Começar em zero, formato percentual |
| Título | **Autonomia do bot — taxa mensal** |

**Confira contra estes números.** Se o seu gráfico bater com esta tabela, está certo:

| Mês | Taxa de autonomia | Taxa de resolução | Abandono do cliente |
|---|---|---|---|
| fev/26 * | 30,9% | 62,3% | 12,9% |
| mar/26 | 26,8% | 58,2% | 15,4% |
| abr/26 | 26,7% | 58,6% | 16,5% |
| mai/26 | 25,8% | 57,4% | 16,5% |
| jun/26 | 23,6% | 54,8% | 18,9% |
| jul/26 | 23,1% | 54,8% | 19,5% |
| ago/26 * | 22,5% | 55,4% | 19,1% |

**A leitura:** a autonomia cai 8,4 pontos percentuais enquanto o volume sobe, e o abandono sobe 6,2 pontos no mesmo período. O bot não piorou — ele deixou de dar conta do crescimento, e a diferença transbordou para o atendimento humano e para o abandono.

\* Meses parciais — ver o ajuste 4.

---

## Ajuste 2 — corrigir o empilhamento

**O problema.** O gráfico "Resolvidas X Resolvidas Bot" está com barras empilhadas, mas `resolvidas_bot` é **subconjunto** de `resolvidas_total`. Em março, a coluna vira 1,6 + 3,4 = 5,0 mil — um número que não existe.

**Duas saídas. A segunda é melhor.**

| | Como | O que comunica |
|---|---|---|
| A | Trocar para **barras agrupadas** (lado a lado), mantendo `resolvidas_bot` e `resolvidas_total` | Compara os dois sem inventar soma |
| **B** ✔ | Manter empilhado, mas trocar `resolvidas_total` por **`Resolvidas por humano`** | A altura passa a ser o total de resolvidas, e cada faixa mostra quem resolveu |

Na opção B, a soma volta a ser legítima: bot + humano = total. E o gráfico responde "quem resolveu o quê" numa olhada.

Título sugerido: **Quem resolveu — bot e humano, por mês**

---

## Ajuste 3 — o abandono certo

**O problema.** O gráfico usa `fila_abandonada`, que é `transferencia_iniciada AND NOT humano_atendeu` — conversas transferidas que **nenhum humano chegou a atender**. São 1.481, 4,1% do total.

O abandono do cliente, em qualquer ponto da jornada, é **6.229 conversas, 17,3%**. Quatro vezes maior.

Os dois são válidos e medem coisas diferentes. O problema é o nome: quem lê "Abandonada" entende o sentido amplo e sai com 4,1% na cabeça, quando o número da dor é 17,3%.

**Montar assim:**

| Configuração | Valor |
|---|---|
| Tipo | Barras **agrupadas** (não empilhadas — um não contém o outro) |
| Dimensão | `mes` |
| Métrica 1 | `abandono_cliente` |
| Métrica 2 | `fila_abandonada` |
| Título | **Abandono — do cliente e na fila de atendimento** |

Conferência: as duas séries somam 6.229 e 1.481 no período inteiro.

---

## Ajuste 4 — os meses parciais

A base vai de **17/02 a 17/08/2026**. Os dois meses das pontas têm cerca de metade dos dias.

No gráfico, agosto aparece como queda de 6,5 mil para 3,6 mil. Qualquer pessoa lê como "o volume despencou" — e não despencou, o mês está pela metade.

**Escolha uma:**

1. Filtrar o período para **01/03 a 31/07** nos gráficos mensais de volume *(mais seguro para apresentar)*
2. Manter os sete meses e escrever abaixo: *"fev e ago são meses parciais — base de 17/02 a 17/08"*

Nos gráficos de **taxa**, o problema não existe: taxa é imune a mês parcial. Só os de volume precisam de tratamento.

---

## Ajuste 5 — a checagem que quebra a apresentação se estiver errada

Recursos → Gerenciar fontes de dados adicionadas → coluna **Credenciais**.

| Valor | O que acontece |
|---|---|
| **Credenciais do proprietário** ✔ | Quem abrir vê os dados usando o seu acesso |
| Credenciais do visualizador | Cada pessoa precisa ter permissão no projeto GCP — o Prof. Gustavo veria o relatório em branco |

Se estiver na segunda, é um clique para trocar. É o tipo de coisa que só se descobre na hora.

---

## Ajuste 6 — forma

Rápidos e visíveis:

- **Foto de perfil no cabeçalho** → trocar pelo logo do projeto ou remover
- **Quarto cartão de KPI vazio** → preencher com `Taxa de autonomia` (o indicador central) ou remover
- **Página 2** → o texto do cabeçalho está escuro sobre a faixa vinho, ilegível. Texto branco
- **Nomes das páginas** → as duas se chamam "Página sem título". Ex.: "Visão Executiva" e "Detalhamento"
- **Título** → "Kenzie 360 — Painel de Atendimento". E a grafia é "Dashboard", não "DashBoard"
- **Redundância** → os dois primeiros gráficos repetem a mesma barra de conversas mudando só a linha. Dá para consolidar num só e liberar espaço para o gráfico de taxa

---

## Ordem sugerida

| | | Tempo |
|---|---|---|
| 1 | Passo 0 e 1 — atualizar campos e criar os calculados | 15 min |
| 2 | Ajuste 1 — o gráfico de taxa | 30 min |
| 3 | Ajuste 2 e 3 — corrigir os dois gráficos existentes | 30 min |
| 4 | Ajuste 5 — conferir credenciais | 2 min |
| 5 | Ajuste 4 e 6 — meses parciais e forma | 30 min |

Os três primeiros são os que mudam o que o painel diz. O resto é acabamento.
