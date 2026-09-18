# Features legais e vazamento — guia para a Fase 4

> ## ⚠️ Nota de atualização — 11/09/2026
>
> **Este documento foi escrito em 28/08, antes de qualquer treino, e permanece como registro
> dessa decisão.** Três pontos dele foram superados pelo que o projeto mediu depois. A fonte
> única da verdade para os números do modelo é `Numeros_Oficiais_Modelo13.md`.
>
> **1 · Os números do checklist final estão desatualizados.**
> O baseline de **74,77%** e o teto de **AUC 0,750** valiam para a população completa e para
> uma estimativa anterior. Depois de excluir as 4.958 conversas de disparo ativo e ruído, e
> com o teto recalculado a partir da fórmula do gerador (linha 484 de
> `gerar_dataset_cde_v8.py`), os valores corretos são **baseline 70,5%** e
> **teto AUC 0,6736**. O modelo final entrega **0,6729** — 99,6% do teto.
>
> **2 · O modelo final desvia desta regra em três pontos, e isso está declarado.**
>
> | Coluna | O que este documento determinou | O que o modelo de 13 variáveis faz | Impacto medido |
> |---|---|---|---|
> | `arquetipo` | *"não usar"* — é construção do gerador, não existe na operação real | usa | **≈ 0** no drop-one-out |
> | `produto_relacionado` | listada como derivada de `categoria_assunto` | usa | **≈ 0** no drop-one-out |
> | `categoria_assunto` | deve entrar como a categoria **prevista** pelo estágio 1 | usa o valor verdadeiro | é a variável essencial (−0,0684) |
>
> **Nenhum dos três é vazamento do desfecho** — o modelo não vê o resultado da conversa. Os
> dois primeiros são questão de **portabilidade** (um modelo que dependa de `arquetipo` não
> pode ser levado para o banco), e o teste de importância mostra que ambos contribuem **zero**:
> removê-los não altera o AUC. **O resultado não depende deles.**
>
> O terceiro é a limitação real. Em produção só existe a categoria prevista, e a versão
> rigorosa do modelo deveria usá-la. Este documento antecipou exatamente isso — *"a diferença
> numérica será pequena, mas a disciplina precisa estar no código, e a banca pode perguntar"*.
> A diferença é pequena; a disciplina não chegou ao código. **Fica declarado como limitação.**
>
> **3 · A recomendação de respeitar o tempo na divisão foi cumprida, por outro caminho.**
> A Seção "a divisão também deveria respeitar o tempo" sugeria treinar até uma data de corte e
> testar depois dela. A separação principal continuou sendo por cliente, mas a recomendação foi
> atendida em separado: `3_pipeline/10_lote_novo.py` treina até 10/08 e pontua a semana
> seguinte, com monitor de deriva. Ver `Carga_Incremental_Lote_Novo.md`.
>
> *Nada foi removido do texto original abaixo. Onde ele discordar desta nota, vale a nota.*

---

**Projeto Kenzie 360 · Sprint 3 · 28/08/2026**
Escrito antes de treinar qualquer modelo. Vale para os dois estágios do pipeline.

---

## O problema que este documento evita

A tabela `atendimentos` tem 30 colunas. A maioria delas **só existe depois que a conversa terminou**. Jogar todas num modelo produz um resultado excelente e completamente inútil: o modelo estaria lendo o desfecho para prever o desfecho.

Concretamente: `csat`, `duracao_seg` e `status_conversa` são consequência do que aconteceu. Um modelo com essas colunas acerta quase tudo — e não serve para nada em produção, onde no momento da decisão nenhuma delas existe ainda.

**A regra:** uma feature só é legal se o seu valor estiver disponível **no instante em que o modelo precisa decidir** — a abertura da conversa.

---

## Colunas legais

Disponíveis quando o cliente manda a primeira mensagem.

| Coluna | Por quê |
|---|---|
| `primeira_mensagem_cliente` | É o gatilho da inferência. Insumo principal do estágio 1 |
| `idioma` | Detectável na primeira mensagem |
| `segmento_cliente` | Cadastro |
| `perfil_tecnologico`, `faixa_etaria` | Cadastro |
| `origem` (Receptivo / Ativo) | O banco sabe se ele mesmo iniciou |
| `canal_entrada` | Conhecido na entrada |
| `data_hora` → hora, dia da semana | Conhecido |
| **`contatos_previos`** | Consulta ao histórico do cliente |
| **`reabertura`** | Consulta ao histórico do cliente |

As duas últimas **só são legais se o sistema consultar o histórico na abertura** — que é exatamente a recomendação da Seção 6.4 da EDA. Se a operação não fizer essa consulta, elas não existem em produção e não podem estar no modelo.

### Sobre `arquetipo`

É construção do gerador, não um campo que exista na operação real. **Não usar.** Um modelo que dependa dele não tem como ser portado para o banco.

---

## Colunas que vazam — não usar em nenhum estágio

| Coluna | Por que vaza |
|---|---|
| `resolvido_bot` | É o alvo do estágio 2 |
| `status_conversa` | O desfecho, escrito por extenso |
| `resolucao_declarada` | O desfecho |
| `sentimento_geral` | É o sentimento da **última** fala do cliente — muda conforme a conversa termine bem ou mal |
| `csat` | Só existe depois do atendimento |
| `duracao_seg` | Idem |
| `num_mensagens`, `num_mensagens_cliente` | Idem |
| `transferencia_iniciada`, `humano_atendeu` | Consequência do fracasso do bot |
| `canal_humano` | Só existe se houve transferência |
| `area_encaminhada`, `motivo_transferencia` | Preenchidos no fim, e são derivados do alvo do estágio 1 |
| `transcricao_completa` | Contém a conversa inteira, incluindo a fala de fechamento |
| `produto_relacionado` | Derivado de `categoria_assunto` — usar é o mesmo que usar o rótulo |
| `qtd_dados_mascarados` | Depende de quantas falas houve |

### O caso especial: `categoria_assunto`

É o **alvo do estágio 1**. No estágio 2 ele não pode entrar como valor verdadeiro — precisa entrar como **a categoria prevista pelo estágio 1**.

Usar a categoria verdadeira no estágio 2 daria um resultado otimista que a produção nunca reproduz, porque em produção só existe a previsão. Como o estágio 1 tem teto de 100%, a diferença numérica será pequena — mas a disciplina precisa estar no código, e a banca pode perguntar.

---

## Duas armadilhas de avaliação

### 1. A divisão treino/teste tem que ser por CLIENTE, não por conversa

`contatos_previos` e `reabertura` ligam as conversas de um mesmo cliente. Dividindo por conversa, o mesmo cliente aparece nos dois lados e o modelo memoriza a trajetória dele em vez de aprender o padrão.

Dividir por `id_cliente`: todas as conversas de um cliente ficam ou no treino ou no teste, nunca nos dois.

### 2. A divisão também deveria respeitar o tempo

Em produção o modelo é treinado no passado e aplicado no futuro. Uma divisão que sorteia conversas ao acaso ao longo dos seis meses treina com o futuro. Se der tempo, treinar até uma data de corte e testar depois dela — o que também prepara a demonstração de carga incremental.

Se não der tempo, a divisão por cliente já resolve o problema mais grave. Declarar a escolha no relatório.

---

## Checklist antes de rodar o treino

- [ ] Nenhuma coluna da lista de vazamento entrou no `X`
- [ ] `arquetipo` fora
- [ ] Estágio 2 usa a categoria **prevista**, não a verdadeira
- [ ] Divisão por `id_cliente`
- [ ] Baseline calculado e reportado ao lado do modelo (74,77% para o estágio 2)
- [ ] AUC reportado contra o teto conhecido (0,750)

**Se a acurácia vier muito acima do teto calculado, não comemore — procure o vazamento.** Os tetos foram medidos na base: 100% para o estágio 1, AUC de 0,750 para o estágio 2. Um resultado acima disso significa que uma coluna proibida entrou.
