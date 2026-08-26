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
#
# Os nomes são passados explicitamente porque estes recursos já existem
# no GCP e serão adotados pelo Terraform, não recriados.
module "data_lake" {
  source      = "../../modules/data-lake"
  project_id  = var.project_id
  region      = var.region
  environment = "dev"

  bucket_raw_name   = var.bucket_raw_name
  dataset_bronze_id = var.dataset_bronze_id
  dataset_silver_id = var.dataset_silver_id
  dataset_gold_id   = var.dataset_gold_id
}

output "raw_bucket_name" { value = module.data_lake.raw_bucket_name }
output "bronze_dataset_id" { value = module.data_lake.bronze_dataset_id }
output "silver_dataset_id" { value = module.data_lake.silver_dataset_id }
output "gold_dataset_id" { value = module.data_lake.gold_dataset_id }
