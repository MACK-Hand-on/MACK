# Este arquivo define os "campos em branco" que o módulo precisa receber
# de fora para funcionar. Pense nisso como os campos de um formulário.

variable "project_id" {
  description = "ID do projeto no GCP onde os recursos serão criados"
  type        = string
}

variable "region" {
  description = "Região do GCP (ex: us-central1, southamerica-east1)"
  type        = string
  default     = "southamerica-east1"
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
