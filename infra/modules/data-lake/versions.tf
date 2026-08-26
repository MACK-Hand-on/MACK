# Um módulo deve declarar de que provider e de que versão do Terraform ele
# depende. Sem isso, o módulo funciona por acidente: herda o que o ambiente
# que o chamou tiver configurado, e quebra silenciosamente se for reutilizado
# em outro lugar com uma versão diferente.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
