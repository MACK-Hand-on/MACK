# O "backend" é onde o Terraform guarda o registro do que ele já criou
# (chamado de "state"). Sem isso, ele esqueceria tudo a cada execução
# e tentaria recriar (ou duplicar) recursos.
#
# ATENÇÃO: o bucket abaixo precisa existir ANTES de rodar terraform init.
# Ele é o único recurso deste projeto que você cria manualmente uma vez
# (veja o passo 1 do README.md), porque o Terraform não pode guardar
# o registro de si mesmo antes de existir um lugar pra guardá-lo.
terraform {
  backend "gcs" {
    bucket = "SEU_PROJECT_ID_AQUI-tfstate"
    prefix = "kenzie-v2/dev"
  }
}
