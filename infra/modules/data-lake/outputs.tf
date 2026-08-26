# Outputs são "valores de saída" que outros módulos (ex: IAM, Composer)
# vão poder usar depois, sem precisar redigitar os nomes na mão.

output "raw_bucket_name" {
  description = "Nome do bucket RAW"
  value       = google_storage_bucket.raw.name
}

output "bronze_dataset_id" {
  description = "ID do dataset BRONZE"
  value       = google_bigquery_dataset.bronze.dataset_id
}

output "silver_dataset_id" {
  description = "ID do dataset SILVER/TRUSTED"
  value       = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset_id" {
  description = "ID do dataset GOLD/CURATED"
  value       = google_bigquery_dataset.gold.dataset_id
}
