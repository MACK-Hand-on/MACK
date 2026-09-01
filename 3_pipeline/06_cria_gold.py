# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2 - Trilha B
Etapa 3 de 3: CAMADA GOLD (CURATED)

Cria as views da gold a partir de sql/05_gold.sql e valida cada uma
consultando algumas linhas.

    kenzie
    python3 06_cria_gold.py

Views, nao tabelas: nao ocupam storage e nunca ficam defasadas.
Pode rodar quantas vezes quiser (CREATE OR REPLACE).
"""

import re
import sys
import time

from google.cloud import bigquery

import config_kenzie as cfg

ARQUIVO_SQL = cfg.PASTA_SQL / "05_gold.sql"


def titulo(t):
    print(); print("=" * 70); print(f"  {t}"); print("=" * 70)


def erro_fatal(t, e=None):
    print(f"\n   [ERRO] {t}")
    if e:
        print(f"          {type(e).__name__}: {str(e)[:400]}")
    print("\n   Cole esta tela no chat.\n")
    sys.exit(1)


titulo("KENZIE 360 - Camada GOLD")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Origem  : {cfg.DS_SILVER}   (base {cfg.VERSAO_BASE})")
print(f"  Destino : {cfg.DS_GOLD}")

if not ARQUIVO_SQL.exists():
    erro_fatal(f"Nao encontrei {ARQUIVO_SQL}.")

cliente = bigquery.Client(project=cfg.PROJETO)

texto = ARQUIVO_SQL.read_text(encoding="utf-8").replace("@PROJETO", cfg.PROJETO)
partes = re.split(r"^-- BLOCO:\s*(.+)$", texto, flags=re.MULTILINE)
blocos = [(partes[i].strip(), partes[i + 1].strip()) for i in range(1, len(partes), 2)]

if not blocos:
    erro_fatal("Nenhum bloco encontrado no SQL.")

print(f"\n  {len(blocos)} views a criar\n")

t0 = time.time()
for i, (nome, sql) in enumerate(blocos, start=1):
    print(f"  {i:>2}/{len(blocos)}  {nome:<34}", end=" ", flush=True)
    try:
        cliente.query(sql, location=cfg.REGIAO).result()
        print("criada")
    except Exception as e:
        print("FALHOU")
        erro_fatal(f"Falhei na view '{nome}'.", e)

# ------------------------------------------------------------------ validacao
titulo("VALIDACAO")
print("  Consultando cada view para confirmar que retorna dados.\n")

total_mb = 0.0
problemas = []
for nome, _ in blocos:
    sql = f"SELECT COUNT(*) AS n FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.{nome}`"
    try:
        job = cliente.query(sql, location=cfg.REGIAO)
        n = list(job.result())[0].n
        mb = (job.total_bytes_processed or 0) / 1_048_576
        total_mb += mb
        marca = "OK" if n > 0 else "!!"
        print(f"   [{marca}] {nome:<34}{n:>9,} linhas   ({mb:>5.0f} MB)".replace(",", "."))
        if n == 0:
            problemas.append(nome)
    except Exception as e:
        print(f"   [!!] {nome:<34} erro ao consultar")
        problemas.append(f"{nome}: {type(e).__name__}")

print(f"\n   Custo da validacao: {total_mb:.0f} MB "
      f"({total_mb/1_048_576*100:.3f}% da franquia mensal)")

if problemas:
    print("\n   [ATENCAO] Views com problema:")
    for p in problemas:
        print(f"      - {p}")
    print()
    sys.exit(1)

# ------------------------------------------------------------------ previa
titulo("PREVIA - a espiral de recorrencia")
sql = f"""
SELECT situacao,
       SUM(conversas)                                              AS conversas,
       ROUND(SUM(conversas*pct_bot_resolve)/SUM(conversas), 1)     AS pct_bot_resolve,
       ROUND(SUM(conversas*pct_negativo)  /SUM(conversas), 1)      AS pct_negativo
FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.vw_espiral_recorrencia`
GROUP BY situacao ORDER BY situacao
"""
try:
    for r in cliente.query(sql, location=cfg.REGIAO).result():
        print(f"   {r.situacao:<38}{r.conversas:>8,}  bot {r.pct_bot_resolve:>5.1f}%  "
              f"negativo {r.pct_negativo:>5.1f}%".replace(",", "."))
except Exception as e:
    print(f"   (previa indisponivel: {type(e).__name__})")

titulo(f"GOLD CONCLUIDA em {time.time()-t0:.0f}s")
print(f"""
  {len(blocos)} views prontas em {cfg.DS_GOLD}.

  No Looker Studio, conecte em:
    Projeto  {cfg.PROJETO}
    Dataset  {cfg.DS_GOLD}

  Comece por vw_kpi_diario (topo do painel) e vw_espiral_recorrencia
  (o achado de maior impacto).
""")
