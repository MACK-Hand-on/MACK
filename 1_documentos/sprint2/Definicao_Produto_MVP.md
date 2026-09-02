# Definição de Produto — Kenzie 360

**MVP · Sprint 3 · 28/08/2026**
Ilan David Schapira · Giovanna Caetano Protti · Jonathas Borges
MBA Engenharia de Dados · Mackenzie · Prof. Gustavo Ferreira

---

## 1. O que é

> A Kenzie 360 é a **camada de inteligência que transforma conversa em decisão**. Ela lê a abertura de cada atendimento, estima o risco de o bot não conseguir resolver, e roteia o caso antes que o cliente perceba que entrou no caminho errado.

É a fundação sobre a qual a V2 do bot será construída — e o mecanismo pelo qual essa V2 aprende.

## 2. O que não é

- **Não é a V2 do bot.** Não escreve resposta, não conversa, não substitui o script atual
- **Não é um relatório.** A saída principal é uma decisão tomada durante o atendimento, não um documento lido depois
- **Não é um modelo treinado uma vez.** O processo de aprendizado contínuo é parte do produto, não um acessório

## 3. Quem usa, e o que muda

O mesmo motor serve dois consumidores em latências diferentes — e eles correspondem exatamente às duas camadas da arquitetura Lambda do projeto.

### 3.1 O bot, na abertura da conversa · camada de velocidade

Entra o texto da primeira mensagem. Sai a rota.

| Hoje | Com a Kenzie 360 |
|---|---|
| Toda conversa entra no script do bot | O caso de alto risco vai direto ao humano, com contexto |
| O cliente descobre que o bot não resolve depois de 14 minutos | A decisão acontece no primeiro turno |
| O histórico do cliente só aparece se alguém procurar | Contatos prévios e reabertura entram na decisão |

**A decisão é automática.** Não há aprovação humana prévia, porque o cliente está aguardando na conversa — não existe supervisor capaz de aprovar roteamento ao vivo em escala.

### 3.2 O supervisor, depois · camada de lote e serviço

Ele vê a fila do que já foi roteado, com a probabilidade que gerou cada decisão, e pode marcar **"este caso foi roteado errado"**.

**Essa marcação é o rótulo.** É ela que alimenta o retreino — o Estágio 3 do ciclo de aprendizado. O supervisor não é um portão de aprovação; é a fonte de aprendizado do sistema.

Sem esse papel, o modelo é treinado uma vez e envelhece em silêncio. Com ele, o produto melhora com o uso.

## 4. A decisão de negócio que muda

**Antes:** a operação descobre que uma demanda não tinha solução no bot depois de gastar o tempo do bot, o tempo da fila e a paciência do cliente. Se o cliente desiste no meio, ninguém registra o motivo — 1.481 clientes por ano saem assim.

**Depois:** a operação decide na abertura onde cada caso deve ser resolvido, e passa a saber quanto custa cada erro dessa decisão.

E há uma assimetria que orienta a política de roteamento:

| Erro | Custo |
|---|---|
| Roteou ao humano um caso que o bot resolveria | Tempo de atendente. O cliente é bem atendido |
| Deixou no bot um caso que vai falhar | O cliente percorre a jornada que falha, se irrita e — pela espiral de recorrência — **volta pior e é atendido pior** |

O segundo erro é mais caro, e seu custo não termina na conversa. **A política deve pender para rotear demais, não de menos.**

## 5. O motor

Dois estágios em cascata, ambos disparados pela primeira mensagem do cliente.

| Estágio | Entrada | Saída |
|---|---|---|
| **1 · Intenção** | Texto da abertura | Categoria do assunto → área de encaminhamento |
| **2 · Risco** | Categoria prevista + contatos prévios + reabertura | Probabilidade de o bot resolver |

O estágio 1 é o extrator de features do estágio 2. A área de encaminhamento sai por mapeamento determinístico a partir da categoria.

**Avaliação:** o estágio 2 é medido por **AUC e calibração**, nunca por acurácia — como classificador ele fica a 2,1 p.p. de chutar sempre a classe majoritária; como escore de risco tem teto de AUC de 0,750. O número que o projeto apresenta como resultado é o AUC obtido contra esse teto.

## 6. Onde cortar — decisão em aberto

O modelo devolve uma probabilidade contínua. **Onde colocar o corte é decisão de produto, não de estatística.**

E o corte certo não depende do modelo: depende de **quanto volume a equipe humana consegue absorver**. A calibração é:

1. Ordenar as conversas pela probabilidade de falha
2. Descer a lista até o volume diário que a operação comporta
3. A probabilidade nesse ponto é o corte

Corte agressivo demais entope a fila humana. Conservador demais, o modelo não muda nada. Este parâmetro deve ser revisto sempre que a capacidade da operação mudar.

**Fica registrado como decisão em aberto** — na base sintética ele será fixado apenas para demonstração.

## 7. Requisitos do MVP

**Funcionais**

| # | Requisito |
|---|---|
| RF1 | Classificar a intenção a partir do texto de abertura |
| RF2 | Estimar a probabilidade de resolução pelo bot |
| RF3 | Devolver uma rota: seguir no bot, ou encaminhar ao humano com contexto |
| RF4 | Registrar decisão e probabilidade de cada caso, para auditoria |
| RF5 | Permitir ao supervisor marcar uma decisão como errada |
| RF6 | Painel com a fila priorizada por risco |

**Não funcionais**

| # | Requisito |
|---|---|
| RNF1 | Executar dentro do free tier da GCP |
| RNF2 | Ingestão incremental — processar apenas o lote novo, sem duplicar |
| RNF3 | Reprodutível: mesma semente, mesmo resultado |
| RNF4 | Nenhum dado pessoal na base ou nos artefatos |
| RNF5 | Código versionado, incluindo a pipeline |
| RNF6 | Nenhuma feature indisponível no momento da decisão (ver `Features_e_Vazamento.md`) |

## 8. Critério de pronto

A entrega está pronta quando:

- [ ] A pipeline roda de ponta a ponta sobre um lote novo, sem intervenção manual
- [ ] Uma conversa entra pelo texto de abertura e sai com rota e probabilidade
- [ ] O AUC do estágio 2 está reportado ao lado do teto de 0,750 e do baseline de 74,77%
- [ ] O painel do supervisor está conectado e abre com credenciais do proprietário
- [ ] O ciclo de aprendizado está desenhado por inteiro, com os estágios não construídos declarados como tal
- [ ] A limitação da base sintética está no relatório, escrita por nós

## 9. Fora de escopo desta entrega

- **Integração com o bot em produção.** "Tempo real" aqui significa o caminho de inferência demonstrado ponta a ponta em uma conversa — não um serviço implantado
- **Streaming (Pub/Sub).** Permanece no desenho como evolução declarada; o incremental diário atende o caso de uso
- **Retreino automático.** O ciclo é desenhado e o gatilho definido; a execução automática fica para depois
- **Geração de resposta.** O produto decide a rota, não escreve o texto

## 10. Limitação declarada

A base é 100% sintética, construída como gêmeo estatístico e calibrada por indicadores agregados da operação real. **Um modelo treinado sobre texto sintético aprende os padrões do gerador, não os do cliente.**

O que esta entrega demonstra com solidez é que o **processo** funciona ponta a ponta — ingestão, rotulagem, treino, inferência e retorno. É o processo, e não o modelo treinado, que transfere para a operação real.

Os tetos de desempenho foram medidos na base **antes** de qualquer treino, precisamente para que o resultado possa ser lido com honestidade: 100% para o estágio 1, AUC de 0,750 para o estágio 2.

---

**Documentos relacionados:** `Ciclo_Aprendizado_Kenzie360.md` · `Features_e_Vazamento.md` · `EDA_Kenzie360_v2.md` · `Decisoes_Sprint3.md`
