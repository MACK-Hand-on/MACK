# Runbook — assumir o CI/CD

**Projeto Kenzie 360 · Sprint 2 · Card 2**
**Decisão:** a execução do CI/CD passa a ser nossa. O repositório continua sendo o do Jonathas (`Jb0rges/MACK`), e a autoria dele fica preservada — trabalhamos por **branch + Pull Request**, nunca direto na `main`.

Tudo aqui roda no **seu Ubuntu** (o mesmo terminal onde você roda o `kenzie` e o `gcloud`). Não dá para rodar do meu lado: o meu ambiente não tem sua credencial do GitHub, e o terminal que eu acesso na sua máquina não tem saída para a internet (testei — o proxy bloqueia).

**Tempo total:** cerca de 2 horas, em quatro fases. Dá para parar entre uma e outra.

---

## Antes de começar — um combinado de processo

Ter acesso de colaborador não é o mesmo que ter carta branca. Três regras:

1. **Nada vai direto na `main`.** Sempre branch + PR.
2. **O Jonathas revisa o PR.** É o repositório dele e o card era dele; a mudança de execução não muda isso.
3. **Nenhum `terraform apply` antes de o `plan` ser lido.** Se o plano mostrar `destroy`, para tudo — detalhe na Fase C.

---

# FASE A — Abrir o Pull Request

**Onde:** terminal do Ubuntu. **Tempo:** ~20 min.

## A1. Instalar o GitHub CLI

O `gh` resolve o login pelo navegador — assim você não precisa criar nem colar token nenhum.

```bash
sudo apt update
sudo apt install -y gh git
gh --version
```

## A2. Fazer login no GitHub

```bash
gh auth login
```

Responda:

| Pergunta | Resposta |
|---|---|
| What account do you want to log into? | **GitHub.com** |
| What is your preferred protocol...? | **HTTPS** |
| Authenticate Git with your GitHub credentials? | **Yes** |
| How would you like to authenticate? | **Login with a web browser** |

Ele mostra um código de 8 caracteres (tipo `A1B2-C3D4`) e abre o navegador. Cole o código lá e autorize.

> Se o navegador não abrir sozinho, ele imprime a URL — abra na mão.

Confirme:

```bash
gh auth status
```

Tem que aparecer `Logged in to github.com as idschapira`.

## A3. Clonar o repositório

```bash
cd ~
gh repo clone Jb0rges/MACK
cd MACK
git log --oneline -3
```

O último commit tem que ser `a0c4e1d Update infra-cicd.yml`.

## A4. Aplicar o patch

O patch está dentro do ZIP que já está na pasta do projeto. Descompacte e aplique:

```bash
cd ~/MACK
unzip -o "/mnt/c/Users/<seu-usuario>/Claude/Projects/Projeto Kenzie 360/1_documentos/sprint2/Correcoes_CICD_Kenzie360.zip" -d /tmp/correcoes

git checkout -b correcoes/alinhamento-ambiente
git am /tmp/correcoes/correcoes-cicd-kenzie360.patch
```

Se der certo, aparece `Applying: Alinhar IaC ao ambiente real e endurecer a esteira`.

Confira o que mudou:

```bash
git show --stat
```

Devem aparecer 15 arquivos.

> **Se o `git am` falhar** (só acontece se o Jonathas tiver commitado algo novo): rode `git am --abort` e me avisa. Eu regero o patch em cima do commit novo.

## A5. Subir e abrir o PR

```bash
git push -u origin correcoes/alinhamento-ambiente

gh pr create \
  --title "Alinhar IaC ao ambiente real e endurecer a esteira" \
  --body-file /tmp/correcoes/GUIA_Aplicar_Correcoes.md \
  --base main
```

O `gh` devolve a URL do PR. **Manda essa URL para o Jonathas** — o corpo do PR já é o guia inteiro explicando cada mudança, então ele consegue revisar sem precisar de contexto extra.

**Não faça merge ainda.** O merge só depois da Fase B, senão a esteira roda sem as credenciais e falha.

---

# FASE B — Conectar o GitHub ao GCP (Workload Identity Federation)

**Onde:** terminal do Ubuntu, logado no `gcloud`. **Tempo:** ~40 min.
**Esta é a parte mais chata.** É o que permite o GitHub criar recursos no GCP sem chave fixa.

## O que é, em uma frase

Em vez de guardar uma senha do GCP dentro do GitHub, o GCP passa a **confiar** que o GitHub é quem diz ser, para um repositório específico. Não existe segredo para vazar.

## B1. Ligar as APIs necessárias

```bash
gcloud config set project kenzie-360-mba

gcloud services enable \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com
```

## B2. Criar a conta de serviço que o GitHub vai usar

```bash
gcloud iam service-accounts create github-actions-terraform \
  --project=kenzie-360-mba \
  --display-name="GitHub Actions - Terraform"
```

Dar a ela permissão para criar buckets e datasets:

```bash
gcloud projects add-iam-policy-binding kenzie-360-mba \
  --member="serviceAccount:github-actions-terraform@kenzie-360-mba.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding kenzie-360-mba \
  --member="serviceAccount:github-actions-terraform@kenzie-360-mba.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"
```

> **Nota de honestidade técnica:** `storage.admin` e `bigquery.admin` no projeto inteiro é mais permissão do que o ideal. O correto em produção seria restringir aos recursos específicos. Para o escopo acadêmico está adequado — e o `checkov` que acrescentamos na esteira vai apontar isso, o que é bom: mostra que a ferramenta funciona.

## B3. Criar o pool e o provider de identidade

```bash
gcloud iam workload-identity-pools create "github" \
  --project="kenzie-360-mba" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

```bash
gcloud iam workload-identity-pools providers create-oidc "kenzie-mack" \
  --project="kenzie-360-mba" \
  --location="global" \
  --workload-identity-pool="github" \
  --display-name="Repo Jb0rges/MACK" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == 'Jb0rges'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

> A linha `attribute-condition` é a trava de segurança: só repositórios do dono `Jb0rges` conseguem usar essa federação. Sem ela, qualquer repositório do GitHub no mundo poderia pedir acesso ao nosso projeto.

## B4. Autorizar o repositório a usar a conta de serviço

```bash
export POOL_ID=$(gcloud iam workload-identity-pools describe "github" \
  --project="kenzie-360-mba" --location="global" --format="value(name)")

echo "POOL_ID = $POOL_ID"

gcloud iam service-accounts add-iam-policy-binding \
  "github-actions-terraform@kenzie-360-mba.iam.gserviceaccount.com" \
  --project="kenzie-360-mba" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/Jb0rges/MACK"
```

## B5. Pegar os dois valores que vão para o GitHub

```bash
echo "WIF_PROVIDER:"
gcloud iam workload-identity-pools providers describe "kenzie-mack" \
  --project="kenzie-360-mba" --location="global" \
  --workload-identity-pool="github" --format="value(name)"

echo "WIF_SERVICE_ACCOUNT:"
echo "github-actions-terraform@kenzie-360-mba.iam.gserviceaccount.com"
```

O primeiro sai no formato `projects/123456789/locations/global/workloadIdentityPools/github/providers/kenzie-mack`.

## B6. Cadastrar os dois no GitHub

Do próprio terminal:

```bash
cd ~/MACK

gh secret set WIF_PROVIDER
# cole o valor do provider quando ele pedir e aperte Enter

gh secret set WIF_SERVICE_ACCOUNT
# cole github-actions-terraform@kenzie-360-mba.iam.gserviceaccount.com

gh secret list
```

> Nenhum desses dois valores é senha — são identificadores. Mesmo assim, ficam como secret porque expõem a estrutura interna do projeto.

---

# FASE C — Terraform adotar o ambiente que já existe

**Onde:** terminal do Ubuntu. **Tempo:** ~30 min.
**Esta é a fase com risco real.** Leia o aviso antes de rodar o `apply`.

## C1. Instalar o Terraform

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update && sudo apt install -y terraform
terraform version
```

## C2. Inicializar

```bash
cd ~/MACK/infra/environments/dev
terraform init
```

Ele vai conectar no bucket `kenzie360-tfstate-ids26`, que já existe desde a Trilha 0.

## C3. Adotar os recursos existentes

```bash
terraform import module.data_lake.google_storage_bucket.raw       kenzie360-raw-ids26
terraform import module.data_lake.google_bigquery_dataset.bronze  kenzie-360-mba/kenzie360_bronze
terraform import module.data_lake.google_bigquery_dataset.silver  kenzie-360-mba/kenzie360_silver
terraform import module.data_lake.google_bigquery_dataset.gold    kenzie-360-mba/kenzie360_gold
```

Cada um deve terminar com `Import successful!`.

## C4. Ler o plano — o passo que não pode ser pulado

```bash
terraform plan -no-color | tee /tmp/plano.txt
```

Procure a última linha, no formato `Plan: X to add, Y to change, Z to destroy.`

| O que aparece | Significa | O que fazer |
|---|---|---|
| `0 to add, 4 to change, 0 to destroy` | Só ajustes de label/descrição/versionamento | **Seguro.** Pode aplicar |
| Qualquer número em `to destroy` | Terraform quer apagar e recriar algo | **PARE.** Não aplique |
| Qualquer `must be replaced` no meio do plano | Idem | **PARE.** Não aplique |

Se aparecer `destroy`, me manda o `/tmp/plano.txt` que eu identifico a causa. A mais provável é `location` divergente — e trocar a região de um dataset destrói os dados dentro dele. São 405 mil mensagens e três semanas de trabalho; não vale o risco de aplicar "para ver no que dá".

## C5. Aplicar

Só depois de C4 dar limpo:

```bash
terraform apply
```

Ele mostra o plano de novo e pede confirmação. Digite `yes`.

## C6. Conferir que nada quebrou

```bash
bq ls kenzie-360-mba:kenzie360_gold
gcloud storage ls gs://kenzie360-raw-ids26 | head
```

Os datasets e o conteúdo do bucket têm que continuar lá.

---

# FASE D — Ligar as travas no GitHub

**Onde:** navegador. **Tempo:** ~10 min.

## D1. Criar os dois ambientes de aprovação

Em **Settings → Environments → New environment**:

| Nome | Required reviewers |
|---|---|
| `gcp-dev` | você e o Jonathas |
| `production` | você e o Jonathas |

Sem isso a esteira aplica sozinha ao dar merge — que é exatamente o que a gente não quer.

## D2. Proteger a branch main

Em **Settings → Branches → Add branch protection rule**, para `main`:

- ✅ Require a pull request before merging
- ✅ Require approvals: **1**
- ✅ Require status checks to pass → selecionar **Validar Terraform**

Isso garante que nenhum de nós — nem o Jonathas — empurre nada direto na `main`, e que o `tflint` e o `checkov` rodem antes de qualquer merge.

## D3. Fechar o ciclo

Com Fase B e C prontas, volte no PR da Fase A:

1. Peça a revisão do Jonathas.
2. Faça o merge.
3. Acompanhe em **Actions**: o job `Aplicar - Ambiente Dev` vai pedir aprovação no environment `gcp-dev`.
4. Aprove e veja rodar.

**Esse é o print que vale para a entrega:** a esteira completa, verde, com aprovação manual registrada.

---

## Checklist de encerramento do card

| | Item |
|---|---|
| ☐ | PR aberto e revisado pelo Jonathas |
| ☐ | `WIF_PROVIDER` e `WIF_SERVICE_ACCOUNT` cadastrados |
| ☐ | `terraform import` dos 4 recursos concluído |
| ☐ | `terraform plan` sem `destroy` |
| ☐ | `terraform apply` aplicado |
| ☐ | Environments `gcp-dev` e `production` com revisores |
| ☐ | Branch `main` protegida |
| ☐ | Print da execução verde salvo em `1_documentos/sprint2/` |
| ☐ | Decisão D4 fechada (repo fica na conta do Jonathas ou vai para organização) |

---

## Onde cada coisa pode dar errado

| Sintoma | Causa provável | Saída |
|---|---|---|
| `gh auth login` não abre navegador | WSL sem integração com o Windows | Copie a URL impressa e abra na mão |
| `git am` falha | Jonathas commitou algo novo | `git am --abort` e me chamar para regerar o patch |
| `Error 403` no `terraform init` | Sua conta sem acesso ao bucket de estado | `gcloud auth application-default login` |
| Job do GitHub falha em "Autenticar no GCP" | Fase B incompleta ou `attribute-condition` errada | Conferir B3 e B4 |
| `terraform plan` quer destruir dataset | Região divergente | **Não aplicar.** Me mandar o plano |
| `checkov` reclamando muito | Esperado — está em `--soft-fail` | Só avisa, não quebra o build |
