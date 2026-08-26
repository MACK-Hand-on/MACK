# AMBIENTE DE PRODUÇÃO — estrutura documentada, ainda NÃO provisionada.
#
# O projeto acadêmico roda em um único projeto GCP (kenzie-360-mba).
# Este ambiente existe para demonstrar a separação dev/prod que a
# arquitetura prevê. Ele só deve ser aplicado quando houver um projeto
# GCP de produção de fato — por isso os jobs de prod no workflow rodam
# apenas sob acionamento manual (workflow_dispatch).
terraform {
  backend "gcs" {
    bucket = "SUBSTITUIR-PELO-BUCKET-DE-ESTADO-DE-PRODUCAO"
    prefix = "kenzie-360/prod"
  }
}
