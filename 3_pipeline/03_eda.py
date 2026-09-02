# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2 - Trilha A
ANALISE EXPLORATORIA sobre a camada SILVER

Executa as consultas de sql/03_eda.sql e grava cada resultado como CSV
na pasta eda_resultados/. Os arquivos sao pequenos (dezenas de linhas)
e abrem direto no Excel.

Como rodar:
    kenzie
    python3 03_eda.py                    # roda sql/03_eda.sql
    python3 03_eda.py 04_hipotese.sql    # roda outro arquivo da pasta sql/

Nenhuma tabela e criada ou alterada: este script so LE a camada silver.
"""

import re
import sys
import time

from google.cloud import bigquery

import config_kenzie as cfg

# Aceita o nome do arquivo SQL como argumento; sem argumento, usa o padrao.
NOME_SQL = sys.argv[1] if len(sys.argv) > 1 else "03_eda.sql"
ARQUIVO_SQL = cfg.PASTA_SQL / NOME_SQL
PASTA_SAIDA = cfg.PASTA_SAIDA_EDA


def titulo(texto):
    print()
    print("=" * 70)
    print(f"  {texto}")
    print("=" * 70)


def erro_fatal(texto, excecao=None):
    print(f"\n   [ERRO] {texto}")
    if excecao:
        print(f"          {type(excecao).__name__}: {str(excecao)[:400]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


titulo(f"KENZIE 360 - Consultas de {NOME_SQL} (camada silver)")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Origem  : {cfg.DS_SILVER}")
print(f"  Saida   : 5_resultados_eda/")

if not ARQUIVO_SQL.exists():
    erro_fatal(f"Nao encontrei {ARQUIVO_SQL}.")

PASTA_SAIDA.mkdir(exist_ok=True)
cliente = bigquery.Client(project=cfg.PROJETO)

texto_sql = ARQUIVO_SQL.read_text(encoding="utf-8").replace("@PROJETO", cfg.PROJETO)
partes = re.split(r"^-- CONSULTA:\s*(.+)$", texto_sql, flags=re.MULTILINE)
consultas = [(partes[i].strip(), partes[i + 1].strip()) for i in range(1, len(partes), 2)]

if not consultas:
    erro_fatal("Nao encontrei nenhuma consulta no arquivo SQL.")

print(f"\n  {len(consultas)} consultas a executar\n")

inicio = time.time()
total_mb = 0.0
falhas = []

for i, (nome, sql) in enumerate(consultas, start=1):
    print(f"  {i:>2}/{len(consultas)}  {nome:<32}", end=" ", flush=True)
    try:
        job = cliente.query(sql, location=cfg.REGIAO)
        df = job.to_dataframe()
    except Exception as e:
        print("FALHOU")
        falhas.append((nome, f"{type(e).__name__}: {str(e)[:200]}"))
        continue

    mb = (job.total_bytes_processed or 0) / 1_048_576
    total_mb += mb

    destino = PASTA_SAIDA / f"{nome}.csv"
    df.to_csv(destino, index=False, sep=";", encoding="utf-8-sig")
    print(f"{len(df):>4} linhas  ({mb:>5.0f} MB)")

# ------------------------------------------------------------------ resumo
titulo("RESUMO")

print(f"  Consultas executadas : {len(consultas) - len(falhas)} de {len(consultas)}")
print(f"  Tempo total          : {time.time() - inicio:.0f}s")
print(f"  Dados varridos       : {total_mb:.0f} MB "
      f"({total_mb / 1_048_576 * 100:.3f}% da franquia mensal de 1 TiB)")
print(f"  Arquivos gerados em  : 5_resultados_eda/")

if falhas:
    print("\n  [ATENCAO] Consultas que falharam:")
    for nome, msg in falhas:
        print(f"     - {nome}: {msg}")
    print("\n  Cole esta tela no chat.\n")
    sys.exit(1)

# ------------------------------------------------------------------ previa
arquivo_perfil = PASTA_SAIDA / "a1_perfil_base.csv"
if NOME_SQL == "03_eda.sql" and arquivo_perfil.exists():
    import pandas as pd

    df = pd.read_csv(arquivo_perfil, sep=";", encoding="utf-8-sig")
    linha = df.iloc[0]
    print("\n  --- Retrato da base ---")
    for coluna in df.columns:
        print(f"     {coluna:<24} {linha[coluna]}")

print("""
  Os CSVs estao em 5_resultados_eda/ e eu consigo le-los daqui.
  Avise no chat que eu escrevo os achados e monto os graficos.
""")
