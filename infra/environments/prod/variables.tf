variable "project_id" {
  description = "ID do projeto GCP de produção"
  type        = string
}

variable "region" {
  description = "Região do GCP. Mantida igual à de dev: o BigQuery não faz join entre regiões."
  type        = string
  default     = "us-central1"
}
