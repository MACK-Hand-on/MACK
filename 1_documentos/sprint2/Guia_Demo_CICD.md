# CI/CD e IaC — guia para explicar e roteiro da demonstração

**Projeto Kenzie 360 · Sprint 2 · quinta-feira**
**Público:** Prof. Gustavo Ferreira e o grupo · **Tempo:** 10 a 15 minutos

---

# PARTE 1 — O que você precisa dominar antes

Não decore comandos. Domine estas cinco ideias e você responde qualquer pergunta.

## 1. O problema que isso resolve

Antes, o ambiente foi criado clicando no console do Google Cloud. Funciona — até alguém precisar saber *por que* um bucket está configurado de um jeito, ou recriar o ambiente, ou descobrir quem mudou o quê.

**A analogia que vale usar, porque é do seu mundo:** é a diferença entre um produto que existe só configurado no sistema e um produto que tem **ficha cadastral**. Se alguém altera o limite de uma conta direto no sistema sem passar pela ficha, ninguém mais sabe qual é a regra verdadeira — a do papel ou a do sistema. Infraestrutura como código diz: **a ficha é a verdade, e o sistema segue a ficha.**

O termo técnico para o problema é *drift*: o ambiente real se afasta da documentação, silenciosamente, ao longo do tempo.

## 2. Terraform: plano, aplicação e estado

Três palavras, e é tudo que o Terraform é:

| Termo | O que é | Analogia bancária |
|---|---|---|
| `plan` | Simula e mostra o que mudaria. Não muda nada. | A prévia do lançamento antes de confirmar a transferência |
| `apply` | Executa o que o plano descreveu | A confirmação |
| *state* | O registro do que o Terraform acredita que existe | O razão contábil |

**A frase que resume:** *o plano é a prévia, o apply é a confirmação, e o state é o razão.*

`terraform import` é a operação de **conciliação**: o recurso já existe no mundo real, e você o registra no razão sem mexer nele. Foi o que fizemos — o ambiente estava criado à mão, e o Terraform passou a reconhecê-lo sem recriar nada.

## 3. A esteira de CI/CD é uma alçada de aprovação

Banco tem alçada: quem aprova até quanto, o que exige segunda assinatura, o que precisa de comitê. A esteira é exatamente isso, com duas diferenças — **é automática e não tem como contornar.**

Quatro controles encadeados:

| Etapa | O que trava |
|---|---|
| Abertura do PR | Verificação automática: formatação, sintaxe, boas práticas (tflint), segurança (checkov) |
| Revisão | O plano vira comentário no PR, legível por quem não é técnico |
| Merge | Exige Pull Request aprovado por **outra pessoa**; escrita direta na branch principal está bloqueada |
| Aplicação | Para e espera aprovação humana, com o comentário do aprovador gravado |

**A prova de que não é teatro:** na nossa execução, quem mesclou o código (Jonathas) e quem autorizou a mudança na infraestrutura (Ilan) foram pessoas diferentes. Ninguém combinou isso — é o desenho que força.

## 4. Autenticação sem senha (Workload Identity Federation)

Este é o ponto que mais impressiona em contexto bancário, e é simples de explicar.

O jeito comum de dar acesso ao GitHub seria gerar uma chave da conta de serviço e guardá-la como segredo. **Problema:** é um arquivo, ele vale para sempre, e se vazar continua valendo até alguém lembrar de revogar.

**A analogia:** em vez de dar ao fornecedor uma cópia da chave do prédio, você emite um crachá de visitante que vale dez minutos e só abre uma sala.

Como funciona: o GitHub emite uma identidade temporária dizendo "sou a execução do repositório X". O GCP verifica a assinatura e, se a origem bater com a regra, empresta a permissão por poucos minutos. **Não existe arquivo de credencial.** Nada para vazar.

E a autorização é dupla: uma condição no provedor restringe a organização dona do repositório, e um vínculo na conta de serviço restringe o repositório exato.

> Se quiser um detalhe concreto para citar: nesta mesma sprint encontramos uma chave de API exposta em texto puro num arquivo de configuração local da minha máquina. O risco não é hipotético.

## 5. Defesa em profundidade

Este é o conceito que amarra a demonstração — e o mais importante de acertar.

Se alguém tentasse aplicar uma mudança destrutiva, existem **três travas independentes**:

| # | Trava | O que faz |
|---|---|---|
| 1 | Leitura do plano | O plano mostra `must be replaced` antes de qualquer coisa acontecer |
| 2 | Aprovação humana | O apply não roda sem alguém autorizar |
| 3 | Configuração do recurso | `force_destroy = false` impede apagar bucket com conteúdo; dataset do BigQuery com tabelas também recusa exclusão |

**A afirmação correta:** *se as duas primeiras falhassem, o apply daria erro e deixaria o estado dessincronizado — chato de consertar, mas não seria perda de dado.*

**Não diga** "isso apagaria a base". Seria exagero, e um professor de engenharia de dados vai perguntar sobre o `force_destroy`. A resposta boa é justamente que existem camadas, e que segurança que depende de uma trava só não é segurança.

---

# PARTE 2 — As perguntas que você vai receber

Separei em fáceis, técnicas e desconfortáveis. **As desconfortáveis são as importantes** — se você levantar o ponto antes de perguntarem, a fraqueza vira maturidade.

## Fáceis

**"Por que não fazer pelo console?"**
Porque o console não deixa rastro do porquê. Com código, cada mudança tem autor, revisor, data e justificativa — e o ambiente pode ser recriado. O console é ótimo para explorar; péssimo como fonte da verdade.

**"Quanto custou?"**
Zero. Tudo dentro do Free Tier: 5,4% da franquia de armazenamento do BigQuery e 0,04% da de consultas. O GitHub Actions é gratuito para repositório público.

**"Quanto tempo levou?"**
Cerca de duas horas de execução, distribuídas em duas noites. A revisão do código levou mais tempo que a implantação.

## Técnicas

**"E se duas pessoas rodarem o Terraform ao mesmo tempo?"**
O estado fica num bucket do Cloud Storage, que faz travamento nativo. A segunda execução espera a primeira terminar. Sem isso, duas execuções simultâneas corromperiam o estado.

**"Por que aplicar em dev e não em produção?"**
Porque só existe um projeto GCP no escopo acadêmico. O ambiente de produção está descrito no código e os jobs existem, mas só rodam por acionamento manual. Preferimos declarar isso a fingir que temos dois ambientes.

**"O `apply` roda o mesmo plano que foi revisado?"**
Sim, e isso foi deliberado. O job salva o plano em arquivo e o apply consome aquele arquivo. Se ele gerasse um plano novo na hora, você aprovaria uma coisa e aplicaria outra.

**"Vocês usaram Composer?"**
Não. Não tem free tier e custa cerca de US$ 525 por mês rodando continuamente — sozinho inviabilizaria o projeto. Está documentado como arquitetura alvo de produção, com o trade-off explícito. A substituição é Cloud Scheduler com Cloud Run Jobs.

**"O que o checkov apontou?"**
Está em modo permissivo, avisando sem quebrar o build. Ele aponta ausência de chave de criptografia gerenciada pelo cliente e de log de acesso ao bucket — exigências de produção bancária que estão fora do escopo acadêmico. A decisão foi consciente, não desconhecimento.

## Desconfortáveis — levante você primeiro

**"As permissões não estão largas demais?"**
Estão, e sabemos. A conta de serviço tem administração de Storage e BigQuery no projeto inteiro. O correto seria restringir aos recursos específicos. Em produção seria inaceitável; no escopo acadêmico foi uma escolha de tempo. E o próprio checkov aponta isso — o que mostra a ferramenta funcionando.

**"Vocês testaram rollback?"**
Não exercitamos. O caminho seria reverter o commit e aplicar de novo, e o bucket tem versionamento ligado. Mas não simulamos uma falha real, então não posso afirmar que funciona — só que está desenhado.

**"O código da pipeline de dados está versionado?"**
Ainda não, e é a nossa maior lacuna. Versionamos a infraestrutura; os scripts de carga e o SQL das camadas estão em pasta local e no Drive. É o próximo passo, e é onde a crítica pega.

**"Isso escala para um banco de verdade?"**
O desenho sim; a configuração não. Mudaria: projetos separados por ambiente, menor privilégio de verdade, chaves gerenciadas pelo cliente, aprovação por um time diferente de quem escreve, e orquestração paga.

---

# PARTE 3 — Roteiro da demonstração

## Antes da aula (30 minutos antes)

**Passo 1 — Conferir que está tudo de pé**

```bash
cd ~/MACK
git checkout main && git pull
gh auth status
gcloud config get-value project
gh api repos/MACK-Hand-on/MACK/branches/main/protection --jq '.required_status_checks'
```

> Se o último comando devolver `null`, você não chegou a rodar aquele comando do status check obrigatório. Não atrapalha a demo — só não mencione essa trava.

**Passo 2 — Abrir o PR "bom" (a mudança inofensiva)**

Acrescenta um rótulo de governança. Muda os 4 recursos, não destrói nada.

```bash
git checkout -b demo/rotulo-de-dono

python3 - <<'EOF'
p = "infra/modules/data-lake/main.tf"
s = open(p).read()
s = s.replace('    ambiente = var.environment\n  }',
              '    ambiente = var.environment\n    dono     = "engenharia-de-dados"\n  }', 1)
open(p, "w").write(s)
EOF

terraform fmt -recursive infra/
git commit -am "Acrescentar rotulo de dono para rastreio de custo por area"
git push -u origin demo/rotulo-de-dono
gh pr create --title "Acrescentar rótulo de dono aos recursos" \
  --body "Rótulo de governança para rastrear custo por área responsável. Muda apenas metadados." --base main
```

**Passo 3 — Abrir o PR "perigoso" (que NÃO será mesclado)**

```bash
git checkout main
git checkout -b demo/NAO-MESCLAR-troca-de-regiao
sed -i 's/region     = "us-central1"/region     = "southamerica-east1"/' infra/environments/dev/terraform.tfvars
git commit -am "DEMONSTRACAO - NAO MESCLAR - troca de regiao"
git push -u origin demo/NAO-MESCLAR-troca-de-regiao
gh pr create --title "[NÃO MESCLAR] Demonstração — troca de região" \
  --body "Aberto apenas para demonstrar a esteira barrando uma mudança destrutiva. NÃO MESCLAR. Será fechado após a apresentação." --base main
```

**Passo 4 — Conferir que os dois planos já rodaram**

```bash
gh pr checks 2
gh pr checks 3
```

> Os números dos PRs podem variar — confira com `gh pr list`.

**Passo 5 — Deixar as abas abertas no navegador**

1. O PR bom, na aba Files changed
2. O PR bom, no comentário do plano
3. O PR perigoso, no comentário do plano
4. A aba Actions

**Passo 6 — Plano B**

Salve as capturas de tela da execução anterior numa pasta acessível. Se a internet cair, você narra pelas imagens. A história continua inteira; só perde o ao vivo.

---

## Durante — roteiro de 13 minutos

### 0:00 a 2:00 — O problema (sem tela)

> "O ambiente do nosso data lake foi criado clicando no console. Funciona. Mas ninguém consegue responder por que um bucket está configurado de um jeito, quem mudou o quê, nem recriar o ambiente do zero.
>
> É a diferença entre um produto que existe só configurado no sistema e um produto que tem ficha cadastral. Infraestrutura como código diz: a ficha é a verdade, e o sistema segue a ficha."

### 2:00 a 4:00 — O código (aba 1)

Mostre a estrutura `modules/` + `environments/`.

> "O módulo é a receita. Os ambientes só passam parâmetros. Este arquivo descreve os buckets e datasets que a gente já tem no BigQuery — não uma cópia, os mesmos. O Terraform os adotou por importação, que é uma conciliação: o recurso já existe, e a gente registra sem mexer nele."

### 4:00 a 8:00 — A mudança que passa (abas 2 e 4)

Mostre o comentário do plano no PR.

> "Abri este PR acrescentando um rótulo de governança. Repare que o robô comentou aqui embaixo o que aconteceria: quatro recursos alterados, nada criado, nada destruído. Quem revisa não precisa saber Terraform — precisa saber ler esta linha."

**Merge ao vivo.** Vá para a aba Actions.

> "Agora vejam o que ele faz: para. Ele não aplica."

Espere aparecer "Review pending deployments". **Este é o momento da apresentação — deixe o silêncio trabalhar.**

> "A esteira executou tudo o que podia sozinha e parou para pedir autorização. Enquanto ninguém clicar, nada muda no ambiente. Na execução de ontem ela ficou vinte e sete minutos parada.
>
> E repare em quem pediu: o Jonathas mesclou o código, eu autorizo a mudança na infraestrutura. Duas pessoas, dois pontos de controle. A gente não combinou — é o desenho que força."

Aprove. Mostre o `Apply complete`.

### 8:00 a 11:00 — A mudança que é barrada (aba 3)

> "Agora o contrário. Abri um segundo PR trocando a região dos datasets — a mudança mais perigosa que existe aqui."

Mostre o comentário do plano, com as linhas `must be replaced`.

> "O plano avisa: estes recursos precisariam ser destruídos e recriados. Este PR não vai ser mesclado. Vou fechá-lo.
>
> E aqui está o ponto que eu quero deixar: mesmo que alguém mesclasse por engano e aprovasse, o `force_destroy` do bucket está em falso e o dataset tem tabelas dentro — os dois recusariam a exclusão. O apply daria erro e deixaria o estado dessincronizado. Chato de consertar, mas não perderíamos dado.
>
> São três travas independentes. Segurança que depende de uma trava só não é segurança."

Feche o PR ao vivo:

```bash
gh pr close 3 --comment "PR de demonstração. Fechado sem merge, como previsto."
```

### 11:00 a 13:00 — O fechamento

> "O que eu não esperava era que a esteira encontrasse coisa de verdade. Foram três:
>
> Primeira: o tflint apontou que o nosso módulo não declarava de que versão do Terraform depende. Isso passou por duas revisões humanas — a de quem escreveu e a de quem revisou — e nenhuma pegou. A ferramenta pegou em fração de segundo.
>
> Segunda: o bucket dos dados crus estava com a proteção contra exposição pública herdada, não imposta. A infraestrutura como código não só documentou o ambiente — corrigiu uma falha de segurança que existia no que foi feito à mão.
>
> Terceira, e a minha favorita: o ambiente de aprovação de produção existia sem nenhuma regra. O GitHub cria sozinho qualquer ambiente citado num workflow. Ele aparentava ser um portão de aprovação e não era. Só descobrimos consultando por API — a interface mostra o ambiente existindo, e isso basta para dar a impressão errada.
>
> Os três têm a mesma natureza: eram controles que existiam no papel e não no sistema. Nenhum apareceria em teste, porque nada estava quebrado — só desprotegido."

---

## Depois da aula

```bash
gh pr list --state open        # conferir que o PR perigoso está fechado
git checkout main && git pull
```

O rótulo de dono pode ficar — é uma melhoria real de governança.

---

## Se der errado ao vivo

| Sintoma | O que fazer |
|---|---|
| Internet caiu | Narre pelas capturas de tela. A história não depende do ao vivo |
| O job falhou | **Use a favor:** "é exatamente para isso que a esteira existe — o erro aparece aqui, e não no ambiente" |
| Alguém mesclou o PR perigoso | Não entre em pânico. O apply vai parar pedindo aprovação. **Rejeite.** Se já tiver rodado, ele falhará nas travas do recurso |
| Perguntaram algo que você não sabe | "Não testamos isso, então não vou afirmar." Vale mais que uma resposta inventada — e um professor reconhece a diferença |

## As três frases, se você só puder dizer três

1. Infraestrutura como código significa que a planta do ambiente é o documento oficial, e o ambiente segue a planta.
2. A esteira é uma alçada de aprovação automatizada: nada muda sem plano revisado e assinatura humana.
3. E ela não é enfeite — encontrou três problemas reais que a nossa revisão humana não pegou.
