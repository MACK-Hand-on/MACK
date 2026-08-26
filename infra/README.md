# Guia passo a passo — Infraestrutura e CI/CD da Kenzie 360

Este guia foi escrito para quem **não é técnico**, mas precisa entregar/coordenar este projeto.
Cada seção explica o que foi feito, por quê, e o que você precisa clicar/rodar para colocar em funcionamento.

---

## O que foi construído (resumo em português simples)

| Arquivo/pasta | O que é, em termos simples |
|---|---|
| `infra/modules/data-lake/` | A "receita" que descreve como criar os depósitos de dados da Kenzie (cru, bronze, silver, gold) |
| `infra/environments/dev/` | "Use essa receita no ambiente que já existe hoje" |
| `infra/environments/prod/` | "Use essa receita no ambiente real" — estrutura pronta, ainda não provisionada |
| `.github/workflows/infra-cicd.yml` | O "robô" que valida e aplica a receita sozinho |
| `docs/proposta-cicd-aplicacao.yml` | Proposta de esteira para a **aplicação do chat** (não roda ainda — ver nota no fim) |

**As camadas de dados.** O projeto usa a nomenclatura "medalhão":

| Camada | Onde mora | O que é |
|---|---|---|
| RAW | Bucket no Cloud Storage | O CSV como chegou, sem tratamento |
| BRONZE | Dataset no BigQuery | O mesmo dado, já como tabela consultável, com rastreabilidade de ingestão |
| SILVER (trusted) | Dataset no BigQuery | Limpo, deduplicado, PII tratada |
| GOLD (curated) | Dataset no BigQuery | Pronto para o dashboard e para o modelo de NLP |

**Por que dois ambientes (dev e prod)?** Para que qualquer erro de configuração apareça primeiro em um ambiente de teste, sem nunca arriscar dados reais de correntistas.

---

## Passo 1 — Preparar a conta no GCP

**No projeto acadêmico este passo já está feito.** O ambiente foi provisionado manualmente na Trilha 0 da Sprint 2:

| Recurso | Nome real |
|---|---|
| Projeto GCP | `kenzie-360-mba` |
| Região | `us-central1` |
| Bucket RAW | `kenzie360-raw-ids26` |
| Bucket de estado do Terraform | `kenzie360-tfstate-ids26` |
| Datasets | `kenzie360_bronze`, `kenzie360_silver`, `kenzie360_gold` |

**Por que `us-central1`?** É a única região com Always Free no Cloud Storage (decisão D3 do projeto). E, mais importante: **o BigQuery não consegue cruzar dados entre regiões diferentes**. Um dataset em São Paulo não faz join com uma tabela em Iowa — a consulta simplesmente falha. Por isso todos os recursos precisam ficar na mesma região.

Se um dia for montar um ambiente do zero, os comandos são:

```bash
gcloud services enable storage.googleapis.com bigquery.googleapis.com
gcloud storage buckets create gs://SEU_PROJECT_ID-tfstate --location=us-central1
```

O bucket de estado precisa existir antes de qualquer `terraform init`, porque o Terraform precisa de um lugar para anotar o que ele já criou.

---

## Passo 2 — Os "espaços em branco"

**No ambiente `dev`, já estão preenchidos** com os nomes reais (`infra/environments/dev/terraform.tfvars` e `backend.tf`).

Em `prod` continuam como `SUBSTITUIR-PELO-...`, porque o projeto GCP de produção ainda não existe.

**Por que os nomes aparecem escritos no `terraform.tfvars`?** Porque estes recursos **já existem**. Os nomes precisam bater exatamente com os reais — senão o Terraform criaria um segundo data lake, vazio, ao lado do que tem os dados.

---

## Passo 3 — Fazer o Terraform "adotar" o que já existe (`terraform import`)

Este é o passo que conecta o código ao ambiente real. Sem ele, o Terraform acha que precisa criar tudo do zero.

`terraform import` significa: *"este recurso já existe lá no GCP, anota ele no seu registro sem recriar"*.

```bash
cd infra/environments/dev
terraform init

terraform import module.data_lake.google_storage_bucket.raw       kenzie360-raw-ids26
terraform import module.data_lake.google_bigquery_dataset.bronze  kenzie-360-mba/kenzie360_bronze
terraform import module.data_lake.google_bigquery_dataset.silver  kenzie-360-mba/kenzie360_silver
terraform import module.data_lake.google_bigquery_dataset.gold    kenzie-360-mba/kenzie360_gold
```

Depois de importar, rode:

```bash
terraform plan
```

> ### ⚠️ Leia o plano antes de aplicar
>
> É esperado ver linhas de **update in-place** (`~`) — o Terraform vai adicionar rótulos, descrições e o versionamento do bucket. Isso é seguro.
>
> **Se aparecer qualquer linha com `destroy` ou `must be replaced`, PARE e não aplique.** O caso mais comum é a região não bater: mudar `location` de um bucket ou dataset força a destruição e recriação — e os dados vão junto.

---

## Passo 4 — Conectar o GitHub ao GCP (uma vez só)

O pipeline precisa de permissão para criar coisas no GCP em nome de vocês, mas **sem usar senha ou chave fixa** (isso é mais seguro — chaves fixas vazam e ficam ativas para sempre até alguém lembrar de revogar).

A técnica usada chama-se **Workload Identity Federation**. Alguém técnico do time roda a configuração documentada pela Google, que gera dois valores:

- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`

Esses dois valores são cadastrados em **GitHub → Settings → Secrets and variables → Actions**, como "Repository secrets". O pipeline já está escrito esperando exatamente esses dois nomes.

Cadastre também os ambientes de aprovação em **Settings → Environments**:

| Environment | Para que serve | Required reviewers |
|---|---|---|
| `gcp-dev` | Aprovar aplicação no ambiente atual | Recomendado |
| `production` | Aprovar aplicação em produção | Obrigatório |

---

## Passo 5 — Testar localmente antes de confiar no robô

```bash
cd infra/environments/dev
terraform init
terraform plan
```

O comando `terraform plan` **não cria nada** — só mostra uma prévia. É a forma mais segura de conferir se está tudo certo.

---

## Passo 6 — Como o dia a dia vai funcionar

1. Alguém do time muda um arquivo `.tf` e abre um **Pull Request**.
2. O robô valida: formatação, sintaxe, **tflint** (boas práticas de GCP) e **checkov** (segurança — detecta bucket público, IAM permissivo demais).
3. O robô publica o plano **como comentário no próprio PR**. Você não precisa saber Terraform para revisar: se o plano diz "vai apagar o bucket" e ninguém pediu isso, é sinal de alerta.
4. Ao mesclar na `main`, o robô aplica no ambiente `dev` — **depois de uma aprovação manual** no GitHub Environment `gcp-dev`.
5. Produção só é aplicada **manualmente**, pelo botão "Run workflow" na aba Actions, e ainda exige aprovação no Environment `production`.

**O ponto mais importante:** nada é aplicado sem alguém apertar "aprovar". O robô nunca age sozinho de forma irreversível. E o `apply` usa exatamente o mesmo arquivo de plano que foi gerado e revisado — não um plano novo, que poderia ter mudado.

---

## Nota sobre `docs/proposta-cicd-aplicacao.yml`

Esse arquivo descreve a esteira da **aplicação do chat** — build de imagem Docker, deploy, smoke test, rollback. É um bom desenho, mas depende de arquivos que ainda não existem (`app/`, `Dockerfile`, `requirements.txt`, `tests/`).

Por isso ele foi movido para fora de `.github/workflows/`: ali dentro, ele dispararia a cada push e falharia em todos os jobs, e um repositório com CI permanentemente vermelho ensina o time a ignorar o alerta. Ele volta para `.github/workflows/` quando o código da aplicação entrar no repositório.

---

## O que ainda falta (próximos incrementos)

Este pacote entrega a **fundação**: os depósitos de dados e a esteira que os mantém. Próximos módulos, na mesma estrutura:

- **Módulo de IAM** — quem pode ler/escrever em cada camada, versionado como código.
- **Orquestração** (mover dados entre as camadas) — quando o time escrever os DAGs. Atenção: o Cloud Composer **não tem free tier** (~US$ 525/mês); a alternativa avaliada é Cloud Scheduler + Cloud Run Jobs.
- **Vertex AI** — quando o alvo do modelo de NLP for definido.
- **DLP / mascaramento de PII** — antes de qualquer dado real de cliente circular pela camada SILVER.

Cada um vira uma nova pasta dentro de `infra/modules/`, seguindo o mesmo padrão que `data-lake/` já estabeleceu.
