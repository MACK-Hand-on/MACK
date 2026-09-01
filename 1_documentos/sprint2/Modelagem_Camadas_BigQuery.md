# Modelagem das Camadas de Dados — BigQuery

**Projeto Kenzie 360 · Sprint 2 · Card 1**
Projeto GCP: `kenzie-360-mba` · Região: `us-central1` · Base: v8

---

## 1. Do desenho lógico à implementação

A Sprint 1 desenhou o Data Lake em três camadas (RAW → TRUSTED → CURATED) sobre a arquitetura Lambda. Este documento registra como esse desenho virou DDL no BigQuery, e por que cada decisão técnica foi tomada.

| Camada do Lake | Dataset | Papel | O que contém |
|---|---|---|---|
| **RAW** | `kenzie360_bronze` | Registro imutável da origem | Espelho fiel do CSV, tudo em STRING |
| **TRUSTED** | `kenzie360_silver` | Dado confiável e consultável | Tipado, deduplicado, particionado, PII tratada |
| **CURATED** | `kenzie360_gold` | Consumo por negócio | 10 views + 1 dimensão, uma por pergunta |

O bucket `gs://kenzie360-raw-ids26` guarda os arquivos originais antes da ingestão, versionados por data (`bronze/AAAAMMDD/`). Ele é o RAW de verdade — a bronze do BigQuery é a primeira materialização consultável.

---

## 2. Camada Bronze — o registro imutável

### 2.1 Regra da camada

**Nada é convertido.** Todas as 30 colunas de `atendimentos` e as 12 de `mensagens` são STRING, na ordem exata do arquivo de origem. Duas colunas de rastreabilidade são acrescentadas:

| Coluna | Tipo | Para que serve |
|---|---|---|
| `_ingestion_ts` | TIMESTAMP | Quando este registro entrou |
| `_source_file` | STRING | De qual arquivo do GCS veio |

Sem essas duas, a bronze não consegue provar a origem de um registro — e provar origem é metade do trabalho de governança em ambiente bancário. Hoje elas registram, por exemplo, que a base atual veio do arquivo `_v8.csv`.

### 2.2 Por que schema explícito, e não autodetecção

Três razões, todas descobertas na prática:

1. **O CSV começa com BOM** (marca invisível deixada pelo Excel). Com autodetecção, o BOM gruda no nome da primeira coluna, que vira `﻿id_conversa`. Schema explícito com `skip_leading_rows=1` descarta o cabeçalho e o BOM junto.
2. **Autodetecção adivinha tipos**, e a bronze exige STRING por definição.
3. **Schema explícito falha alto** se a origem mudar de formato — e falhar alto é desejável numa camada de ingestão.

### 2.3 O detalhe que quase corrompeu a carga

A inspeção da base encontrou **4.361 linhas em `atendimentos` e 4.842 em `mensagens` com ponto e vírgula dentro do texto** — o mesmo caractere usado como separador. Exemplo real:

```
"Encaminhei para a area de Mesa de Limites; retornaremos em ate 48h."
```

Esses campos vêm corretamente protegidos por aspas duplas, e a prova é que o número de linhas com aspas bate exatamente com o número de linhas com campo extra. Mas a carga só funciona porque declara `quote_character='"'`. Sem isso, os registros quebrariam em colunas a mais — sem erro, silenciosamente.

### 2.4 Configuração da carga

```python
source_format       = CSV
field_delimiter     = ";"
skip_leading_rows   = 1
quote_character     = '"'
allow_quoted_newlines = True
encoding            = "UTF-8"
write_disposition   = WRITE_TRUNCATE
```

`WRITE_TRUNCATE` torna a carga idempotente: rodar duas vezes produz o mesmo resultado, nunca duplicação.

---

## 3. Camada Silver — o dado confiável

### 3.1 Particionamento e clustering

| Tabela | Partição | Clustering |
|---|---|---|
| `atendimentos` | `data_ref` (DATE) | `segmento_cliente`, `categoria_assunto`, `idioma` |
| `mensagens` | `data_ref` (DATE) | `id_conversa`, `remetente` |

**Por que particionar por coluna DATE explícita** em vez de `PARTITION BY DATE(data_hora)`: a coluna `data_ref` é materializada na transformação, o que torna a partição legível no schema e dispensa a função na cláusula. O período tem 182 dias — bem abaixo do limite de 4.000 partições.

**Por que isso importa na prática:** sem partição, toda consulta do Looker Studio varreria as 405 mil mensagens inteiras. Com partição por data, um filtro de período lê só as partições necessárias. É a diferença entre caber e não caber na franquia de 1 TiB mensal.

**Por que esse clustering:** as três colunas de `atendimentos` são exatamente os filtros mais usados na EDA e no dashboard. Em `mensagens`, `id_conversa` acelera o join com atendimentos e `remetente` filtra as falas do cliente, que é o recorte mais frequente.

### 3.2 Decisões de tipo

| Decisão | Escolha | Motivo |
|---|---|---|
| `data_hora` | **DATETIME**, não TIMESTAMP | A origem não declara fuso horário. Converter para UTC seria inventar informação que o dado não tem |
| `resolvida` → `resolucao_declarada` | **STRING**, não BOOL | Tem 4 valores (Sim / Nao / Desconhecido / Nao aplicavel). Tratar como booleano jogaria fora a diferença entre "não resolveu" e "não se aplica" |
| `csat` | INT64 via FLOAT64 | Vem gravado como "5.0"; o cast direto para INT64 falha |
| Booleanos | `campo = 'True'` | Origem em formato Python. NULL na origem permanece NULL |
| Strings vazias | `NULLIF(TRIM(x), '')` | Vazio e NULL passam a ser a mesma coisa |

Todas as conversões usam `SAFE_CAST` e `SAFE.PARSE_DATETIME`: em vez de quebrar a carga, um valor inesperado vira NULL e aparece na validação.

### 3.3 Deduplicação

| Tabela | Chave de negócio |
|---|---|
| `atendimentos` | `id_conversa` |
| `mensagens` | `id_conversa` + `ordem` |

Quando há repetição, prevalece a ingestão mais recente (`ROW_NUMBER() OVER (PARTITION BY chave ORDER BY _ingestion_ts DESC)`). A validação confirma que linhas e chaves distintas batem exatamente: 36.000 e 405.073.

### 3.4 Mascaramento de PII

A transição bronze → silver aplica regex para e-mail e CPF sobre o texto livre, e marca com a coluna `pii_remascarada` as linhas em que a regra agiu.

Telefone ficou **deliberadamente de fora**: o padrão colide com valores monetários e números de protocolo, e um falso positivo destrói dado legítimo.

Na base atual a regra não encontra nada — os dados já nascem mascarados por construção. Ela permanece porque em produção a origem é um export real, onde essa garantia não existe. É rede de segurança, e o custo de mantê-la é zero.

**Divisão de responsabilidade entre camadas:** a bronze preserva o texto como veio; a silver entrega a versão tratada. O acesso à bronze é o mais restrito dos três — quem consulta a silver não precisa ver o original.

---

## 4. Camada Gold — o consumo

Nove views e uma dimensão. **Cada uma existe por causa de um achado específico da EDA** — nenhuma foi criada por completude.

| View | Pergunta que responde | Achado que a justifica |
|---|---|---|
| `vw_dim_assunto` | Que tipo de ação cada assunto exige? | Dimensão de apoio |
| `vw_kpi_diario` | Como o atendimento evoluiu dia a dia? | Sazonalidade (após correção L1) |
| `vw_autonomia_por_tipo_demanda` | Por que o bot resolve pouco? | Teste (a): 45,9% → 20,9% |
| `vw_funil_atendimento` | Onde o atendimento vaza? | Teste (c), revisado em 28/08: funil etapa a etapa — bot resolveu → pediu humano → desistiu na fila → humano atendeu → resolveu / não resolveu |
| `vw_funil_e_modos_de_falha` | (obsoleta) | Mantida como repasse da `vw_funil_atendimento`, para que relatórios já conectados recebam o dado corrigido |
| `vw_desempenho_areas_internas` | Que área devolve o caso sem resolver? | Teste (c), revisado em 28/08: denominador passou a ser "o humano atendeu" e a área vem de `vw_dim_assunto.area_padrao`. Resolução real ~84%, não ~68% |
| `vw_desfecho_e_custo` | Quanto custa cada desfecho? | CSAT bimodal |
| `vw_espiral_recorrencia` | O cliente que insiste é pior atendido? | A espiral: 29,9% → 15,4% |
| `vw_jornada_sentimento` | Onde na conversa o cliente se frustra? | Vale no 3º quinto |
| `vw_dores_priorizadas` | Em qual dor investir primeiro? | Score composto |
| `vw_features_nlp` | (insumo da Fase 4) | Sem alvo fixado — regra 5 do handoff |

**Views, não tabelas.** Não ocupam armazenamento, nunca ficam defasadas e herdam o particionamento da silver. O custo é recalcular a cada consulta — aceitável neste volume, e mitigado pelo cache do Looker Studio.

**Escala de custo medida:** consultar todas as views custa 48 MB, ou 0,004% da franquia mensal. A mais pesada é `vw_jornada_sentimento` (26 MB), única que percorre a tabela de mensagens.

---

## 5. Convenção de nomenclatura

| Elemento | Padrão | Exemplo |
|---|---|---|
| Dataset | `kenzie360_<camada>` | `kenzie360_silver` |
| Tabela | substantivo plural, minúsculo | `atendimentos` |
| View | prefixo `vw_` + o que responde | `vw_espiral_recorrencia` |
| Dimensão | prefixo `vw_dim_` | `vw_dim_assunto` |
| Coluna técnica | prefixo `_` | `_ingestion_ts` |
| Snapshot de versão | sufixo `_v7` | `atendimentos_v7` |
| Percentual | prefixo `pct_` | `pct_bot_resolve` |
| Contagem | substantivo direto | `conversas`, `resolvidas_bot` |

Sem acentos e sem espaços em qualquer identificador.

---

## 6. Governança

**Acesso por camada** — princípio de menor privilégio:

| Camada | Quem acessa | Papel IAM |
|---|---|---|
| bronze | Esteira de ingestão | BigQuery Data Editor |
| silver | Engenharia de dados | BigQuery Data Editor |
| gold | Analistas e Looker Studio | BigQuery Data Viewer |

O grupo usa papéis específicos (Data Editor, Job User, Storage Admin) em vez do papel Editor, que permitiria até apagar o projeto.

**Rastreabilidade:** `_ingestion_ts` e `_source_file` acompanham cada registro da bronze até a silver, permitindo responder "de onde veio este dado e quando entrou" para qualquer linha.

**Versionamento de dados:** a promoção da base v7 para v8 preservou a versão anterior em tabelas com sufixo `_v7`, nos dois datasets. As duas versões são consultáveis e comparáveis em SQL.

**LGPD:** a base é 100% sintética e nenhum dado pessoal foi utilizado. O pipeline de mascaramento está implementado mesmo assim, porque é ele que seria exercido num export real.

---

## 7. Custo

| Item | Consumo | Franquia mensal | Uso |
|---|---:|---:|---:|
| Armazenamento (v7 + v8, bronze + silver) | 0,543 GiB | 10 GiB | **5,4%** |
| Consultas (carga + EDA + gold, acumulado) | ~330 MB | 1 TiB | **0,03%** |

Alerta de orçamento configurado em US$ 20/mês com avisos em 10%, 50% e 90%.

---

## 8. Reprodutibilidade

Todo o ambiente é recriável a partir da pasta do projeto:

```bash
python3 gerar_dataset_cde_v8.py   # gera os CSVs (SEED = 42, deterministico)
python3 01_carga_bronze.py        # GCS + bronze
python3 02_cria_silver.py         # silver
python3 06_cria_gold.py           # gold
python3 05_inventario_bq.py       # confere o resultado
```

Cada script valida o próprio resultado e aborta se a contagem divergir do esperado. Os DDLs ficam versionados em `sql/`, separados do código que os executa — o SQL é revisável sem ler Python.
