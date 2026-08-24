terraform {
  backend "gcs" {
    bucket = "SEU_PROJECT_ID_DE_PRODUCAO_AQUI-tfstate"
    prefix = "kenzie-v2/prod"
  }
}
