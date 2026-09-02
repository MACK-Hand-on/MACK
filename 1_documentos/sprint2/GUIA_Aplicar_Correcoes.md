# Como aplicar as correções — repositório MACK

**Para:** Jonathas Borges
**De:** frente de dados (Ilan / Giovanna)
**Repositório:** https://github.com/Jb0rges/MACK
**Base:** commit `a0c4e1d` ("Update infra-cicd.yml")

---

## Antes de tudo

O que está aqui **não é reescrita**. A estrutura de módulos, a segurança do bucket, o Workload Identity Federation e o README para não-técnico ficaram como estavam — são a parte boa e ela foi preservada.

O que mudou foi o **alinhamento com o ambiente que já subimos no GCP na Trilha 0**. Sem isso, `terraform apply` criaria um segundo data lake, vazio, ao lado do que já tem 405 mil mensagens carregadas.

Tudo foi validado antes de mandar: `terraform fmt -check`, `terraform validate` nos dois ambientes e o YAML do workflow.

---

## O que mudou, em uma tabela

| # | Mudança | Por quê |
|---|---|---|
| 1 | Região `southamerica-east1` → `us-central1` | **O BigQuery não faz join entre regiões.** Dataset em São Paulo não cruza com tabela em Iowa — a consulta falha, não fica lenta |
| 2 | Nomes dos recursos viraram variáveis, com os valores reais no `terraform.tfvars` de dev | Para o Terraform **adotar** o que existe (`terraform import`), não criar duplicata |
| 3 | Camada `bronze` acrescentada ao módulo | Nossa arquitetura tem 3 datasets no BigQuery, não 2 |
| 4 | `ci-cd.yml` → `docs/proposta-cicd-aplicacao.yml` | Ele referencia `app/`, `Dockerfile`, `requirements.txt` — nada disso existe no repo, então falhava em **todo push** |
| 5 | `tflint` + `checkov` no job `validate` | Você mesmo propôs no documento conceitual. `checkov` é o que pegaria um bucket público automaticamente |
| 6 | Plano publicado como comentário no PR | O README promete isso; hoje o plano só ia para o log da aba Actions |
| 7 | Novo job `apply-dev`; `apply-prod` virou manual | Antes dev nunca era aplicado, e prod era aplicado a cada merge — num projeto GCP que ainda não existe |
| 8 | `apply` usa o arquivo `tfplan` gerado no mesmo job | Garante que o que é aplicado é exatamente o que foi revisado |
| 9 | `.gitignore` | `.terraform/`, `tfstate` e chaves `.json` de service account não podem ir para o repositório |

**Sobre o item 2 — a parte que mais importa.** O módulo continua gerando os nomes no seu padrão original (`${project_id}-kenzie-raw-${environment}`) quando nenhum nome é informado. Só que agora dá pra informar o nome real. Ambiente `prod` continua usando o padrão gerado; `dev` usa os nomes que existem:

| Recurso | Nome real no GCP |
|---|---|
| Bucket RAW | `kenzie360-raw-ids26` |
| Bucket de estado | `kenzie360-tfstate-ids26` |
| Datasets | `kenzie360_bronze`, `kenzie360_silver`, `kenzie360_gold` |
| Projeto / Região | `kenzie-360-mba` / `us-central1` |

---

## Como aplicar

Você escolhe. As três dão no mesmo resultado.

### Opção A — patch por linha de comando (mais rápida)

```bash
cd MACK
git checkout main && git pull
git checkout -b correcoes/alinhamento-ambiente
git am /caminho/para/correcoes-cicd-kenzie360.patch
```

Isso cria um commit com a mensagem já escrita. Confira e suba:

```bash
git push -u origin correcoes/alinhamento-ambiente
```

Depois abra o Pull Request no GitHub. **Não faça merge direto na main** — o objetivo é justamente ver a esteira nova rodando no PR.

### Opção B — trocar os arquivos na mão

Na pasta `arquivos_corrigidos/` deste pacote está a árvore completa já corrigida. Copie por cima do seu clone, confira o `git diff` e commite. É a opção mais transparente se você quiser ler mudança por mudança.

### Opção C — a gente abre o PR

Se preferir, é só nos dar acesso ao repositório (veja a última seção) que abrimos o PR e você revisa e aprova pelo GitHub. Nada entra na `main` sem seu aval.

---

## Depois de aplicar: o `terraform import`

Este é o passo que conecta o código ao ambiente real. Sem ele o Terraform ainda acha que precisa criar tudo do zero.

```bash
cd infra/environments/dev
terraform init

terraform import module.data_lake.google_storage_bucket.raw       kenzie360-raw-ids26
terraform import module.data_lake.google_bigquery_dataset.bronze  kenzie-360-mba/kenzie360_bronze
terraform import module.data_lake.google_bigquery_dataset.silver  kenzie-360-mba/kenzie360_silver
terraform import module.data_lake.google_bigquery_dataset.gold    kenzie-360-mba/kenzie360_gold

terraform plan
```

> ### ⚠️ Leia o plano antes de aplicar
>
> **Esperado e seguro:** linhas de `~ update in-place` — o Terraform vai adicionar labels, descrições e ligar o versionamento do bucket.
>
> **PARE se aparecer `destroy` ou `must be replaced`.** A causa quase sempre é `location` divergente, e trocar a região de um dataset significa destruir e recriar — com os dados dentro.
>
> Se isso acontecer, não aplique e nos chama. Preferimos um plano vermelho a um dataset perdido a três semanas da entrega.

---

## O que você precisa configurar no GitHub

Sem isso os jobs que tocam o GCP não rodam.

**Settings → Secrets and variables → Actions:**

| Secret | O que é |
|---|---|
| `WIF_PROVIDER` | Provider do Workload Identity Federation |
| `WIF_SERVICE_ACCOUNT` | Service account que o GitHub assume |

**Settings → Environments** — criar dois:

| Environment | Required reviewers |
|---|---|
| `gcp-dev` | Recomendado |
| `production` | Obrigatório |

Se o WIF ainda não estiver configurado no GCP, avisa — a gente ajuda a montar, é a única parte que exige mexer no IAM do projeto.

---

## O que ficou de fora de propósito

Não mexemos nestes, para não decidir por você:

- **Provider `~> 5.0`.** A linha 6.x já saiu. Fixar versão é boa prática, então não subimos por conta própria — mas vale saber que está uma major atrás.
- **Módulo de IAM.** Seu documento conceitual previa. É um bom próximo incremento, mas não é bloqueante para a Sprint 2.
- **`checkov` está em `--soft-fail`.** Ele avisa mas não quebra o build. Ele vai reclamar de CMEK e logging de bucket, que são exageros para um projeto acadêmico. Quando o time zerar o que faz sentido, é só tirar a flag.

---

## Sobre colaborar no repositório

Hoje só você consegue subir código. Duas formas de abrir isso, ambas de dois minutos:

| Como | Onde | Efeito |
|---|---|---|
| **Adicionar colaboradores** | Settings → Collaborators → Add people | A gente cria branch e abre PR direto. Você continua sendo quem aprova |
| **Fork + PR** | Não depende de você | A gente trabalha num fork e manda PR. Funciona sem nenhuma permissão |

A primeira é melhor para o ritmo da sprint. E vale ligar a proteção da branch em **Settings → Branches → Add rule** para `main`, exigindo PR e aprovação — assim ninguém (nem a gente) empurra nada direto na main por engano.

**Decisão que ainda está em aberto (D4):** se o repositório final da entrega fica na sua conta ou numa organização do grupo. Se for pra organização, o GitHub transfere o repo inteiro com histórico e commits preservados — sua autoria não se perde. Vale decidir antes da entrega, dia 11–17/09.
