# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2 - Trilha B
Etapa 1 de 3: CAMADA BRONZE (RAW)

O que este script faz, em ordem:
  1. Cria os tres datasets no BigQuery (bronze, silver, gold), se nao existirem
  2. Envia os dois CSVs para o bucket do Cloud Storage
  3. Carrega cada CSV numa tabela de staging (tudo STRING, espelho fiel do arquivo)
  4. Cria a tabela bronze definitiva acrescentando as colunas de rastreabilidade
  5. Apaga a staging e confere as contagens

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    python3 01_carga_bronze.py

Pode rodar mais de uma vez sem medo: cada execucao substitui a carga anterior.
"""

import sys
import time
from datetime import datetime, timezone

from google.cloud import bigquery, storage
from google.api_core import exceptions

import config_kenzie as cfg


# ==================================================================== apoio

def titulo(texto):
    print()
    print("=" * 66)
    print(f"  {texto}")
    print("=" * 66)


def passo(texto):
    print(f"\n>> {texto}")


def ok(texto):
    print(f"   [OK] {texto}")


def erro_fatal(texto, excecao=None):
    print(f"\n   [ERRO] {texto}")
    if excecao:
        print(f"          {type(excecao).__name__}: {str(excecao)[:300]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


def formata_seg(segundos):
    return f"{segundos:.0f}s" if segundos < 60 else f"{segundos/60:.1f}min"


# ==================================================================== inicio

titulo("KENZIE 360 - Camada BRONZE")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Regiao  : {cfg.REGIAO}")
print(f"  Bucket  : gs://{cfg.BUCKET_RAW}")

inicio_geral = time.time()

# Confere se os CSVs existem antes de tocar na nuvem
for arquivo in (cfg.CSV_ATENDIMENTOS, cfg.CSV_MENSAGENS):
    if not arquivo.exists():
        erro_fatal(
            f"Nao encontrei {arquivo.name}. "
            "Rode o script de dentro da pasta do projeto (use o atalho 'kenzie')."
        )

try:
    cliente_bq = bigquery.Client(project=cfg.PROJETO)
    cliente_gcs = storage.Client(project=cfg.PROJETO)
except Exception as e:
    erro_fatal("Nao consegui autenticar no GCP.", e)


# ==================================================================== 1. datasets

passo("1/5  Criando os datasets")

for nome_ds in (cfg.DS_BRONZE, cfg.DS_SILVER, cfg.DS_GOLD):
    ref = bigquery.Dataset(f"{cfg.PROJETO}.{nome_ds}")
    ref.location = cfg.REGIAO
    ref.description = {
        cfg.DS_BRONZE: "RAW - espelho fiel da origem, tudo em STRING, imutavel",
        cfg.DS_SILVER: "TRUSTED - tipado, deduplicado, particionado, PII tratada",
        cfg.DS_GOLD: "CURATED - agregacoes prontas para consumo e dashboard",
    }[nome_ds]
    try:
        cliente_bq.create_dataset(ref)
        ok(f"{nome_ds} criado")
    except exceptions.Conflict:
        ok(f"{nome_ds} ja existia")
    except Exception as e:
        erro_fatal(f"Falhei ao criar o dataset {nome_ds}.", e)


# ==================================================================== 2. upload

passo("2/5  Enviando os CSVs para o Cloud Storage")

carimbo = datetime.now(timezone.utc).strftime("%Y%m%d")
bucket = cliente_gcs.bucket(cfg.BUCKET_RAW)

uris = {}
for tabela, arquivo in (
    ("atendimentos", cfg.CSV_ATENDIMENTOS),
    ("mensagens", cfg.CSV_MENSAGENS),
):
    destino = f"bronze/{carimbo}/{arquivo.name}"
    mb = arquivo.stat().st_size / 1_048_576
    print(f"   enviando {arquivo.name} ({mb:.0f} MB)...", end=" ", flush=True)
    t0 = time.time()
    try:
        blob = bucket.blob(destino)
        blob.upload_from_filename(str(arquivo), timeout=900)
    except Exception as e:
        print()
        erro_fatal(f"Falhei ao enviar {arquivo.name}.", e)
    uris[tabela] = f"gs://{cfg.BUCKET_RAW}/{destino}"
    print(f"pronto em {formata_seg(time.time() - t0)}")

ok(f"os dois arquivos estao em gs://{cfg.BUCKET_RAW}/bronze/{carimbo}/")


# ==================================================================== 3. load

passo("3/5  Carregando na camada bronze")

# Por que schema explicito em vez de autodeteccao:
#   1. O CSV comeca com BOM (marca invisivel do Excel). Com autodeteccao, o BOM
#      grudaria no nome da primeira coluna e viraria "﻿id_conversa".
#   2. Autodeteccao adivinha tipos, e a bronze exige TUDO em STRING por definicao.
#   3. Schema explicito falha alto se a origem mudar de formato - e isso e bom.

def monta_schema(colunas):
    return [bigquery.SchemaField(c, "STRING") for c in colunas]


config_base = dict(
    source_format=bigquery.SourceFormat.CSV,
    field_delimiter=cfg.SEPARADOR,
    skip_leading_rows=1,          # pula o cabecalho (e o BOM junto com ele)
    quote_character='"',          # 4.8 mil linhas tem ";" dentro de texto entre aspas
    allow_quoted_newlines=True,   # protecao extra para quebras de linha em campo
    encoding="UTF-8",
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)

tabelas = {
    "atendimentos": (cfg.COLUNAS_ATENDIMENTOS, cfg.TOTAL_ATENDIMENTOS),
    "mensagens": (cfg.COLUNAS_MENSAGENS, cfg.TOTAL_MENSAGENS),
}

for tabela, (colunas, esperado) in tabelas.items():
    destino_stg = f"{cfg.PROJETO}.{cfg.DS_BRONZE}.{tabela}_stg"
    print(f"   carregando {tabela}...", end=" ", flush=True)
    t0 = time.time()
    try:
        job = cliente_bq.load_table_from_uri(
            uris[tabela],
            destino_stg,
            job_config=bigquery.LoadJobConfig(schema=monta_schema(colunas), **config_base),
            location=cfg.REGIAO,
        )
        job.result()
    except Exception as e:
        print()
        erro_fatal(f"Falhei ao carregar {tabela}.", e)
    print(f"{job.output_rows:,} linhas em {formata_seg(time.time() - t0)}".replace(",", "."))

    if job.output_rows != esperado:
        erro_fatal(
            f"{tabela}: carreguei {job.output_rows} linhas, mas o esperado era {esperado}. "
            "Isso indica CSV truncado ou alterado. Nao siga adiante sem investigar."
        )


# ==================================================================== 4. bronze final

passo("4/5  Acrescentando as colunas de rastreabilidade")

# _ingestion_ts e _source_file respondem "quando este dado entrou e de onde veio".
# Sem isso, a bronze nao consegue provar a origem de um registro - e provar origem
# e metade do trabalho de governanca em ambiente bancario.

for tabela in tabelas:
    sql = f"""
    CREATE OR REPLACE TABLE `{cfg.PROJETO}.{cfg.DS_BRONZE}.{tabela}` AS
    SELECT
      *,
      CURRENT_TIMESTAMP()      AS _ingestion_ts,
      '{uris[tabela]}'         AS _source_file
    FROM `{cfg.PROJETO}.{cfg.DS_BRONZE}.{tabela}_stg`
    """
    try:
        cliente_bq.query(sql, location=cfg.REGIAO).result()
        cliente_bq.query(
            f"DROP TABLE `{cfg.PROJETO}.{cfg.DS_BRONZE}.{tabela}_stg`",
            location=cfg.REGIAO,
        ).result()
        ok(f"{cfg.DS_BRONZE}.{tabela} pronta (staging removida)")
    except Exception as e:
        erro_fatal(f"Falhei ao finalizar a tabela {tabela}.", e)


# ==================================================================== 5. conferencia

passo("5/5  Conferindo o resultado")

sql_check = f"""
SELECT 'atendimentos' AS tabela,
       COUNT(*)                        AS linhas,
       COUNT(DISTINCT id_conversa)     AS conversas_distintas,
       COUNT(DISTINCT id_cliente)      AS clientes_distintos
FROM `{cfg.PROJETO}.{cfg.DS_BRONZE}.atendimentos`
UNION ALL
SELECT 'mensagens',
       COUNT(*),
       COUNT(DISTINCT id_conversa),
       COUNT(DISTINCT id_cliente)
FROM `{cfg.PROJETO}.{cfg.DS_BRONZE}.mensagens`
ORDER BY tabela
"""

try:
    job = cliente_bq.query(sql_check, location=cfg.REGIAO)
    linhas = list(job.result())
except Exception as e:
    erro_fatal("Falhei na consulta de conferencia.", e)

print()
print(f"   {'tabela':<14}{'linhas':>12}{'conversas':>14}{'clientes':>12}")
print("   " + "-" * 52)
for r in linhas:
    print(
        f"   {r.tabela:<14}{r.linhas:>12,}{r.conversas_distintas:>14,}"
        f"{r.clientes_distintos:>12,}".replace(",", ".")
    )

mb_lidos = job.total_bytes_processed / 1_048_576
print(f"\n   Consulta varreu {mb_lidos:.0f} MB "
      f"({mb_lidos/1_048_576*100:.4f}% da franquia mensal de 1 TiB)")

titulo(f"BRONZE CONCLUIDA em {formata_seg(time.time() - inicio_geral)}")
print("""
  Confira no console:
  https://console.cloud.google.com/bigquery?project=kenzie-360-mba

  Proximo passo: python3 02_cria_silver.py
""")
