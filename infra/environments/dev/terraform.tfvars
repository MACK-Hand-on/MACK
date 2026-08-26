# Valores do ambiente que JÁ EXISTE no GCP (provisionado na Trilha 0).
# Estes nomes precisam bater exatamente com os recursos reais — é o que
# permite ao Terraform ADOTAR o ambiente (terraform import) em vez de
# criar um segundo data lake vazio ao lado do que tem os dados.

project_id = "kenzie-360-mba"
region     = "us-central1"

bucket_raw_name   = "kenzie360-raw-ids26"
dataset_bronze_id = "kenzie360_bronze"
dataset_silver_id = "kenzie360_silver"
dataset_gold_id   = "kenzie360_gold"
