# Memorial de execução — CI/CD e IaC

**Projeto Kenzie 360 · Sprint 2 · Card 2**
**Executado por:** Ilan Schapira · **Autoria do código original:** Jonathas Borges
**Repositório:** https://github.com/MACK-Hand-on/MACK — público
*(originalmente em `Jb0rges/MACK`; transferido para a organização do grupo em 26/08 — ver a seção sobre a decisão D4)*

Documento de registro: o que foi feito, por que foi feito assim, e o que cada decisão evitou.
Serve de roteiro para a apresentação ao Prof. Gustavo Ferreira.

---

## Contexto: por que houve uma etapa de correção

O Jonathas entregou a infraestrutura como código (Terraform) e a esteira de CI/CD. A estrutura estava correta — módulos reutilizáveis, ambientes separados, bucket com proteção contra exposição pública, autenticação sem chave estática.

O que impedia rodar não era qualidade de código: eram **divergências entre o que o Terraform descrevia e o ambiente que já existia no GCP**, provisionado manualmente na Trilha 0.

Três divergências bloqueantes:

| # | Divergência | Consequência se aplicado como estava |
|---|---|---|
| 1 | Região `southamerica-east1` vs `us-central1` real | **O BigQuery não executa join entre datasets de regiões diferentes.** A consulta falha, não fica lenta. Criaria um ambiente paralelo incapaz de conversar com o que tem os dados |
| 2 | Nomes de recursos diferentes dos reais | `terraform apply` criaria um **segundo data lake, vazio**, ao lado do que tem 405 mil mensagens |
| 3 | Camada bronze ausente no módulo | Nossa arquitetura tem três datasets no BigQuery; o módulo descrevia dois |

**Este é o achado conceitual da etapa:** infraestrutura como código só entrega valor quando o código descreve o ambiente que existe de fato. Um Terraform sintaticamente perfeito que aponta para nomes errados é mais perigoso do que não ter Terraform nenhum — porque dá a falsa sensação de que o ambiente está versionado.

---

## Decisão de projeto: adotar em vez de recriar

Havia duas saídas para a divergência de nomes:

| Opção | Como | Por que foi/não foi escolhida |
|---|---|---|
| **Alinhar os nomes e adotar** ✔ | Ajustar o código para os nomes reais e usar `terraform import` | Preserva os dados e toda a pipeline que já aponta para esses nomes |
| Recriar com os nomes novos | Aplicar como estava e migrar dados e scripts | Retrabalho puro, sem ganho |

**Como foi implementado sem descartar o trabalho original:** os nomes viraram **variáveis opcionais**. Quando nenhum nome é informado, o módulo continua gerando o padrão que o Jonathas escreveu (`${project_id}-kenzie-raw-${environment}`). O ambiente `dev` informa os nomes reais; o `prod` usa o padrão gerado.

O módulo continua reutilizável, e a autoria do desenho original se mantém.

---

## Decisão de processo: branch e Pull Request, nunca direto na main

Mesmo com acesso de escrita liberado, o trabalho foi feito em branch com PR para revisão do autor original. Três razões:

1. O repositório e o card são dele; mudar quem executa não muda quem revisa.
2. O PR é o registro auditável da mudança — quem propôs, quem revisou, o que a esteira verificou.
3. É a prática que a própria esteira exige (proteção de branch na Fase D).

---

## Correções na esteira, além dos três bloqueantes

| Ajuste | Problema que resolve |
|---|---|
| `ci-cd.yml` movido para `docs/proposta-cicd-aplicacao.yml` | Era o pipeline da *aplicação* do chat, referenciando `app/`, `Dockerfile`, `requirements.txt` — nenhum existe no repositório. Falhava em **todo push**. Um CI permanentemente vermelho ensina o time a ignorar o alerta |
| `tflint` e `checkov` no job `validate` | Estavam previstos no documento conceitual do próprio autor, mas não tinham ido para o código. `checkov` é o que detecta automaticamente bucket público ou IAM permissivo demais |
| Plano publicado como comentário no PR | O README prometia isso; o plano só ia para o log da aba Actions. Publicar no PR é o que torna a revisão viável para quem não é técnico |
| Job `apply-dev` acrescentado | O fluxo anterior nunca aplicava em dev — validava um plano contra um ambiente que não existia |
| `apply-prod` passou a ser manual | Antes aplicava a cada merge, num projeto GCP de produção que ainda não existe |
| `apply` usa o arquivo `tfplan` gerado no mesmo job | Garante que o que é aplicado é **exatamente** o que foi revisado, não um plano novo gerado depois |
| `.gitignore` criado | O repositório não tinha um. `.terraform/`, arquivos de state e chaves `.json` de service account podiam ser versionados por acidente |

---

## Registro de execução

### Fase A — proposta de mudança versionada

| Passo | Comando / ação | Resultado |
|---|---|---|
| Autenticação | `gh auth login` (fluxo por navegador) | Conta `idschapira`, escopos `repo` e `workflow` |
| Clone | `gh repo clone Jb0rges/MACK` | Base confirmada em `a0c4e1d` |
| Branch | `git checkout -b correcoes/alinhamento-ambiente` | — |
| Aplicação do patch | `git am` + `git commit --amend --reset-author` | Commit `fd14645` — 15 arquivos, +432 / −98 |
| Push | `git push -u origin correcoes/...` | Branch no remoto; `main` intacta |

**Detalhe técnico que vale citar:** o Git detectou o `ci-cd.yml` como *rename 100%*, não como exclusão + criação. O histórico do arquivo se preserva e a autoria original não se perde.

**Decisão de sequenciamento:** o PR foi deixado para depois da Fase B. Abrir o PR dispara a esteira, e o job `plan-dev` exige credenciais que ainda não existiam — o PR nasceria com check vermelho. Push de branch não dispara nada (o gatilho de `push` está limitado à `main`), então o trabalho ficou salvo sem gerar ruído.

### Fase B — autenticação sem chave estática

**O conceito:** em vez de guardar uma credencial do GCP dentro do GitHub, o GCP passa a **confiar** que o GitHub é quem diz ser — e apenas para um repositório específico. A técnica é **Workload Identity Federation** (OIDC).

**Por que isso importa num contexto bancário:** uma chave de service account é um arquivo que, uma vez vazado, continua válido até alguém lembrar de revogá-lo. Nesta mesma sprint encontramos uma chave de API exposta em texto puro num arquivo de configuração local — o risco não é teórico. Com federação, não existe arquivo de credencial: o GitHub apresenta um token de curta duração emitido na hora, e o GCP valida a origem.

| Passo | O que foi feito |
|---|---|
| B1 | APIs habilitadas: `iamcredentials`, `sts`, `iam`, `cloudresourcemanager`. Conta de serviço `github-actions-terraform` criada |
| B2 | Papéis `roles/storage.admin` e `roles/bigquery.admin` concedidos no projeto |
| B3 | Pool `github` e provider OIDC `kenzie-mack` criados, com trava de origem |
| B4 | Repositório `Jb0rges/MACK` autorizado a assumir a conta de serviço |

**A trava de origem, e por que ela é o ponto central da Fase B.** O provider foi criado com:

```
--attribute-condition="assertion.repository_owner == 'Jb0rges'"
```

Isso significa: o GCP só aceita um token do GitHub se o dono do repositório for `Jb0rges`. Sem essa linha, **qualquer repositório do GitHub no mundo** poderia solicitar um token para o projeto `kenzie-360-mba`. É o erro de configuração mais comum em Workload Identity Federation.

Há um segundo cadeado, independente: o binding da conta de serviço é em `attribute.repository/Jb0rges/MACK` — o repositório exato, não apenas o dono.

### ⚠ Dependência registrada: a decisão D4

A decisão D4 (o repositório final fica na conta do Jonathas ou vai para uma organização do grupo) **impacta diretamente esta configuração**.

Transferir o repositório muda o `repository_owner`, e os dois cadeados acima passam a rejeitar a autenticação. Não há perda de dado nem migração — o conserto são dois comandos (atualizar a condição do provider e acrescentar o binding do novo caminho) — mas precisa ser feito **junto** com a transferência, não depois.

Se a transferência acontecer perto da entrega sem esse ajuste, a esteira para de autenticar e o sintoma aparece como falha genérica de permissão, difícil de diagnosticar sob pressão.


**Ponto de honestidade técnica a declarar na apresentação:** conceder `storage.admin` e `bigquery.admin` no projeto inteiro é mais permissão do que o princípio do menor privilégio recomenda. Em produção, restringiríamos aos recursos específicos. A decisão foi consciente, considerando o escopo acadêmico — e o `checkov` na esteira deve apontar exatamente isso, o que demonstra a ferramenta funcionando.

*(Registro em andamento — atualizado a cada fase concluída.)*

### Fase C — adoção do ambiente existente (`terraform import`)

O `terraform import` não cria nem altera nada no GCP. Ele registra no *state* que um recurso já existente corresponde a um bloco do código. É a operação que converte um ambiente construído manualmente em um ambiente versionado.

| Recurso | Identificador usado no import |
|---|---|
| Bucket RAW | `kenzie360-raw-ids26` |
| Dataset bronze | `kenzie-360-mba/kenzie360_bronze` |
| Dataset silver | `kenzie-360-mba/kenzie360_silver` |
| Dataset gold | `kenzie-360-mba/kenzie360_gold` |

*Detalhe:* bucket é identificado só pelo nome (é único no mundo inteiro); dataset exige `projeto/dataset` (só é único dentro do projeto).

#### O plano — e por que ele foi lido antes de qualquer aplicação

Resultado: **`Plan: 0 to add, 4 to change, 0 to destroy`**. Nenhuma linha de `must be replaced`, `forces replacement` ou `will be destroyed`.

As quatro mudanças previstas:

| Mudança | Natureza |
|---|---|
| Rótulos `camada` / `projeto` / `ambiente` nos 4 recursos | Governança — permite rastrear custo e propriedade por camada |
| Descrições dos datasets padronizadas | Documentação |
| `public_access_prevention`: `inherited` → **`enforced`** | **Ganho de segurança real** |
| Bucket RAW: versionamento ligado + regra de ciclo de vida de 365 dias | Recuperação e retenção |

**Dois pontos que merecem destaque na apresentação:**

1. **O bucket RAW não estava protegido contra exposição pública.** Estava em `inherited`, que herda a política do projeto; o `apply` o coloca em `enforced`, que impede tornar o bucket público mesmo por engano. Num contexto de dados de correntistas, é o tipo de configuração cuja ausência vira incidente. A IaC não só documentou o ambiente — ela **corrigiu** uma lacuna de segurança que existia no ambiente feito à mão.

2. **A regra de ciclo de vida é a única mudança com consequência futura.** Objetos no bucket RAW passam a ser excluídos automaticamente após 365 dias. É intencional (dado cru não deve acumular custo e risco indefinidamente) e sem efeito no horizonte do projeto — a base vai de fev a ago/2026. Mas é uma decisão de retenção, não um detalhe técnico, e por isso está registrada aqui.

#### O protocolo de leitura do plano

Antes do `apply`, foi aplicada uma regra de decisão explícita:

| Resultado do plano | Ação |
|---|---|
| `0 to destroy` e nenhuma linha de substituição | Seguir |
| Qualquer `destroy`, `must be replaced` ou `forces replacement` | **Parar** |

**A razão de a regra ser tão rígida:** alterar a `location` de um dataset do BigQuery não é uma modificação — é destruir e recriar, com o conteúdo junto. A causa mais provável de uma linha de `destroy` neste projeto seria justamente uma divergência de região, que era o bloqueante nº 1 identificado na revisão. O protocolo existe para que o erro apareça no plano, e não depois do apply.

**Decisão de sequenciamento:** o `apply` **não** foi executado localmente. Foi deixado para a esteira, após o merge do PR e com aprovação manual, para demonstrar o ciclo completo: plano revisado → aprovação humana → aplicação automatizada. O plano é lido duas vezes antes — uma localmente, outra como comentário no PR.

---

## O caso concreto do valor da automação

Na primeira execução da esteira, o job `Validar Terraform` falhou. Não por erro de configuração nossa — o **`tflint` encontrou um problema real de qualidade**:

```
Missing version constraint for provider "google" in `required_providers`
terraform "required_version" attribute is required
```

**O problema.** Os dois ambientes (`dev` e `prod`) declaravam de que versão do Terraform e do provider dependiam. O **módulo** não declarava nada — funcionava por herdar o que o ambiente que o chamou tivesse configurado. Um módulo assim quebra de forma silenciosa quando reutilizado em outro contexto com versão diferente do provider. É uma dependência implícita, exatamente o tipo de defeito que não aparece em teste e só se manifesta muito depois.

**Por que este caso é forte para a apresentação.** Esse problema passou por duas revisões humanas — a do autor ao escrever o módulo e a da revisão técnica que originou este PR — e nenhuma das duas o pegou. Uma ferramenta de análise estática pegou em 0,3 segundo, na primeira vez que rodou.

É um argumento empírico, e não retórico, para a existência da esteira: não se trata de "adicionamos lint porque é boa prática", e sim de "o lint achou o que nós dois não achamos".

**Correção:** arquivo `infra/modules/data-lake/versions.tf` declarando `required_version` e `required_providers` no próprio módulo.

---

## Validação de ponta a ponta pela própria esteira

Após a correção, todos os checks passaram. E o job `Plano - Ambiente Dev` publicou no Pull Request um comentário terminando em:

```
Plan: 0 to add, 4 to change, 0 to destroy.
Saved the plan to: tfplan
```

**Idêntico ao plano executado localmente.** Isso valida, de uma só vez e sem depender de afirmação de ninguém:

| O que ficou provado | Como |
|---|---|
| A federação de identidade funciona | O job autenticou no GCP sem nenhuma chave estática e leu o *state* remoto |
| O `terraform import` surtiu efeito | O plano vê 4 recursos existentes a ajustar, não 4 a criar |
| A publicação do plano no PR funciona | O comentário está lá, legível por quem não é técnico |
| O `apply` aplicará o que foi revisado | `Saved the plan to: tfplan` — o mesmo arquivo que o job de apply consome |


---

## O teste real da documentação: a decisão D4 se materializou

Na noite de 25/08 esta dependência foi registrada neste documento:

> Transferir o repositório muda o `repository_owner`, e os dois cadeados passam a rejeitar a autenticação. O conserto são dois comandos — mas precisa ser feito **junto** com a transferência, não depois.

Na manhã de 26/08, o repositório foi transferido de `Jb0rges/MACK` para a organização **`MACK-Hand-on/MACK`**.

**Como o problema foi detectado — antes de quebrar nada.** A transferência não foi anunciada. Ela apareceu como efeito colateral: uma chamada de API à configuração de environments retornou `HTTP 307 Moved Permanently`, e a URL de resposta trazia o novo caminho. O sintoma que se investigava era outro; a transferência apareceu no meio do output.

Se ninguém tivesse reparado, o sintoma seguinte seria uma falha genérica de permissão no job de autenticação — o tipo de erro que consome uma tarde para diagnosticar, especialmente porque nada no código teria mudado.

**A correção, exatamente como estava previsto:**

| Ajuste | Comando |
|---|---|
| Condição do provider → novo dono | `workload-identity-pools providers update-oidc --attribute-condition` |
| Binding da conta de serviço → novo caminho | `service-accounts add-iam-policy-binding` |

Sem migração, sem recriar recursos, sem perda de dado. Os secrets do GitHub sobreviveram à transferência.

**Higiene: a permissão órfã foi removida.** Após a correção, o binding continha os dois caminhos — o antigo e o novo. O antigo não era explorável (a condição do provider já rejeitaria qualquer token com `repository_owner == 'Jb0rges'`), mas foi removido mesmo assim. Permissão órfã é a origem do acúmulo silencioso de acesso: ninguém remove porque "não faz mal", e depois ninguém sabe mais o que cada linha concede.

**Validação:** o run foi reexecutado, emitindo um token OIDC novo já com a identidade `MACK-Hand-on/MACK`. Todos os checks passaram.

**A lição a levar para a banca.** O valor de documentar uma dependência não é burocrático. Aqui, o intervalo entre registrar o risco e ele acontecer foi de **doze horas** — e o conserto já estava escrito, com os comandos prontos. A alternativa seria descobrir o problema por uma mensagem de erro opaca, em cima da entrega.


---

## Fechamento: a esteira alterou infraestrutura com aprovação humana

### O que aconteceu, na ordem

1. **Jonathas revisou e mesclou** o PR #1 na `main`.
2. O merge disparou o workflow, que rodou `Validar Terraform` (44s, verde) e **parou** no job `Aplicar - Ambiente Dev`, com a mensagem `gcp-dev waiting for review`.
3. O run ficou **27 minutos parado** aguardando decisão humana.
4. **Ilan aprovou** o deploy no environment `gcp-dev`, registrando o comentário `Plano revisado: 0 to add, 4 to change, 0 to destroy`.
5. O `terraform apply` executou o arquivo `tfplan` gerado e revisado no mesmo job.

**Separação de responsabilidades, não planejada mas registrada:** quem mesclou o código (Jonathas) e quem autorizou a alteração da infraestrutura (Ilan) são pessoas diferentes, em dois pontos de controle distintos. Não foi combinado — emergiu do desenho da esteira.

### O resultado

```
Apply complete! Resources: 0 added, 4 changed, 0 destroyed.
```

Idêntico ao plano lido localmente na véspera e ao plano publicado no PR. O protocolo de leitura do plano cumpriu sua função: o que foi aplicado é exatamente o que foi revisado — três vezes, por duas pessoas.

### Verificação no ambiente real

Job verde não é prova de que o ambiente está correto. A conferência foi feita direto no GCP:

| Verificação | Antes | Depois |
|---|---|---|
| `publicAccessPrevention` do bucket RAW | `inherited` | **`enforced`** |
| `versioning_enabled` do bucket RAW | desligado | **`True`** |
| Tabelas do `kenzie360_gold` | presentes | presentes |
| `kenzie360_silver.atendimentos` — partição e clustering | `DAY (data_ref)`, clusters intactos | inalterado |

**O ponto que fecha o argumento do card:** a esteira não apenas documentou a infraestrutura existente — ela **corrigiu uma lacuna de segurança real** (o bucket de dados crus não estava protegido contra exposição pública) e ligou o versionamento, tornando sobrescrita acidental recuperável. E fez isso sem nenhuma chave estática, com aprovação humana explícita e rastro completo de quem decidiu o quê.

### Manutenção futura registrada

O run emitiu um aviso: `actions/checkout@v4`, `hashicorp/setup-terraform@v3` e `terraform-linters/setup-tflint@v4` ainda declaram Node.js 20, em processo de aposentadoria pelo GitHub. É *warning*, não erro — o runner já executa em Node 24. Requer atualização de versão dessas actions em algum momento, sem impacto imediato.

---

## Fase D — travas de governança

| Configuração | Estado |
|---|---|
| Environment `gcp-dev` | Criado, com `idschapira` e `Jb0rges` como revisores obrigatórios |
| Environment `production` | **Já existia sem proteção nenhuma** — corrigido, agora com os mesmos revisores |
| Branch `main` | Exige Pull Request com 1 aprovação; force-push e exclusão bloqueados |

**O caso do `production` merece registro.** Ele não foi criado por nós: o GitHub cria automaticamente qualquer environment citado em um workflow — **sem nenhuma regra de proteção**. Ou seja, o job `apply-prod` referenciava um environment que aparentava ser um portão de aprovação e não era. A trava existia no papel e não no sistema.

É a diferença entre declarar um controle e verificar que ele existe. A verificação aqui foi consultar as `protection_rules` do environment via API — a interface mostra o environment existindo, o que basta para dar a impressão errada.

---

## Estado ao fim desta etapa

| Fase | Situação |
|---|---|
| A — proposta versionada (branch + PR) | ✅ Concluída — PR #1 |
| B — autenticação sem chave estática (WIF) | ✅ Concluída e validada pela esteira |
| C — adoção do ambiente (`import` + `plan`) | ✅ Concluída — `0 to destroy` |
| D — environments e proteção de branch | ✅ Concluída |
| Correção do WIF após transferência para organização | ✅ Concluída e validada |
| Merge e `apply` pela esteira | ✅ Concluído — `0 added, 4 changed, 0 destroyed` |

**Por que o merge não pode acontecer antes da Fase D:** se o environment `gcp-dev` não existir, o GitHub o cria implicitamente, sem nenhuma proteção — e o `terraform apply` executa sem aprovação humana. A trava de aprovação é justamente o controle que a arquitetura promete, e aplicá-lo sem ele descaracterizaria a entrega.

---

## Pendências

| # | Item | Responsável |
|---|---|---|
| 1 | Acrescentar `Validar Terraform` como status check obrigatório na `main` | Ilan |
| 2 | Atualizar as actions que ainda declaram Node.js 20 | Sprint 3 |
| 3 | Avaliar versionar o código da pipeline de dados (`3_pipeline/`), hoje fora de qualquer repositório | Equipe |

**Decisão D4:** fechada — o repositório passou para a organização `MACK-Hand-on`.
