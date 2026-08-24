variable "project_id" {
  description = "ID do projeto GCP de produção"
  type        = string
}

variable "region" {
  description = "Região do GCP"
  type        = string
  default     = "southamerica-east1"
}
