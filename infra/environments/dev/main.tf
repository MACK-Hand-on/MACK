terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Diz ao Terraform qual projeto do GCP e região usar por padrão
provider "google" {
  project = var.project_id
  region  = var.region
}

# Aqui é onde "chamamos a receita": usamos o módulo data-lake
# passando os valores específicos do ambiente dev.
module "data_lake" {
  source      = "../../modules/data-lake"
  project_id  = var.project_id
  region      = var.region
  environment = "dev"
}
