# Outputs são "valores de saída" que outros módulos (ex: IAM, Composer)
# vão poder usar depois, sem precisar redigitar os nomes na mão.

output "raw_bucket_name" {
  description = "Nome do bucket RAW criado"
  value       = google_storage_bucket.raw.name
}

output "trusted_dataset_id" {
  description = "ID do dataset TRUSTED criado"
  value       = google_bigquery_dataset.trusted.dataset_id
}

output "curated_dataset_id" {
  description = "ID do dataset CURATED criado"
  value       = google_bigquery_dataset.curated.dataset_id
}
