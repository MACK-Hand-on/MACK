# ─────────────────────────────────────────────────────────────
# MÓDULO DATA LAKE — Kenzie 360
#
# Três camadas, na nomenclatura "medalhão" que o projeto usa:
#   bronze  = RAW tabelado      (CSV materializado, com rastreabilidade)
#   silver  = TRUSTED           (limpo, deduplicado, PII tratada)
#   gold    = CURATED           (pronto para dashboard e modelo de NLP)
#
# Os nomes dos recursos são parametrizáveis. Quando não informados,
# o módulo cai no padrão "<projeto>-kenzie-<camada>-<ambiente>".
# Isso permite ADOTAR o ambiente que já existe no GCP (terraform import)
# sem perder a capacidade de criar um ambiente novo do zero.
# ─────────────────────────────────────────────────────────────

locals {
  bucket_raw_name   = coalesce(var.bucket_raw_name, "${var.project_id}-kenzie-raw-${var.environment}")
  dataset_bronze_id = coalesce(var.dataset_bronze_id, "kenzie_bronze_${var.environment}")
  dataset_silver_id = coalesce(var.dataset_silver_id, "kenzie_silver_${var.environment}")
  dataset_gold_id   = coalesce(var.dataset_gold_id, "kenzie_gold_${var.environment}")

  labels_comuns = {
    projeto  = "kenzie-360"
    ambiente = var.environment
  }
}

# ─────────────────────────────────────────────────────────────
# CAMADA RAW — onde os logs da Kenzie chegam "crus", sem tratamento.
# É um bucket (uma pasta gigante no Google Cloud Storage).
# ─────────────────────────────────────────────────────────────
resource "google_storage_bucket" "raw" {
  name     = local.bucket_raw_name
  project  = var.project_id
  location = var.region

  # Impede que alguém apague o bucket sem querer (só apaga com um passo extra)
  force_destroy = false

  # Ninguém consegue tornar esse bucket público por engano
  public_access_prevention    = "enforced"
  uniform_bucket_level_access = true

  # Guarda versões antigas de um arquivo caso algo seja sobrescrito por engano
  versioning {
    enabled = true
  }

  # Apaga dados automaticamente após X dias (evita acumular custo/risco pra sempre)
  lifecycle_rule {
    condition {
      age = var.raw_retention_days
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(local.labels_comuns, { camada = "raw" })
}

# ─────────────────────────────────────────────────────────────
# CAMADA BRONZE — o CSV do bucket materializado como tabela consultável,
# com as colunas de rastreabilidade _ingestion_ts e _source_file.
# É o primeiro ponto onde o dado vira SQL.
# ─────────────────────────────────────────────────────────────
resource "google_bigquery_dataset" "bronze" {
  dataset_id  = local.dataset_bronze_id
  project     = var.project_id
  location    = var.region
  description = "Camada BRONZE - dado cru tabelado, com rastreabilidade de ingestao"

  labels = merge(local.labels_comuns, { camada = "bronze" })
}

# ─────────────────────────────────────────────────────────────
# CAMADA SILVER (TRUSTED) — dados já limpos, sem duplicidade, com PII tratada.
# É uma "gaveta" dentro do BigQuery (dataset) onde as tabelas moram.
# ─────────────────────────────────────────────────────────────
resource "google_bigquery_dataset" "silver" {
  dataset_id  = local.dataset_silver_id
  project     = var.project_id
  location    = var.region
  description = "Camada SILVER/TRUSTED - dados limpos, deduplicados e com PII tratada"

  labels = merge(local.labels_comuns, { camada = "silver" })
}

# ─────────────────────────────────────────────────────────────
# CAMADA GOLD (CURATED) — dados prontos para consumo:
# dashboard no Looker Studio e modelo de ML.
# ─────────────────────────────────────────────────────────────
resource "google_bigquery_dataset" "gold" {
  dataset_id  = local.dataset_gold_id
  project     = var.project_id
  location    = var.region
  description = "Camada GOLD/CURATED - pronta para dashboards e modelo de NLP"

  labels = merge(local.labels_comuns, { camada = "gold" })
}
