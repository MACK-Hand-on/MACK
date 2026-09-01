# Brief para a equipe — 28/08

Rascunho para o Ilan enviar. Ajustar o tom conforme o canal (WhatsApp pede mais curto).

---

**Pessoal, resumo do que apurei hoje. Tem uma correção importante e uma decisão que precisa de vocês.**

**1. Achamos um erro na nossa própria EDA — e corrigimos**

Fui auditar o gerador da base antes de escolher o alvo do modelo e descobri que a Seção 4 estava calculando a taxa de falha sobre o denominador errado.

O motivo: no gerador, quando o caso é resolvido a área só é registrada em 40% das vezes; quando não é resolvido, é registrada sempre. Então estávamos dividindo os fracassos por um conjunto que excluía três em cada cinco sucessos. O número saiu inflado em exatamente 2×.

O que muda:
- Taxa de não resolução no atendimento humano: **32,0% → 15,9%**
- Resolução por área: 64%–69,6% → **81,7%–88,5%**
- "Cartões é a pior área" — era ruído estatístico, saiu
- "Dois modos de falha" — era artefato do gerador, saiu

O Teste (a) e o Teste (b) não foram afetados. O custo anual recalculado deu 11.197 h contra as 11.106 que publicamos — diferença de 0,8%.

Isso é chato, mas é muito melhor termos achado agora do que o professor achar na apresentação. E dá para transformar em ponto forte: "auditamos nossa própria análise e corrigimos" é maturidade metodológica que quase nenhum grupo leva.

Também reescrevi a Seção 6. A espiral de recorrência não é um achado — é um parâmetro que nós mesmos colocamos no gerador v8 (`atrito_por_contato = 0,07`). Continua valendo, mas agora está declarada como premissa modelada, não como descoberta. A recomendação prática que sai dela sobrevive inteira.

Tudo em `1_documentos/sprint2/EDA_Kenzie360_v2.md`. O original ficou preservado ao lado.

**2. Giovanna — dois pedidos**

- **Confere se o dashboard cita os 32% em algum lugar.** Se citar, o número agora é 15,9%. Melhor mexer hoje do que depois de consolidar o fim de semana inteiro em cima dele.
- Duas views da gold precisam de revisão e podem afetar o que você conectou: a `vw_funil_e_modos_de_falha` (existia só para os "dois modos de falha" que caíram) e a `vw_desempenho_areas_internas` (precisa usar o mapeamento assunto → área). Se você estiver usando alguma das duas, me avisa que eu ajusto antes.

**3. Jonathas — sua tarefa mudou de forma, e para melhor**

O professor fez duas críticas que na verdade são a mesma: faltou o desenho da arquitetura, e faltou explicar como o robô aprende.

O nosso desenho atual é um cano de mão única — dado entra, dashboard sai. É por isso que ele não encontrou o objetivo final ali. O que falta é o caminho de volta:

conversas novas → rotulagem → retreino → modelo melhor → influencia o próximo atendimento → que vira conversa nova

Então não é "deixar o diagrama mais bonito", é **desenhar o que faltava**: cinco estágios com a seta de retorno em destaque. Tem um documento com tudo mastigado e um diagrama base em `Ciclo_Aprendizado_Kenzie360.md`, no Project. O card do Trello está atualizado.

Uma boa notícia que apareceu na auditoria: a nossa silver **já está pronta para carga incremental** (ela já deduplica por chave de negócio). O único bloqueio é o `WRITE_TRUNCATE` da bronze. Estamos bem mais perto disso do que imaginávamos.

**4. Decisão que precisa de vocês: o alvo do modelo**

Regra do projeto é que isso se decide em grupo, então trago para vocês baterem o martelo.

Testei os candidatos direto na base, antes de treinar qualquer coisa:

- **Motivo de transferência** — inviável. É `random.choice()` no gerador, ruído puro, teto de acurácia = 20% (o acaso)
- **Opt-out** — descartado. Regra determinística que nós mesmos escrevemos; acurácia altíssima e valor zero
- **Categoria/área a partir do texto** — funciona, mas com teto de 100%: nenhuma das 11.438 aberturas é ambígua. Prova que a pipeline funciona, não que há aprendizado
- **Prever se o bot resolve** — como classificador é inútil (76,9% contra 74,8% de chutar sempre), mas como **escore de risco** tem teto de AUC 0,750, que é um número honesto

**Proposta: pipeline de dois estágios.** Estágio 1 classifica a intenção (texto → categoria → área de roteamento). Estágio 2 usa isso mais o histórico do cliente para estimar a probabilidade de o bot resolver. Um alimenta o outro, e juntos são a triagem na abertura — que é o ganho concreto que a EDA aponta para a V2.

O número que apresentamos como resultado é o **AUC do estágio 2 contra o teto de 0,750**, não a acurácia do estágio 1. Poder dizer "conhecemos o teto teórico do nosso problema e chegamos a X% dele" é coisa que quase ninguém leva para a banca.

Vocês concordam? Se tiverem outra ideia, é agora — segunda já vou estar com o estágio 1 rodando.

**5. Escopo — a resposta para "qual é o objetivo final"**

Fechamos assim:

> A Kenzie 360 é a camada de inteligência que transforma conversa em decisão. Ela é a fundação sobre a qual a V2 do bot será construída. O bot conversacional em si é o passo seguinte, fora do escopo deste semestre — e este projeto define o processo de aprendizado que vai alimentá-lo.

Descartamos fazer o bot completo: exigiria runtime de conversa e inferência em produção, não cabe no prazo, e seria um bot conversando com dados sintéticos.

**6. Trello e prazo**

Atualizei o quadro. Dois cards da Sprint 3 já estavam entregues desde a Sprint 2 e foram fechados; criei os que faltavam. **A Sprint 3 fecha segunda, 31/08.**

Tem um roteiro dia a dia até a entrega, com o que está com cada um: [colar o link do Roteiro Kenzie 360]

Qualquer coisa me chamem.
