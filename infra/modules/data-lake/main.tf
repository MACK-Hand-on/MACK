# ─────────────────────────────────────────────────────────────
# CAMADA RAW — onde os logs da Kenzie chegam "crus", sem tratamento.
# É um bucket (uma pasta gigante no Google Cloud Storage).
# ─────────────────────────────────────────────────────────────
resource "google_storage_bucket" "raw" {
  name     = "${var.project_id}-kenzie-raw-${var.environment}"
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

  labels = {
    camada   = "raw"
    projeto  = "kenzie-v2"
    ambiente = var.environment
  }
}

# ─────────────────────────────────────────────────────────────
# CAMADA TRUSTED — dados já limpos, sem duplicidade, com PII tratada.
# É uma "gaveta" dentro do BigQuery (dataset) onde as tabelas moram.
# ─────────────────────────────────────────────────────────────
resource "google_bigquery_dataset" "trusted" {
  dataset_id  = "kenzie_trusted_${var.environment}"
  project     = var.project_id
  location    = var.region
  description = "Camada TRUSTED - dados limpos, deduplicados e com PII tratada"

  labels = {
    camada   = "trusted"
    projeto  = "kenzie-v2"
    ambiente = var.environment
  }
}

# ─────────────────────────────────────────────────────────────
# CAMADA CURATED — dados prontos para consumo: dashboard e modelo de ML.
# ─────────────────────────────────────────────────────────────
resource "google_bigquery_dataset" "curated" {
  dataset_id  = "kenzie_curated_${var.environment}"
  project     = var.project_id
  location    = var.region
  description = "Camada CURATED - pronta para dashboards e modelo de NLP"

  labels = {
    camada   = "curated"
    projeto  = "kenzie-v2"
    ambiente = var.environment
  }
}
