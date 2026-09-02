# Comandos prontos — Trilha 0 · Kenzie 360

**Project ID confirmado:** `kenzie-360-mba`
**Número do projeto:** 82113574624
**Sufixo dos buckets:** `ids26`
**Região:** `us-central1`
**Ambiente:** Ubuntu no WSL

> Passos 1, 2 e 3 já concluídos pelo Ilan em 21/08/2026.
> Copie e cole um bloco de cada vez. Aguarde cada um terminar antes do próximo.

---

## Passo 4 — Instalar o gcloud CLI

**4.1** Dependências:

```bash
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
```

**4.2** Chave pública do Google:

```bash
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
```

**4.3** Repositório:

```bash
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
```

**4.4** Instalar:

```bash
sudo apt-get update && sudo apt-get install -y google-cloud-cli
```

**4.5** Conferir:

```bash
gcloud --version
```

---

## Passo 5 — Autenticar

**5.1** Login da sua conta:

```bash
gcloud auth login --no-launch-browser
```

Ele imprime uma URL longa. Copie, cole no Chrome do Windows, autorize, e cole o código de volta no terminal.

**5.2** Fixar o projeto:

```bash
gcloud config set project kenzie-360-mba
```

**5.3** Autenticar as bibliotecas Python (é diferente do 5.1, não pule):

```bash
gcloud auth application-default login --no-launch-browser
```

**5.4** Conferir:

```bash
gcloud config list
```

Deve mostrar `project = kenzie-360-mba`.

---

## Passo 6 — Habilitar as APIs

```bash
gcloud services enable bigquery.googleapis.com storage.googleapis.com iam.googleapis.com cloudresourcemanager.googleapis.com run.googleapis.com cloudscheduler.googleapis.com bigquerydatatransfer.googleapis.com
```

Demora 1 a 2 minutos sem mostrar progresso. Depois:

```bash
gcloud services list --enabled
```

---

## Passo 7 — Criar os buckets

**7.1** Bucket do RAW:

```bash
gcloud storage buckets create gs://kenzie360-raw-ids26 --location=us-central1 --uniform-bucket-level-access
```

**7.2** Bucket do estado do Terraform:

```bash
gcloud storage buckets create gs://kenzie360-tfstate-ids26 --location=us-central1 --uniform-bucket-level-access
```

**7.3** Versionamento no bucket de estado:

```bash
gcloud storage buckets update gs://kenzie360-tfstate-ids26 --versioning
```

**7.4** Conferir:

```bash
gcloud storage ls
```

Deve listar os dois. Se der erro de nome já em uso, troque `ids26` por outro sufixo nos três comandos e me avise qual usou.

---

## Passo 8 — Orçamento *(navegador, 5 min)*

1. https://console.cloud.google.com/billing → **Orçamentos e alertas**
2. **Criar orçamento**
3. **Escopo → Projetos:** selecione **apenas** `Kenzie 360 MBA`
4. **Valor:** `20` dólares (Valor especificado)
5. **Ações:** alertas em **10%, 50%, 90%**
6. Marque "Enviar alertas por e-mail aos administradores de faturamento"
7. Salvar

---

## Passo 9 — Ambiente Python

**9.1** Instalar o Python e o venv:

```bash
sudo apt-get install -y python3 python3-pip python3-venv
```

**9.2** Criar o ambiente virtual **no disco do Linux** (não em /mnt/c):

```bash
mkdir -p ~/.venvs && python3 -m venv ~/.venvs/kenzie360
```

**9.3** Criar o atalho permanente:

```bash
echo "alias kenzie='source ~/.venvs/kenzie360/bin/activate && cd \"/mnt/c/Users/<seu-usuario>/Claude/Projects/Projeto Kenzie 360\"'" >> ~/.bashrc && source ~/.bashrc
```

**9.4** Ativar (a partir de agora, é só digitar `kenzie`):

```bash
kenzie
```

O prompt deve mostrar `(kenzie360)` e você deve estar na pasta do projeto. Confirme com:

```bash
pwd && ls *.csv
```

**9.5** Instalar as bibliotecas:

```bash
pip install --upgrade pip
```

```bash
pip install pandas numpy matplotlib seaborn jupyter google-cloud-bigquery google-cloud-storage pyarrow db-dtypes openpyxl
```

**9.6** Prevenir o problema de fim de linha (vai importar na Trilha C):

```bash
git config --global core.autocrlf input
```

---

## Passo 10 — Teste de fumaça

```bash
kenzie
```

```bash
python3 00_teste_conexao.py
```

Cinco OKs = Trilha 0 concluída.

---

## Passo 11 — Acesso para a equipe *(navegador)*

1. https://console.cloud.google.com/iam-admin/iam (com o projeto `Kenzie 360 MBA` selecionado)
2. **Conceder acesso** → e-mail Google da Giovanna e do Jonathas
3. Papéis para cada um: **BigQuery Data Editor**, **BigQuery Job User**, **Storage Admin**
4. Salvar

---

## Situação dos créditos — registrado em 21/08/2026

| Crédito | Valor restante | Validade | Serve para a Sprint 2? |
|---|---|---|---|
| Trial credit for GenAI App Builder | R$ 5.757,87 | 23/06/2027 | **Não.** Escopo restrito ao GenAI App Builder — não cobre BigQuery nem Cloud Storage |
| Free Trial | **R$ 1.117,39** | **21/09/2026** | **Sim.** É este que sustenta o projeto |
| Free Trial (anterior) | — | Expirado em 27/06/2026 | Não |

**Consumo previsto da Sprint 2:** menos de R$ 5. A base tem 100 MB e o BigQuery tem franquia permanente de 10 GiB de armazenamento e 1 TiB de consulta por mês.

### ⚠️ Ação com data marcada: 21/09/2026

Quando o Free Trial expira, o Google **para todos os recursos do projeto** e abre uma janela de 30 dias. Se ninguém fizer o upgrade para conta paga nessa janela, **os recursos são apagados em definitivo** — datasets, buckets e tudo que estiver dentro.

O MBA vai até a Fase 5. A Sprint 2 termina antes de 21/09, mas as Fases 3, 4 e 5 não.

**Recomendação:** fazer o upgrade para conta paga **antes de 21/09**. O upgrade não gera cobrança por si — ele só remove o teto do trial. O consumo do projeto continua dentro da franquia gratuita permanente do BigQuery, e o alerta de orçamento do Passo 8 permanece como rede de proteção. Os créditos restantes continuam valendo até a data de expiração deles.
