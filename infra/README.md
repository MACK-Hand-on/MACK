# Guia passo a passo — Infraestrutura e CI/CD da Kenzie V2

Este guia foi escrito para quem **não é técnico**, mas precisa entregar/coordenar este projeto.
Cada seção explica o que foi feito, por quê, e o que você precisa clicar/rodar para colocar em funcionamento.

---

## O que foi construído (resumo em português simples)

| Arquivo/pasta | O que é, em termos simples |
|---|---|
| `infra/modules/data-lake/` | A "receita" que descreve como criar os 3 depósitos de dados da Kenzie (cru, limpo, pronto pra uso) |
| `infra/environments/dev/` | "Use essa receita, mas no ambiente de teste" |
| `infra/environments/prod/` | "Use essa receita, mas no ambiente real, com dados de clientes de verdade" |
| `.github/workflows/infra-cicd.yml` | O "robô" que aplica a receita sozinho, sempre que alguém aprova uma mudança |

**Por que dois ambientes (dev e prod)?** Para que qualquer erro de configuração apareça primeiro em um ambiente de teste (dev), sem nunca arriscar dados reais de correntistas.

---

## Passo 1 — Preparar a conta no GCP (uma vez só, feito por alguém com acesso administrativo)

1. Criar (ou obter acesso a) um projeto no Google Cloud Console — um para dev, outro para produção. Isso normalmente é feito pelo time de TI/infra do banco, não por você.
2. Anotar o **Project ID** de cada um (aparece no topo do Console GCP). Você vai substituir isso nos arquivos `terraform.tfvars`.
3. Habilitar as APIs necessárias no projeto: Cloud Storage, BigQuery. (Comando, para quem for técnico: `gcloud services enable storage.googleapis.com bigquery.googleapis.com`)
4. Criar **um bucket manualmente** (só esse recurso é manual) para guardar o "registro" do Terraform — o backend mencionado nos arquivos `backend.tf`:
   ```
   gsutil mb -l southamerica-east1 gs://SEU_PROJECT_ID-tfstate
   ```
   Isso precisa existir antes de qualquer `terraform init`, porque o Terraform precisa de um lugar para anotar o que ele já criou.

---

## Passo 2 — Preencher os "espaços em branco" nos arquivos

Abra estes dois arquivos e troque `SEU_PROJECT_ID_AQUI` pelo ID real do seu projeto:

- `infra/environments/dev/terraform.tfvars`
- `infra/environments/dev/backend.tf`

E o mesmo para produção:

- `infra/environments/prod/terraform.tfvars`
- `infra/environments/prod/backend.tf`

**Por que isso não vem pronto?** Porque o ID do projeto é único da sua empresa — ninguém mais no mundo pode usar o mesmo nome de bucket, então isso não dá pra deixar genérico.

---

## Passo 3 — Conectar o GitHub ao GCP (uma vez só)

O pipeline precisa de permissão para criar coisas no GCP em nome de vocês, mas **sem usar senha ou chave fixa** (isso é mais seguro — chaves fixas vazam e ficam ativas para sempre até alguém lembrar de revogar).

A técnica usada chama-se **Workload Identity Federation**. Na prática, alguém técnico do time roda uma configuração (documentada pela Google) que gera dois valores:

- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`

Esses dois valores são cadastrados em **GitHub → Settings → Secrets and variables → Actions**, como "Repository secrets". O pipeline (`infra-cicd.yml`) já está escrito esperando exatamente esses dois nomes.

---

## Passo 4 — Testar localmente antes de confiar no robô (recomendado, mas opcional)

Se alguém do time quiser testar na própria máquina antes de depender do CI/CD:

```bash
cd infra/environments/dev
terraform init
terraform plan
```

O comando `terraform plan` **não cria nada** — só mostra uma prévia do que seria criado. É a forma mais segura de conferir se está tudo certo.

---

## Passo 5 — Como o dia a dia vai funcionar depois de configurado

1. Alguém do time faz uma mudança nos arquivos `.tf` (ex.: adicionar uma nova tabela) e abre um **Pull Request** no GitHub.
2. O robô (`infra-cicd.yml`) roda sozinho: valida a sintaxe e mostra um "plano" — uma lista tipo "vou criar isso, vou mudar aquilo" — como comentário/log visível no PR.
3. Alguém revisa esse plano (você pode fazer isso, mesmo sem saber Terraform: se o plano diz "vai apagar o bucket de produção" e ninguém pediu isso, é sinal de alerta).
4. Ao aprovar e mesclar (merge) o PR na branch `main`, o robô aplica automaticamente em produção — mas só depois de uma aprovação manual configurada no GitHub Environment "production" (Settings → Environments → production → Required reviewers).

**Esse último ponto é o mais importante para você entender:** nada muda em produção sem alguém apertar "aprovar" — o robô nunca age sozinho de forma irreversível.

---

## O que ainda falta (próximos incrementos, fora do escopo deste pacote inicial)

Este primeiro pacote entrega a **fundação**: os depósitos de dados (raw/trusted/curated) e a esteira que os mantém. Ainda faltam, como próximos módulos a serem adicionados nesta mesma estrutura:

- **Composer** (orquestrador que move os dados entre as camadas) — entra quando o time começar a escrever os DAGs, no Sprint 3.
- **Vertex AI** (onde o modelo de NLP vai rodar) — entra quando o alvo do modelo for definido.
- **DLP / mascaramento de PII** — entra antes de qualquer dado real de cliente circular pela camada TRUSTED.
- **Looker Studio** — conexão do dashboard aos dados CURATED.

Cada um desses vira uma nova pasta dentro de `infra/modules/`, seguindo exatamente o mesmo padrão que `data-lake/` já estabeleceu.
