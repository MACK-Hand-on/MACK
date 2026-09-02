# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2
Snapshot da base v7 no BigQuery, ANTES de promover a v8.

Copia as tabelas atuais de bronze e silver para tabelas com sufixo _v7.
Nada e apagado: a v7 continua consultavel depois da promocao, o que permite
comparar os dois cenarios em SQL e refazer qualquer analise da Sprint 1.

Rode UMA vez, antes de 01_carga_bronze.py:
    kenzie
    python3 04_snapshot_v7.py

Se as tabelas _v7 ja existirem, o script avisa e nao sobrescreve.
"""

import sys

from google.cloud import bigquery
from google.api_core import exceptions

import config_kenzie as cfg

PARES = [
    (cfg.DS_BRONZE, "atendimentos"),
    (cfg.DS_BRONZE, "mensagens"),
    (cfg.DS_SILVER, "atendimentos"),
    (cfg.DS_SILVER, "mensagens"),
]


def titulo(texto):
    print()
    print("=" * 66)
    print(f"  {texto}")
    print("=" * 66)


def erro_fatal(texto, e=None):
    print(f"\n   [ERRO] {texto}")
    if e:
        print(f"          {type(e).__name__}: {str(e)[:300]}")
    print("\n   Cole esta tela no chat.\n")
    sys.exit(1)


titulo("KENZIE 360 - Snapshot da base v7")
print(f"  Projeto : {cfg.PROJETO}")
print("  Guarda a base atual antes de carregar a v8 por cima.")

cliente = bigquery.Client(project=cfg.PROJETO)

# ------------------------------------------------------------------ checagem
existentes = []
for ds, tab in PARES:
    try:
        cliente.get_table(f"{cfg.PROJETO}.{ds}.{tab}_v7")
        existentes.append(f"{ds}.{tab}_v7")
    except exceptions.NotFound:
        pass

if existentes:
    print("\n   [AVISO] Estas tabelas de snapshot JA existem:")
    for x in existentes:
        print(f"      - {x}")
    print("\n   O snapshot ja foi feito antes. Nada a fazer - siga para")
    print("   python3 01_carga_bronze.py\n")
    sys.exit(0)

# ------------------------------------------------------------------ copia
print()
total_linhas = 0
for ds, tab in PARES:
    origem = f"{cfg.PROJETO}.{ds}.{tab}"
    destino = f"{origem}_v7"
    try:
        n = cliente.get_table(origem).num_rows
    except exceptions.NotFound:
        print(f"   [pulado] {ds}.{tab} nao existe ainda")
        continue

    print(f"   copiando {ds}.{tab} ({n:,} linhas)...".replace(",", "."), end=" ", flush=True)
    try:
        job = cliente.copy_table(
            origem, destino,
            job_config=bigquery.CopyJobConfig(write_disposition="WRITE_EMPTY"),
            location=cfg.REGIAO,
        )
        job.result()
    except Exception as e:
        print()
        erro_fatal(f"Falhei ao copiar {ds}.{tab}.", e)
    total_linhas += n
    print("ok")

# ------------------------------------------------------------------ conferencia
print()
for ds, tab in PARES:
    try:
        t = cliente.get_table(f"{cfg.PROJETO}.{ds}.{tab}_v7")
        print(f"   [OK] {ds}.{tab}_v7 -> {t.num_rows:,} linhas".replace(",", "."))
    except exceptions.NotFound:
        print(f"   [--] {ds}.{tab}_v7 nao criada")

titulo("SNAPSHOT CONCLUIDO")
print(f"""
  {total_linhas:,} linhas preservadas.

  A v7 continua consultavel, por exemplo:
    SELECT COUNT(*) FROM `{cfg.PROJETO}.{cfg.DS_SILVER}.atendimentos_v7`

  Proximos passos:
    python3 01_carga_bronze.py     (carrega a v8 por cima da bronze)
    python3 02_cria_silver.py      (recria a silver a partir da v8)
    python3 03_eda.py              (refaz a EDA)
    python3 03_eda.py 04_hipotese.sql
""".replace(",", "."))
