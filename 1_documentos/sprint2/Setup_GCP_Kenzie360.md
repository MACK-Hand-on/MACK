# Trilha 0 — Fundação GCP · Roteiro de execução

**Projeto Kenzie 360 · Sprint 2**
Tempo estimado: **60 a 90 minutos.**
Cobre dois ambientes: **Windows (CMD)** e **Ubuntu no WSL**.
Executado por: Ilan · Repetível por Giovanna e Jonathas

---

## Escolha do ambiente — leia antes de tudo

O roteiro funciona nos dois. Escolha o seu e siga apenas a coluna correspondente onde houver bifurcação.

| | **Trilha A — Windows (CMD)** | **Trilha B — Ubuntu no WSL** |
|---|---|---|
| Para quem | Nunca usou Linux, ou quer o caminho de menor atrito hoje | Já tem WSL rodando e é confortável com bash |
| Vantagem | Zero configuração extra. O instalador resolve tudo | Espelha o ambiente do GitHub Actions (que roda Ubuntu). Terraform e git funcionam melhor. Comando da documentação cola e roda |
| Custo | Terraform na Trilha C fica um pouco mais chato | 15 minutos de configuração inicial e três armadilhas conhecidas (todas cobertas abaixo) |

**Recomendação para o Ilan:** Trilha B (Ubuntu). Você já usou WSL, e a Trilha C é toda Terraform e GitHub Actions — ambos nasceram em Linux. O ganho aparece daqui a duas semanas, não hoje.

### ⚠️ A regra que não pode ser quebrada, em qualquer trilha

**Os arquivos do projeto continuam em `C:\Users\<seu-usuario>\Claude\Projects\Projeto Kenzie 360`. Não mova a pasta para dentro do WSL.**

Essa pasta é a que está conectada ao Claude. Se o projeto for para `~/kenzie360` dentro do Linux, eu deixo de enxergar os arquivos e a nossa colaboração quebra — cada script passaria a ser copiado na mão.

Do Ubuntu, essa pasta é acessível assim:

```bash
cd "/mnt/c/Users/<seu-usuario>/Claude/Projects/Projeto Kenzie 360"
```

Funciona normalmente. É só um pouco mais lenta que o disco nativo do Linux, e a seção de armadilhas explica como contornar o único ponto onde isso incomoda.

---

## Antes de começar

- Sua conta Google que já tem GCP com créditos
- O terminal escolhido:
  - **Trilha A:** tecla Windows → digite `cmd` → Enter
  - **Trilha B:** tecla Windows → digite `ubuntu` → Enter
- 90 minutos sem interrupção

**Convenção:** tudo em bloco de código é para copiar, colar e apertar Enter. Onde aparecer `SEU-PROJECT-ID` ou `SEU-SUFIXO`, troque pelo valor real antes de rodar.

---

## Passo 1 — Conferir os créditos *(navegador, igual nas duas trilhas)*

Créditos GCP **têm data de validade**. Precisamos saber quanto resta e até quando.

1. Abra https://console.cloud.google.com/billing
2. Clique na sua conta de faturamento
3. Menu da esquerda → **Créditos** (*Credits*)
4. Anote: **valor restante**, **data de expiração** e o **nome da conta de faturamento**

> Se os créditos expirarem no meio da sprint, o custo passa a cair no cartão. Nosso consumo previsto é de poucos dólares, mas você precisa saber disso antes, não pela fatura.

---

## Passo 2 — Criar o projeto *(navegador)*

Um projeto novo, separado do que você usou no Kaggle. Isso mantém o custo do MBA isolado e rastreável.

1. https://console.cloud.google.com
2. No topo, clique no **seletor de projeto** (ao lado do logo "Google Cloud")
3. **Novo projeto** (canto superior direito da janela)
4. Preencha:
   - **Nome:** `Kenzie 360 MBA`
   - **ID do projeto:** clique em **Editar** e coloque `kenzie360-mba`
   - **Organização:** deixe como está
5. **Criar**

> **Erro de ID já em uso?** O Project ID é único no mundo inteiro. Tente `kenzie360-mba-2026` ou `kenzie360-mackenzie`. **Anote o que funcionou.**

**Meu Project ID:** `________________________`

---

## Passo 3 — Vincular o faturamento *(navegador)*

1. Menu (☰) → **Faturamento**
2. Se aparecer "Este projeto não tem conta de faturamento" → **Vincular conta de faturamento**
3. Selecione a conta com os créditos → confirme

**Deu certo se:** a tela de Faturamento passa a mostrar o resumo do projeto com R$ 0,00.

---

## Passo 4 — Instalar o gcloud CLI

O `gcloud` comanda a nuvem pelo terminal em vez de por telas. É ele que torna o trabalho reproduzível — e reprodutibilidade é metade da nota.

### 🅐 Trilha A — Windows (CMD)

1. Baixe: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
2. Execute
3. Opções padrão. **Na última tela, DESMARQUE** "Start Google Cloud SDK Shell" e deixe marcado rodar `gcloud init`
4. Um terminal abre sozinho e o navegador pede login. Autorize
5. Ao perguntar o projeto, escolha `kenzie360-mba`

### 🅑 Trilha B — Ubuntu no WSL

Quatro comandos, um de cada vez:

```bash
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
```

```bash
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
```

```bash
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
```

```bash
sudo apt-get update && sudo apt-get install -y google-cloud-cli
```

Depois inicialize:

```bash
gcloud init
```

> **Armadilha 1 do WSL — o navegador.** Se o `gcloud init` travar em "Go to the following link in your browser" sem abrir nada, cancele com `Ctrl+C` e rode assim:
>
> ```bash
> gcloud init --console-only
> ```
>
> Ele imprime uma URL. Copie, cole no Chrome do Windows, autorize, e cole o código de verificação de volta no terminal. Funciona igual — só tem duas etapas a mais.

### Conferir (as duas trilhas)

Abra um terminal **novo** e rode:

```
gcloud --version
```

Deve listar "Google Cloud SDK" com um número de versão. Se der "comando não reconhecido" no Windows, reinicie o computador — o PATH precisa recarregar.

### Fixar o projeto padrão

```
gcloud config set project SEU-PROJECT-ID
```

```
gcloud config list
```

Deve mostrar `project = kenzie360-mba`.

---

## Passo 5 — Autorizar as bibliotecas Python

O `gcloud init` autenticou **você**. Este comando autentica os **scripts Python**. São duas coisas diferentes, e esquecer a segunda é o erro nº 1 de quem está começando — a mensagem de erro que aparece depois não deixa nada óbvio.

```
gcloud auth application-default login
```

**Na Trilha B, se o navegador não abrir:**

```bash
gcloud auth application-default login --no-launch-browser
```

---

## Passo 6 — Habilitar as APIs

Na GCP cada serviço vem desligado. Este comando liga todos os da Sprint 2 de uma vez:

```
gcloud services enable bigquery.googleapis.com storage.googleapis.com iam.googleapis.com cloudresourcemanager.googleapis.com run.googleapis.com cloudscheduler.googleapis.com bigquerydatatransfer.googleapis.com
```

Demora 1 a 2 minutos, sem barra de progresso. Quando o cursor voltar, terminou.

```
gcloud services list --enabled
```

---

## Passo 7 — Criar os dois buckets

Nomes de bucket são **únicos no mundo inteiro**. Escolha um sufixo pessoal — sugiro iniciais + ano, ex.: `ids26`.

**Meu sufixo:** `________`

**7.1 — Bucket do RAW** (onde os CSVs vão morar):

```
gcloud storage buckets create gs://kenzie360-raw-SEU-SUFIXO --location=us-central1 --uniform-bucket-level-access
```

**7.2 — Bucket do estado do Terraform** (o Jonathas vai precisar na Trilha C; criar agora evita retrabalho):

```
gcloud storage buckets create gs://kenzie360-tfstate-SEU-SUFIXO --location=us-central1 --uniform-bucket-level-access
```

```
gcloud storage buckets update gs://kenzie360-tfstate-SEU-SUFIXO --versioning
```

**Conferir:**

```
gcloud storage ls
```

> **Erro de nome em uso?** Troque o sufixo e rode de novo.

---

## Passo 8 — Alerta de orçamento *(navegador)*

**Não é opcional.** É a rede de segurança contra uma consulta mal escrita queimar seus créditos.

1. Menu (☰) → **Faturamento** → **Orçamentos e alertas**
2. **Criar orçamento**
3. **Escopo:** em "Projetos", selecione **apenas** o `kenzie360-mba`. Sem filtrar, o alerta considera todos os seus projetos
4. **Valor:** `20` dólares, opção "Valor especificado"
5. **Ações:** alertas em **10%, 50% e 90%** → e-mail em US$ 2, US$ 10 e US$ 18
6. Marque **"Enviar alertas por e-mail aos administradores de faturamento"**
7. Salvar

> O orçamento **avisa, não bloqueia**. Mas com 100 MB de base, chegar em US$ 2 já significa que algo está muito errado — e você fica sabendo no mesmo dia.

---

## Passo 9 — Ambiente Python

### 🅐 Trilha A — Windows (CMD)

```
python --version
```

Se der erro ou abrir a Microsoft Store, instale de https://www.python.org/downloads/ e **marque "Add Python to PATH"** na primeira tela. É a caixa que todo mundo esquece.

```
cd /d "C:\Users\<seu-usuario>\Claude\Projects\Projeto Kenzie 360"
```

```
python -m venv .venv
```

```
.venv\Scripts\activate
```

### 🅑 Trilha B — Ubuntu no WSL

```bash
sudo apt-get install -y python3 python3-pip python3-venv
```

> **Armadilha 2 do WSL — onde criar o ambiente virtual.** Criar o `.venv` dentro de `/mnt/c/` funciona, mas fica lento e às vezes dá problema de permissão de execução. A solução é manter **os dados no Windows** e o **ambiente virtual no Linux**:

```bash
mkdir -p ~/.venvs && python3 -m venv ~/.venvs/kenzie360
```

```bash
source ~/.venvs/kenzie360/bin/activate
```

```bash
cd "/mnt/c/Users/<seu-usuario>/Claude/Projects/Projeto Kenzie 360"
```

Para facilitar, crie um atalho permanente:

```bash
echo "alias kenzie='source ~/.venvs/kenzie360/bin/activate && cd \"/mnt/c/Users/<seu-usuario>/Claude/Projects/Projeto Kenzie 360\"'" >> ~/.bashrc && source ~/.bashrc
```

A partir daí, basta digitar `kenzie` no terminal para cair no projeto com o ambiente ativado.

### Instalar as bibliotecas *(as duas trilhas, com o ambiente ativado)*

Depois de ativar, o começo da linha mostra `(.venv)` ou `(kenzie360)`.

```
pip install --upgrade pip
```

```
pip install pandas numpy matplotlib seaborn jupyter google-cloud-bigquery google-cloud-storage pyarrow db-dtypes openpyxl
```

Leva de 3 a 5 minutos.

---

## Passo 10 — Teste de fumaça

O arquivo `00_teste_conexao.py` já está na pasta do projeto. Com o ambiente ativado e dentro da pasta:

**Trilha A:** `python 00_teste_conexao.py`
**Trilha B:** `python3 00_teste_conexao.py`

Ele faz 5 checagens e imprime um relatório. **Cinco OKs = Trilha 0 concluída.**

---

## Passo 11 — Dar acesso à Giovanna e ao Jonathas *(navegador)*

1. Menu (☰) → **IAM e administrador** → **IAM**
2. **Conceder acesso**
3. Em "Novos principais", o e-mail Google de cada um
4. Papéis para os dois:
   - **BigQuery Data Editor** — criar e alterar tabelas
   - **BigQuery Job User** — rodar consultas
   - **Storage Admin** — gerenciar os buckets
5. Salvar

> **Por que não dar "Editor" e pronto:** o papel Editor permite até apagar o projeto. Atribuir papéis específicos é o princípio de **menor privilégio** — o mesmo raciocínio que vamos documentar na governança da Trilha C. Fazer certo aqui já vira material de entrega.

---

## Armadilhas do WSL — as três que importam

Se você escolheu a Trilha B, estas são as únicas coisas que costumam morder mais adiante. Todas têm solução de uma linha.

**1. Navegador não abre na autenticação.**
Sintoma: o comando trava esperando um retorno que nunca vem.
Solução: `--console-only` no `gcloud init`, `--no-launch-browser` no `application-default login`. Já está nos Passos 4 e 5. Atenção: `--no-browser` (sem o "launch") é outra coisa — exige uma segunda máquina com gcloud instalado. Não é o seu caso.

**2. Ambiente virtual dentro de `/mnt/c/`.**
Sintoma: `pip install` lentíssimo, ou `Permission denied` ao ativar.
Solução: venv no home do Linux, dados no Windows. Já está no Passo 9B.

**3. Fim de linha (CRLF vs LF) — só aparece na Trilha C.**
Sintoma: você cria um script no Windows, roda no Linux e recebe `bad interpreter: No such file or directory`. Acontece porque o Windows termina linha com dois caracteres e o Linux com um.
Solução preventiva, rode uma vez agora:

```bash
git config --global core.autocrlf input
```

Isso evita duas horas de confusão quando o repositório do Jonathas entrar em cena.

---

## Definição de pronto ✅

- [ ] `gcloud config list` mostra o projeto `kenzie360-mba`
- [ ] `gcloud storage ls` lista os dois buckets
- [ ] Orçamento de US$ 20 criado, com escopo no projeto certo
- [ ] `00_teste_conexao.py` retorna 5 OKs
- [ ] Giovanna e Jonathas abrem o projeto no console
- [ ] Anotado: Project ID, sufixo dos buckets, valor e validade dos créditos

---

## Nota técnica: por que criar na mão se a Trilha C usa Terraform?

Pergunta legítima, e a resposta entra no documento final.

O que criamos aqui na mão é a **fundação** — projeto, APIs, buckets, permissões. Muda raramente e, na prática de mercado, é mesmo provisionada uma vez e versionada depois (o chamado *bootstrap*).

O que o Terraform vai gerenciar são os **datasets e tabelas do BigQuery**, que mudam a cada evolução do modelo. É ali que o IaC ganha valor real.

Se tentássemos fazer o Terraform criar o próprio bucket onde ele guarda o estado, cairíamos num problema de ovo e galinha. Toda documentação séria de Terraform no GCP resolve do mesmo jeito: bootstrap manual, resto versionado. Vale um parágrafo no `CI_CD_IaC_Kenzie360.md`.

---

## O que me mandar quando terminar

1. Seu **Project ID** final
2. O **sufixo** dos buckets
3. A saída do `00_teste_conexao.py` (print da tela serve)
4. Valor e validade dos créditos
5. Qual trilha você seguiu (A ou B) — para eu ajustar os comandos dos próximos scripts
