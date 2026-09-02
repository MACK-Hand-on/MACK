# Rascunho da Arquitetura Lambda na GCP — Projeto Kenzie 360

> Desenho lógico (Sprint 1) do fluxo de dados da Kenzie (bot de atendimento V2).
> Objetivo: mostrar como os logs conversacionais dos correntistas (majoritariamente CDE) percorrem
> as camadas **Batch**, **Speed** e **Serving**, mapeadas ao modelo de
> Data Lake **RAW → TRUSTED → CURATED**.

---

## 1. Visão geral (o fluxo em uma frase)

As conversas do bot entram no sistema, são armazenadas de forma bruta,
processadas em dois "trilhos" paralelos (lote e tempo real), consolidadas
num repositório analítico e, por fim, exibidas em dashboards para o negócio.

```
                          ┌─────────────────────────────┐
                          │        SOURCE SYSTEMS        │
                          │  Take Blip / WhatsApp (bot   │
                          │  Kenzie) + atendimento humano│
                          │  (WhatsApp, telefone, e-mail)│
                          └───────────────┬─────────────┘
                                          │  (logs de conversa)
                          ┌───────────────▼─────────────┐
                          │   DATA ACQUISITION / INGEST  │
                          │  Cloud Functions / Pub/Sub   │
                          │  + mascaramento de PII       │
                          └──────┬───────────────┬───────┘
                                 │               │
              ┌──────────────────▼───┐   ┌───────▼───────────────────┐
              │      BATCH LAYER      │   │        SPEED LAYER        │
              │  (histórico, lotes)   │   │   (tempo real, streaming) │
              │                       │   │                           │
              │ Cloud Storage (RAW)   │   │ Pub/Sub → Dataflow (stream)│
              │ Dataflow / BigQuery   │   │ atualizações incrementais │
              │ (batch) processa      │   │ no BigQuery               │
              └───────────┬───────────┘   └───────────┬───────────────┘
                          │                           │
                          └─────────────┬─────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │       SERVING LAYER        │
                          │  BigQuery (tabelas CURATED)│
                          │  → Looker Studio (dashboard)│
                          └────────────────────────────┘
```

---

## 2. As três camadas da Arquitetura Lambda

### 2.1 Batch Layer (Camada de Lote) — "a fonte da verdade histórica"

Processa **grandes volumes de dados acumulados**, em intervalos programados
(ex.: de hora em hora ou 1x por dia). É onde ficam as análises completas e
consistentes de todo o histórico de atendimentos.

- **Ingestão / Armazenamento bruto:** os logs chegam e são gravados "como
  vieram" no **Google Cloud Storage** (nosso repositório RAW), em arquivos
  CSV/JSON. Nesta Sprint 1, as nossas duas bases —
  `dataset_kenzie360_atendimentos.csv` (conversas) e
  `dataset_kenzie360_mensagens.csv` (histórico turno a turno) — representam
  exatamente essa entrada.
- **Processamento em lote:** o **Dataflow** (ou consultas SQL no próprio
  **BigQuery**) limpa, padroniza e organiza os dados.
- **Serviços GCP:** Cloud Storage + BigQuery + Dataflow.

### 2.2 Speed Layer (Camada de Velocidade) — "o tempo real"

Processa os dados **assim que eles acontecem**, entregando visão imediata
(ex.: um pico súbito de reclamações de "Bloqueio de PIX" nas últimas horas).
Cobre a defasagem natural da camada de lote.

- **Mensageria / streaming:** o **Pub/Sub** recebe cada nova conversa como um
  evento em tempo real; o **Dataflow em modo streaming** processa e injeta
  atualizações incrementais no BigQuery.
- **Serviços GCP:** Pub/Sub + Dataflow (streaming).

> Nota didática: nesta fase acadêmica, a Speed Layer é **simulada/conceitual**.
> Nosso MVP roda no trilho Batch (arquivo CSV), e desenhamos a Speed Layer para
> demonstrar domínio do conceito, como exige a arquitetura Lambda.

### 2.3 Serving Layer (Camada de Servição/Consumo) — "onde o negócio enxerga"

Combina os resultados do Batch e do Speed e os **apresenta ao usuário final**.

- **Armazenamento analítico:** o **BigQuery** guarda as tabelas já tratadas
  (camada CURATED), otimizadas para consulta rápida (SQL).
- **Visualização:** o **Looker Studio** conecta-se ao BigQuery e exibe os
  KPIs e insights em dashboards para diretoria e áreas de negócio.
- **Serviços GCP:** BigQuery + Looker Studio.

---

## 3. Mapeamento para o Data Lake (RAW → TRUSTED → CURATED)

O professor pede a simulação das camadas de um Data Lake. Veja como elas se
encaixam na nossa arquitetura Lambda na GCP:

| Camada do Lake | O que é | Ferramenta GCP | Exemplo de conteúdo |
|---|---|---|---|
| **RAW** (Bruta) | Dado cru, exatamente como chega da fonte | Cloud Storage (bucket) | `dataset_kenzie360_atendimentos.csv` original, sem tratamento |
| **TRUSTED** (Confiável) | Dado limpo, padronizado e validado | Dataflow / BigQuery (SQL) | Datas convertidas, textos limpos, nulos tratados, tipos corrigidos |
| **CURATED** (Refinada) | Dado modelado e pronto para consumo | BigQuery (tabelas/views) | Tabelas agregadas por categoria, KPIs, features para o modelo de NLP |

---

## 4. Governança (visão inicial, a detalhar na Sprint 2)

- **Catálogo de dados:** dicionário das duas tabelas — conversas (30 colunas, com `status_conversa`/`resolvida`/`origem`) e mensagens/histórico (12 colunas, com o interlocutor `Atendente Humano` e `tipo_midia`) — detalhado na Seção 4 do Briefing. O fluxo que origina esses campos está especificado em `Fluxo_Conversacional_Kenzie360.md`.
- **Descaracterização (LGPD by design):** pipeline de mascaramento aplicado já na ingestão — dados pessoais digitados no chat (CPF, telefone, e-mail, conta) são substituídos por marcadores antes de chegarem à camada RAW; o identificador do cliente é pseudonimizado por hash. Campos de rastreio: `contem_dado_mascarado` e `qtd_dados_mascarados`.
- **Políticas de acesso:** controle via IAM do GCP (quem lê/escreve cada camada).
- **LGPD (simulada):** uso de dados 100% sintéticos; anonimização por design.
- **Classificação de sensibilidade:** campos de texto livre (`texto`, `primeira_mensagem_cliente`, `transcricao_completa`) tratados como sensíveis e sujeitos ao mascaramento.
