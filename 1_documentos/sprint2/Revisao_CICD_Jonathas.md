# Revisão técnica — repositório de CI/CD e IaC

**Projeto Kenzie 360 · Sprint 2 · Card 2**
Repositório: https://github.com/Jb0rges/MACK
Autor: Jonathas Borges · Revisado em 24/08/2026
14 arquivos · 10 commits

---

## Veredito

**A estrutura está correta e as decisões de segurança estão bem tomadas.** O que impede rodar hoje não é qualidade do código — são **divergências de configuração** entre o que o Terraform descreve e o ambiente que já existe no GCP.

São três correções bloqueantes, todas de baixa complexidade, e duas melhorias que o próprio autor já havia previsto no documento conceitual.

---

## 1. O que está bem feito

Vale registrar antes de listar ajustes, porque é a maior parte do trabalho.

**Organização em módulos e ambientes.** A separação `modules/` + `environments/dev` + `environments/prod` é o padrão correto de Terraform. O módulo é reutilizável e os ambientes só passam parâmetros — exatamente como deve ser.

**Segurança do bucket, bem acima do básico:**

| Configuração | Efeito |
|---|---|
| `public_access_prevention = "enforced"` | Impede exposição pública mesmo por engano |
| `uniform_bucket_level_access = true` | Acesso controlado num ponto só, sem ACL por objeto |
| `versioning { enabled = true }` | Sobrescrita acidental é recuperável |
| `force_destroy = false` | Exclusão exige passo deliberado |
| `lifecycle_rule` com retenção | Dado cru não acumula custo nem risco indefinidamente |

Em ambiente bancário, `public_access_prevention` é o tipo de configuração cuja ausência vira incidente. Está certo.

**Workload Identity Federation em vez de chave estática.** O workflow autentica sem `credentials_json`, usando `id-token: write` e federação. Elimina o risco de chave de service account vazada — e a preocupação é concreta: nesta mesma sprint encontramos uma chave de API exposta em texto puro num arquivo de configuração local.

**Aprovação manual em produção.** O job `apply-prod` usa `environment: production`, que no GitHub permite exigir revisores. É o freio que impede o robô de agir sozinho em produção.

**Comentários didáticos e README para não-técnico.** Raro e valioso. O README explica o problema de ovo e galinha do bucket de estado, o que é `terraform plan`, e por que existem dois ambientes. Isso é entregável de documentação por si só.

---

## 2. Correções bloqueantes

### 2.1 A região não bate com o ambiente existente — e isso quebra o BigQuery

**Situação:** o Terraform usa `southamerica-east1` como padrão. O ambiente provisionado na Trilha 0 está em **`us-central1`**.

**Por que é bloqueante, e não cosmético:** o BigQuery **não permite consulta entre datasets de regiões diferentes**. Um dataset criado em São Paulo não consegue fazer join com uma tabela em Iowa — a consulta falha, não fica lenta. Aplicar o Terraform como está criaria um ambiente paralelo incapaz de conversar com o que já existe.

**Correção:** alterar o `default` de `region` para `us-central1` em `modules/data-lake/variables.tf` e nos dois `environments/*/variables.tf` e `terraform.tfvars`.

*Nota de contexto:* `southamerica-east1` foi uma escolha razoável — menor latência e argumento de soberania de dados, relevante num banco. O grupo optou por `us-central1` porque é a única região com Always Free no Cloud Storage (decisão D3, registrada). A soberania de dados permanece documentada como decisão de produção.

### 2.2 Os nomes dos recursos divergem dos que já existem

**Situação:**

| Recurso | Terraform criaria | Já existe no GCP |
|---|---|---|
| Bucket RAW | `kenzie-360-mba-kenzie-raw-dev` | `kenzie360-raw-ids26` |
| Dataset TRUSTED | `kenzie_trusted_dev` | `kenzie360_silver` |
| Dataset CURATED | `kenzie_curated_dev` | `kenzie360_gold` |
| Dataset BRONZE | *(não existe no módulo)* | `kenzie360_bronze` |
| Bucket de estado | `<project>-tfstate` | `kenzie360-tfstate-ids26` |

**Consequência:** `terraform apply` não assumiria o controle do ambiente atual — criaria um segundo conjunto de recursos vazios, ao lado. Ficaríamos com dois data lakes, um deles sem dados.

**Duas saídas possíveis:**

| Opção | Como | Quando faz sentido |
|---|---|---|
| **A — Alinhar os nomes** *(recomendada)* | Ajustar o módulo para os nomes reais e usar `terraform import` para o Terraform adotar os recursos existentes | O ambiente já tem dados e a pipeline inteira aponta para esses nomes |
| B — Recriar com os nomes novos | Aplicar como está e migrar dados e scripts | Só se houvesse motivo forte para renomear, e não há |

A opção A preserva o trabalho das duas frentes. O comando de adoção é `terraform import`, que registra um recurso já existente no estado sem recriá-lo.

### 2.3 Falta a camada bronze

O módulo cria `trusted` e `curated`, mas o RAW aparece apenas como bucket. Nossa arquitetura tem **três camadas no BigQuery** — a bronze é onde o CSV é materializado como tabela consultável, com as colunas de rastreabilidade `_ingestion_ts` e `_source_file`.

**Correção:** acrescentar um `google_bigquery_dataset` para a camada bronze no módulo.

---

## 3. O workflow `ci-cd.yml` não pertence a este repositório

O arquivo descreve o pipeline da **aplicação do chat** — build de imagem Docker, deploy on-premises via SSH, smoke test em `chat-investimentos.suaempresa.com.br`, rollback automático. É um bom desenho, mas referencia arquivos que não existem aqui:

`app/` · `requirements.txt` · `requirements-dev.txt` · `tests/quality/casos_clientes.yaml` · `Dockerfile`

**Consequência prática:** o workflow dispara a cada push e **falha em todos os jobs**, porque `ruff check .` não encontra código Python, `pip install -r requirements.txt` não encontra o arquivo, e assim por diante. Um repositório com CI permanentemente vermelho é pior do que um sem CI — a equipe aprende a ignorar o alerta.

**Três saídas, em ordem de preferência:**

1. **Mover para `docs/proposta-cicd-aplicacao.yml`** e citar no README como proposta de arquitetura para a aplicação. Preserva o conteúdo, que é bom, sem quebrar o repositório.
2. Trocar o gatilho para apenas `workflow_dispatch`, deixando claro no nome que é modelo de referência.
3. Criar os arquivos mínimos para o pipeline rodar — mais trabalho, e fora do escopo do card.

A primeira mantém o mérito do trabalho e resolve o problema em um `git mv`.

---

## 4. Melhorias que o próprio autor havia previsto

O documento conceitual escrito por ele propunha itens que ainda não foram para o código:

| Proposto no documento | No repositório | Ajuste |
|---|---|---|
| `tflint` — boas práticas de GCP | Ausente | Acrescentar step no job `validate` |
| `checkov` ou `tfsec` — segurança | Ausente | Acrescentar step no job `validate` |
| Plano publicado **como comentário no PR** | Roda, mas fica só no log | Usar action que publica o plano no PR |
| Módulo de IAM | Ausente | Pode ficar para um incremento |

Os dois primeiros são especialmente relevantes: `checkov` é o que detectaria automaticamente um bucket público ou IAM excessivamente permissivo — exatamente o risco que o documento cita como crítico por lidarmos com dados de correntistas. São dois steps de cinco linhas cada.

Sobre o plano no PR: o README promete que "o plano aparece como comentário/log visível no PR", mas hoje ele só vai para o log da execução. Quem revisa precisa abrir a aba Actions e procurar. Publicar como comentário é o que torna a revisão viável para quem não é técnico — que é justamente o público que o README mira.

---

## 5. Observações menores

**Não há `apply` para o ambiente dev.** O fluxo atual é: PR → `plan-dev`; merge em main → `apply-prod`. Ou seja, dev nunca é efetivamente aplicado — o plano é validado contra um ambiente que não existe. Faz sentido acrescentar um `apply-dev` no push para main, antes do apply de produção.

**`apply-prod` não depende de `plan`.** Ele depende só de `validate`. Um `plan` prévio como gate daria mais segurança.

**Provider fixado em `~> 5.0`.** A linha 6.x já está disponível. Não é erro — fixar versão é boa prática — mas vale saber que está uma major atrás.

**O `backend.tf` não aceita variáveis.** O Terraform exige valor literal no bloco `backend`. O README documenta a substituição manual, o que está correto. Uma alternativa mais limpa é `terraform init -backend-config="bucket=..."`, que evita editar arquivo versionado.

---

## 6. Resumo priorizado

| # | Item | Gravidade | Esforço |
|---|---|---|---|
| 1 | Região `southamerica-east1` → `us-central1` | **Bloqueante** | 5 min |
| 2 | Alinhar nomes de recursos aos existentes + `terraform import` | **Bloqueante** | 1 h |
| 3 | Acrescentar dataset da camada bronze | **Bloqueante** | 10 min |
| 4 | Mover `ci-cd.yml` para `docs/` | Alta | 5 min |
| 5 | Acrescentar `tflint` e `checkov` ao `validate` | Média | 20 min |
| 6 | Publicar o plano como comentário no PR | Média | 20 min |
| 7 | Acrescentar job `apply-dev` | Baixa | 15 min |

Os três bloqueantes somam pouco mais de uma hora. Nada aqui exige reescrever o que foi feito — são ajustes de configuração sobre uma base que está bem construída.
