# Este arquivo define os "campos em branco" que o módulo precisa receber
# de fora para funcionar. Pense nisso como os campos de um formulário.

variable "project_id" {
  description = "ID do projeto no GCP onde os recursos serão criados"
  type        = string
}

variable "region" {
  description = "Região do GCP. us-central1 é a única com Always Free no Cloud Storage (decisão D3)."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Ambiente: dev, staging ou prod. Usado para nomear recursos e evitar colisão."
  type        = string
}

variable "raw_retention_days" {
  description = "Por quantos dias os dados crus (RAW) ficam guardados antes de serem apagados"
  type        = number
  default     = 365
}

# ─────────────────────────────────────────────────────────────
# Nomes explícitos dos recursos.
# Deixe null para o módulo gerar o nome padrão.
# Informe o nome real quando for ADOTAR um recurso já existente.
# ─────────────────────────────────────────────────────────────

variable "bucket_raw_name" {
  description = "Nome exato do bucket RAW. null = gerar padrão."
  type        = string
  default     = null
}

variable "dataset_bronze_id" {
  description = "ID exato do dataset BRONZE. null = gerar padrão."
  type        = string
  default     = null
}

variable "dataset_silver_id" {
  description = "ID exato do dataset SILVER/TRUSTED. null = gerar padrão."
  type        = string
  default     = null
}

variable "dataset_gold_id" {
  description = "ID exato do dataset GOLD/CURATED. null = gerar padrão."
  type        = string
  default     = null
}
