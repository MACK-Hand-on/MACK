terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Sem nomes explícitos: em produção os recursos seriam criados do zero,
# então o módulo gera os nomes no padrão "<projeto>-kenzie-<camada>-prod".
module "data_lake" {
  source      = "../../modules/data-lake"
  project_id  = var.project_id
  region      = var.region
  environment = "prod"
}
