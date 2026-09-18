# Trilhas de carreira e atuação dos perfis envolvidos

**Projeto Kenzie 360 · Item 5 do escopo · MBA Engenharia de Dados · Mackenzie**  
**Grupo:** Ilan David Schapira · Giovanna Caetano Protti · Jonathas Borges  
**11/09/2026**

---

## 1. Por que este item não é teoria

O escopo pede para mapear "os perfis envolvidos". A tentação é listar descrições de vaga tiradas da internet. Preferimos outro caminho: **descrever os papéis que o Kenzie 360 de fato exigiu**, e quem do grupo os exerceu — porque isso nós vivemos, e dá material verificável em vez de generalidade.

Somos três pessoas. Um projeto de dados de ponta a ponta exige mais do que três funções. Então cada um acumulou papéis, e **é nas costuras entre eles que o projeto quase errou** — três vezes. Essa é a parte interessante deste documento.

---

## 2. Os perfis que o projeto exigiu

| Perfil | O que responde | Onde apareceu no Kenzie 360 | Ferramentas |
|---|---|---|---|
| **Analista de Negócio / Produto de Dados** | *Que pergunta vale a pena responder?* | Definição do problema, hipótese dos três eixos, escolha do alvo do modelo, cortes das faixas operacionais, Caso de Negócio | Briefing, entrevistas com a operação, números reais do banco |
| **Engenheiro de Dados** | *Como o dado chega, confiável e repetível?* | Data Lake medalhão no BigQuery, ingestão, deduplicação, mascaramento de PII, camada gold em views | Python, SQL, BigQuery, Cloud Storage |
| **Analista / Cientista de Dados** | *O que o dado diz, e o que ele não diz?* | EDA e testes de hipótese, modelo de risco de 13 variáveis, medição do teto, backtest, monitor de deriva | Python, scikit-learn, estatística aplicada |
| **DataOps / Engenheiro de Plataforma** | *Como isso roda sem depender de uma pessoa?* | Terraform, CI/CD no GitHub Actions, Workload Identity Federation, ambientes dev e prod | Terraform, GitHub Actions, IAM do GCP |
| **Analista de BI / Visualização** | *Como quem decide enxerga isso?* | Painel no Looker Studio, narrativa visual, ciclos de revisão | Looker Studio, modelagem de métricas |

Um sexto papel apareceu sem ter nome no escopo e merece registro: **o de quem duvida do número**. Voltamos a ele na Seção 5.

---

## 3. Quem exerceu o quê

### Ilan — Analista de Negócio, com incursões em Ciência de Dados

Formado em Economia, analista de produtos de conta corrente. Chegou ao projeto com a visão de negócio e sem experiência prévia em programação ou cloud.

**Papel principal:** definiu o problema, trouxe os números reais da operação (703 escalonamentos em 21 dias úteis, capacidade de 11,8 tickets por atendente/dia, 74% de uso médio e 123% no pico), escreveu o Caso de Negócio e decidiu os cortes das três faixas operacionais — que são decisão de negócio tirada da capacidade da equipe, não da estatística.

**Papel acumulado:** conduziu a modelagem do estágio 2 — escolha do alvo, exclusão das 4.958 conversas de disparo e ruído, separação por cliente, medição do teto da base. Executou a pipeline de ponta a ponta e publicou as duas tabelas na camada gold.

**A contribuição mais valiosa não foi técnica.** Quando o professor perguntou como um classificador de intenção chegava a 99,99% de acurácia, o grupo não soube responder — e a decisão do Ilan foi ir medir em vez de defender o número. A medição mostrou que o modelo lia o assunto de um texto gerado por template: recuperava uma coluna que já existia na base. O resultado foi descartado e substituído por um bem mais modesto e defensável inteiro.

Descartar o próprio melhor número, a três sprints do fim, é decisão de produto — e é a mais difícil de tomar quando o prazo aperta.

### Giovanna — Analista de BI, e o controle de qualidade do grupo

**Papel principal:** o painel no Looker Studio, do protótipo às revisões. Modelagem das métricas de visualização e a narrativa que o painel conta.

**Papel acumulado:** virou o portão de qualidade do projeto. A frase dela — ***"número que não rodamos é número que não defendemos"*** — deixou de ser opinião e virou regra: nenhum número entrou em entrega sem ter sido executado por alguém que não o escreveu.

Foi essa regra que obrigou a execução independente do modelo em duas máquinas diferentes, com resultados batendo na terceira casa decimal. É hoje um dos argumentos mais fortes da defesa.

### Jonathas — Engenheiro de Dados e DataOps

**Papel principal:** infraestrutura como código em Terraform, esteira de CI/CD no GitHub Actions, autenticação por Workload Identity Federation — sem chave de service account, portanto sem credencial de longa duração para vazar.

**Papel acumulado:** construiu por conta própria um segundo estágio do modelo, com histórico de sentimento do cliente e janela temporal sem vazamento por construção.

**O detalhe que define o perfil dele:** mediu o efeito do histórico de sentimento e encontrou **zero**. Reportou como zero. Um perfil menos maduro teria escondido, inflado ou simplesmente não medido. Reportar um ganho nulo como nulo é comportamento de engenheiro, não de estudante.

Foi também o primeiro a rodar a pipeline inteira numa máquina que não era a de quem a escreveu — o que expôs quatro erros de reprodutibilidade que ninguém teria encontrado de outro jeito.

---

## 4. O mapa de sobreposição

| Perfil | Ilan | Giovanna | Jonathas |
|---|:---:|:---:|:---:|
| Analista de Negócio / Produto | ●●● | ● | — |
| Engenheiro de Dados | ●● | — | ●●● |
| Analista / Cientista de Dados | ●●● | ● | ●● |
| DataOps / Plataforma | — | — | ●●● |
| Analista de BI / Visualização | ● | ●●● | — |
| Controle de qualidade | ●● | ●●● | ●● |

*●●● principal · ●● significativo · ● pontual*

**Nenhuma coluna tem uma só linha preenchida.** Em time pequeno isso não é improviso: é a condição normal. A leitura que fica é que a especialização é um luxo de estrutura grande — e que saber transitar entre perfis vale mais no começo de carreira do que dominar um só.

---

## 5. Onde os perfis se encontram é onde o projeto quase errou

Três erros graves foram pegos. **Nenhum foi pego por quem o cometeu, e nenhum estava dentro de um único perfil.**

**O denominador inflado.** A taxa de falha do atendimento humano estava calculada sobre as conversas com área registrada — um subconjunto que exclui três em cada cinco casos resolvidos. O número publicado estava 2,01× maior: 32,0% eram na verdade 15,9%. Duas conclusões caíram junto e estão registradas como retratadas. **Fronteira:** quem escreve a consulta e quem conhece a operação. Um denominador errado não parece errado dentro do SQL; parece errado para quem sabe como o atendimento funciona na prática.

**O classificador com 99,99%.** Vazamento de variável disfarçado de resultado excelente. **Quem perguntou foi o professor, não o grupo** — e vale registrar assim. O mérito do grupo foi a resposta: medir em vez de defender, e descartar o resultado quando a medição não sustentou. **Fronteira:** o time e a revisão externa. Nenhum dos três havia estranhado o número sozinho.

**O modelo reportado sobre a população errada.** Uma implementação reportava AUC 0,7039 porque incluía as 4.958 conversas que nunca geram atendimento; filtradas, 0,667. A outra já as excluía. **Fronteira:** duas implementações independentes do mesmo modelo. A divergência só apareceu porque existiam duas — com uma só, o número inflado teria ido para a entrega sem que ninguém notasse.

> **A conclusão de carreira que tiramos disto:** o valor de um profissional de dados não está só no que ele produz dentro da própria especialidade. Está na capacidade de **olhar o trabalho do perfil vizinho e perguntar "esse número faz sentido?"** — e em aceitar a mesma pergunta vinda de fora sem defender o número por orgulho. Os três erros acima custariam a credibilidade da entrega inteira. Dois foram pegos na costura entre perfis; o terceiro veio da revisão externa, que é a costura de última instância.

---

## 6. O papel da IA, e o que ele muda nas trilhas

Seria desonesto descrever os perfis acima sem registrar isto: **boa parte do código deste projeto foi escrita por uma IA assistente (Claude), sob direção do grupo.** Os scripts de pipeline, o modelo, os testes de hipótese, o simulador e boa parte da documentação passaram por ela.

O que **não** foi terceirizado, e é onde o trabalho realmente aconteceu:

- **decidir qual pergunta valia a pena responder** — o alvo do modelo foi discutido e trocado uma vez, por decisão do grupo
- **desconfiar dos resultados** — o 99,99%, o denominador e o AUC inflado foram pegos por pessoas, não pela ferramenta; em dois dos três casos a ferramenta havia produzido o número errado sem sinalizar nada
- **decidir os cortes operacionais** a partir da capacidade real da equipe de atendimento
- **declarar limites** — o que é premissa do gerador e o que é achado; a base sintética; o teto da base
- **executar e conferir** — a regra de não defender número que não se rodou

**A leitura para a trilha de carreira é direta.** A parte do trabalho que a ferramenta faz bem — escrever código, lembrar sintaxe, montar boilerplate — deixou de ser diferencial competitivo. A parte que ela não faz sozinha — formular a pergunta certa, reconhecer quando um resultado é bom demais para ser verdade, traduzir estatística em decisão operacional, assumir a responsabilidade pelo número — é exatamente o que passa a definir o profissional.

Isso não reduz a necessidade de fundamento técnico: **é impossível desconfiar de um resultado que não se entende.** O grupo só conseguiu pegar os três erros porque entendia o suficiente de denominador, de vazamento e de população para olhar e estranhar.

---

## 7. As trilhas, daqui para frente

Para cada perfil, o caminho de desenvolvimento a partir de onde cada um está de fato.

### Analista de Negócio / Produto de Dados → **Ilan**

*Ponto de partida:* Economia, produto bancário, SQL e Python em nível funcional adquiridos no semestre.

| Horizonte | O que desenvolver |
|---|---|
| Curto | SQL analítico com autonomia — janelas, CTEs, leitura de plano de execução. É o que permite auditar o trabalho alheio sem depender de ninguém |
| Médio | Fundamento estatístico aplicado a decisão: intervalo de confiança, significância, viés de seleção. O suficiente para não ser enganado por um gráfico |
| Longo | Product Manager de dados ou Head de Analytics — o papel de quem decide o que a área constrói e defende o resultado diante do negócio |

*Diferencial já construído:* saber ler a operação real. Poucos profissionais de dados conseguem dizer quantos tickets por dia uma equipe aguenta.

### Engenheiro de Dados e DataOps → **Jonathas**

*Ponto de partida:* Terraform, CI/CD, IAM e BigQuery exercitados de ponta a ponta.

| Horizonte | O que desenvolver |
|---|---|
| Curto | Orquestração de verdade — Airflow ou Cloud Composer, com dependências, retentativas e SLA |
| Médio | Certificação de engenharia de dados em nuvem; testes de qualidade de dado como parte da esteira, não como conferência manual |
| Longo | Arquiteto de dados ou Platform Engineer — quem define o padrão que os outros times seguem |

*Diferencial já construído:* fez infraestrutura como código sem credencial de longa duração, o que muita equipe profissional ainda não faz.

### Analista de BI / Visualização → **Giovanna**

*Ponto de partida:* Looker Studio, modelagem de métricas, ciclos de revisão sobre crítica.

| Horizonte | O que desenvolver |
|---|---|
| Curto | Modelagem semântica — métricas definidas em um lugar só, não repetidas em cada gráfico. É o que separa painel de planilha bonita |
| Médio | Ferramenta de mercado mais ampla (Power BI ou Tableau) e camada semântica versionada |
| Longo | Analytics Engineer — o perfil que hoje mais cresce, entre o engenheiro e o analista |

*Diferencial já construído:* a exigência de executar antes de publicar. É disciplina de engenharia aplicada a BI, e é rara.

### O perfil que o projeto sugere e que ninguém ocupou

**Analista de Governança de Dados.** Catálogo, linhagem, classificação de sensibilidade, política de acesso e retenção. No Kenzie 360 isso existe implementado — rastreabilidade de ingestão, mascaramento de PII, acesso restrito por camada — mas **distribuído entre as três pessoas**, sem dono.

Em ambiente bancário esse papel é obrigatório e tende a ser o primeiro a ser contratado quando a área de dados amadurece. Fica registrado como a lacuna que o próprio projeto revelou.

---

## 8. O que levamos

1. **Em time pequeno, todo mundo acumula papel.** Isso não é falha de planejamento — é a condição, e prepara melhor do que a especialização precoce.
2. **A costura entre perfis é onde o erro aparece.** Os três erros graves do projeto foram pegos ali, nunca dentro de uma especialidade.
3. **A IA move a fronteira do que é diferencial.** Escrever código deixou de ser o gargalo; desconfiar do resultado passou a ser o trabalho — e desconfiar exige entender.
4. **Reportar zero como zero é competência técnica.** O ganho nulo do histórico de sentimento e o AUC modesto de 0,6729 valem mais, na defesa, do que qualquer número inflado teria valido.
