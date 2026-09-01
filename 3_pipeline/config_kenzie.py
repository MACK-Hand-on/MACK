# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2
Configuracao central. Todos os scripts do pipeline importam daqui.

Se algum parametro mudar (projeto, bucket, regiao, versao da base),
altere SO NESTE ARQUIVO.

Este arquivo vive em 3_pipeline/ e resolve os caminhos a partir dele:

    Projeto Kenzie 360/
    |- 2_dados/            <- CSVs de entrada
    |- 3_pipeline/         <- este arquivo e os scripts
    |  |- sql/             <- DDLs versionados
    |- 5_resultados_eda/   <- saida das consultas da EDA
"""

from pathlib import Path

# ---------------------------------------------------------------- GCP
PROJETO = "kenzie-360-mba"
REGIAO = "us-central1"
BUCKET_RAW = "kenzie360-raw-ids26"
BUCKET_TFSTATE = "kenzie360-tfstate-ids26"

# ---------------------------------------------------------------- Datasets
DS_BRONZE = "kenzie360_bronze"
DS_SILVER = "kenzie360_silver"
DS_GOLD = "kenzie360_gold"

# ---------------------------------------------------------------- Versao da base
# v7 = base original da Sprint 1
# v8 = recalibrada apos a EDA (sazonalidade, fuso do CDE, atrito acumulado)
#      ver 1_documentos/sprint2/Calibracao_Gemeo_v8.md
VERSAO_BASE = "v8"

# ---------------------------------------------------------------- Caminhos
PASTA_PIPELINE = Path(__file__).resolve().parent          # 3_pipeline/
PASTA_PROJETO = PASTA_PIPELINE.parent                     # raiz do projeto
PASTA_DADOS = PASTA_PROJETO / "2_dados"
PASTA_SQL = PASTA_PIPELINE / "sql"
PASTA_SAIDA_EDA = PASTA_PROJETO / "5_resultados_eda"
PASTA_MODELO = PASTA_PROJETO / "7_modelo"        # artefatos da Fase 4 (NLP)

if VERSAO_BASE == "v8":
    CSV_ATENDIMENTOS = PASTA_DADOS / "atual_v8" / "dataset_kenzie360_atendimentos_v8.csv"
    CSV_MENSAGENS = PASTA_DADOS / "atual_v8" / "dataset_kenzie360_mensagens_v8.csv"
else:
    CSV_ATENDIMENTOS = PASTA_DADOS / "historico_v7" / "dataset_kenzie360_atendimentos.csv"
    CSV_MENSAGENS = PASTA_DADOS / "historico_v7" / "dataset_kenzie360_mensagens.csv"

# ---------------------------------------------------------------- Formato dos CSVs
SEPARADOR = ";"
ENCODING_PANDAS = "utf-8-sig"   # utf-8-sig remove o BOM automaticamente

# ---------------------------------------------------------------- Schemas da BRONZE
# Regra da camada bronze: TUDO em STRING, na ordem exata do CSV.
# Nada de conversao aqui - a bronze e o espelho fiel da origem.

COLUNAS_ATENDIMENTOS = [
    "id_conversa", "id_cliente", "segmento_cliente", "arquetipo",
    "perfil_tecnologico", "faixa_etaria", "idioma", "origem", "data_hora",
    "canal_entrada", "canal_humano", "categoria_assunto", "produto_relacionado",
    "primeira_mensagem_cliente", "sentimento_geral", "resolvido_bot",
    "transferencia_iniciada", "humano_atendeu", "status_conversa", "resolvida",
    "area_encaminhada", "motivo_transferencia", "num_mensagens",
    "num_mensagens_cliente", "duracao_seg", "csat", "qtd_dados_mascarados",
    "transcricao_completa", "contatos_previos", "reabertura",
]

COLUNAS_MENSAGENS = [
    "id_conversa", "id_cliente", "segmento_cliente", "idioma",
    "categoria_assunto", "ordem", "timestamp", "remetente", "texto",
    "sentimento", "tipo_midia", "contem_dado_mascarado",
]

# ---------------------------------------------------------------- Numeros esperados
# Servem de controle: se a carga divergir disso, algo deu errado.
TOTAL_ATENDIMENTOS = 36000
TOTAL_MENSAGENS = 405073 if VERSAO_BASE == "v8" else 404092
