# O "backend" é onde o Terraform guarda o registro do que ele já criou
# (chamado de "state"). Sem isso, ele esqueceria tudo a cada execução
# e tentaria recriar (ou duplicar) recursos.
#
# ATENÇÃO: o bucket abaixo precisa existir ANTES de rodar terraform init.
# Ele é o único recurso deste projeto criado manualmente uma vez, porque
# o Terraform não pode guardar o registro de si mesmo antes de existir
# um lugar pra guardá-lo.
#
# Este bucket JÁ EXISTE — foi criado na Trilha 0 do projeto.
# O bloco backend não aceita variáveis: o valor precisa ser literal.
terraform {
  backend "gcs" {
    bucket = "kenzie360-tfstate-ids26"
    prefix = "kenzie-360/dev"
  }
}
