variable "project_id" {
  description = "ID do projeto GCP de desenvolvimento"
  type        = string
}

variable "region" {
  description = "Região do GCP"
  type        = string
  default     = "us-central1"
}

variable "bucket_raw_name" {
  description = "Nome exato do bucket RAW já existente"
  type        = string
}

variable "dataset_bronze_id" {
  description = "ID exato do dataset BRONZE já existente"
  type        = string
}

variable "dataset_silver_id" {
  description = "ID exato do dataset SILVER já existente"
  type        = string
}

variable "dataset_gold_id" {
  description = "ID exato do dataset GOLD já existente"
  type        = string
}
