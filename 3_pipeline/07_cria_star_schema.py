# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2
STAR SCHEMA + WIDE TABLE

Cria o modelo dimensional a partir de sql/06_star_schema.sql e valida:
  1. contagem de cada objeto
  2. INTEGRIDADE REFERENCIAL - nenhuma linha da fato pode ficar orfa
  3. uma consulta OLAP de exemplo, para provar que o modelo responde

    kenzie
    python3 07_cria_star_schema.py

Pode rodar quantas vezes quiser (CREATE OR REPLACE).
"""

import re
import sys
import time

from google.cloud import bigquery

import config_kenzie as cfg

ARQUIVO_SQL = cfg.PASTA_SQL / "06_star_schema.sql"

DIMENSOES = [
    ("sk_tempo",    "dim_tempo"),
    ("sk_cliente",  "dim_cliente"),
    ("sk_assunto",  "dim_assunto"),
    ("sk_canal",    "dim_canal"),
    ("sk_desfecho", "dim_desfecho"),
    ("sk_motivo",   "dim_motivo_transferencia"),
]


def titulo(t):
    print(); print("=" * 72); print(f"  {t}"); print("=" * 72)


def erro_fatal(t, e=None):
    print(f"\n   [ERRO] {t}")
    if e:
        print(f"          {type(e).__name__}: {str(e)[:400]}")
    print("\n   Cole esta tela no chat.\n")
    sys.exit(1)


def num(n):
    return f"{n:,}".replace(",", ".")


titulo("KENZIE 360 - Star Schema e Wide Table")
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

print(f"\n  {len(blocos)} objetos a criar (a fato depende das dimensoes: ordem importa)\n")

t0 = time.time()
total_mb = 0.0
for i, (nome, sql) in enumerate(blocos, start=1):
    print(f"  {i}/{len(blocos)}  {nome:<30}", end=" ", flush=True)
    try:
        job = cliente.query(sql, location=cfg.REGIAO)
        job.result()
        total_mb += (job.total_bytes_processed or 0) / 1_048_576
        print("criado")
    except Exception as e:
        print("FALHOU")
        erro_fatal(f"Falhei em '{nome}'.", e)

# ------------------------------------------------------------------ contagens
titulo("1/3  CONTAGENS")

sql_cont = " UNION ALL ".join(
    f"SELECT '{t}' AS objeto, COUNT(*) AS linhas FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.{t}`"
    for _, t in DIMENSOES
) + f" UNION ALL SELECT 'fato_atendimento', COUNT(*) FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.fato_atendimento`"
sql_cont += f" UNION ALL SELECT 'vw_wide_atendimento', COUNT(*) FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.vw_wide_atendimento`"

try:
    job = cliente.query(sql_cont, location=cfg.REGIAO)
    linhas = {r.objeto: r.linhas for r in job.result()}
    total_mb += (job.total_bytes_processed or 0) / 1_048_576
except Exception as e:
    erro_fatal("Falhei nas contagens.", e)

for _, tab in DIMENSOES:
    print(f"   {tab:<30}{num(linhas.get(tab, 0)):>10} linhas")
print(f"   {'fato_atendimento':<30}{num(linhas.get('fato_atendimento', 0)):>10} linhas")
print(f"   {'vw_wide_atendimento':<30}{num(linhas.get('vw_wide_atendimento', 0)):>10} linhas")

problemas = []
if linhas.get("fato_atendimento") != cfg.TOTAL_ATENDIMENTOS:
    problemas.append(f"fato tem {linhas.get('fato_atendimento')} linhas, esperado {cfg.TOTAL_ATENDIMENTOS}")
if linhas.get("vw_wide_atendimento") != linhas.get("fato_atendimento"):
    problemas.append("wide table e fato tem contagens diferentes - algum LEFT JOIN duplicou linhas")

# ------------------------------------------------------------------ integridade
titulo("2/3  INTEGRIDADE REFERENCIAL")
print("   Toda chave da fato precisa existir na dimensao correspondente.\n")

for chave, tab in DIMENSOES:
    sql = f"""
    SELECT COUNT(*) AS orfas
    FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.fato_atendimento` f
    LEFT JOIN `{cfg.PROJETO}.{cfg.DS_GOLD}.{tab}` d
           ON f.{chave} = d.{chave}
    WHERE d.{chave} IS NULL
    """
    try:
        job = cliente.query(sql, location=cfg.REGIAO)
        orfas = list(job.result())[0].orfas
        total_mb += (job.total_bytes_processed or 0) / 1_048_576
    except Exception as e:
        erro_fatal(f"Falhei ao checar {tab}.", e)

    marca = "OK" if orfas == 0 else "!!"
    print(f"   [{marca}] fato -> {tab:<28}{num(orfas):>8} orfas")
    if orfas:
        problemas.append(f"{tab}: {orfas} linhas da fato sem dimensao correspondente")

# ------------------------------------------------------------------ consulta OLAP
titulo("3/3  CONSULTA OLAP DE EXEMPLO")
print("   Autonomia do bot por tipo de demanda e segmento - o corte que\n"
      "   revelou a causa do problema, agora respondido pelo modelo estrela.\n")

sql_olap = f"""
SELECT
  s.tipo_demanda,
  c.segmento_cliente,
  COUNT(*)                                                   AS atendimentos,
  ROUND(100 * COUNTIF(f.resolvido_bot) / COUNT(*), 1)        AS pct_bot_resolve,
  ROUND(SUM(f.min_humano) / 60, 0)                           AS horas_humanas,
  ROUND(AVG(f.csat), 2)                                      AS csat_medio
FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.fato_atendimento` f
JOIN `{cfg.PROJETO}.{cfg.DS_GOLD}.dim_assunto` s USING (sk_assunto)
JOIN `{cfg.PROJETO}.{cfg.DS_GOLD}.dim_cliente` c USING (sk_cliente)
WHERE s.tipo_demanda != 'Nao atendimento'
GROUP BY s.tipo_demanda, c.segmento_cliente
HAVING atendimentos >= 100
ORDER BY s.tipo_demanda, atendimentos DESC
"""

try:
    job = cliente.query(sql_olap, location=cfg.REGIAO)
    resultado = list(job.result())
    total_mb += (job.total_bytes_processed or 0) / 1_048_576
except Exception as e:
    erro_fatal("Falhei na consulta OLAP.", e)

print(f"   {'tipo de demanda':<22}{'segmento':<24}{'atend.':>8}{'bot':>7}{'horas':>8}{'csat':>7}")
print("   " + "-" * 76)
for r in resultado:
    print(f"   {r.tipo_demanda:<22}{r.segmento_cliente:<24}"
          f"{num(r.atendimentos):>8}{r.pct_bot_resolve:>6.1f}%"
          f"{num(int(r.horas_humanas)):>8}{r.csat_medio:>7.2f}")

# ------------------------------------------------------------------ fecho
print(f"\n   Custo total: {total_mb:.0f} MB ({total_mb/1_048_576*100:.3f}% da franquia mensal)")

if problemas:
    titulo("ATENCAO")
    for p in problemas:
        print(f"   - {p}")
    print("\n   Cole esta tela no chat.\n")
    sys.exit(1)

titulo(f"STAR SCHEMA CONCLUIDO em {time.time()-t0:.0f}s")
print(f"""
  Modelo dimensional no ar em {cfg.DS_GOLD}:

    fato_atendimento            grao de um atendimento, particionada por data
    6 dimensoes                 tempo, cliente, assunto, canal, desfecho, motivo
    vw_wide_atendimento         Wide Table - tudo desnormalizado, sem join

  Integridade referencial verificada: nenhuma linha orfa.

  No Looker Studio, a Wide Table e o caminho mais simples (uma fonte, sem
  relacionamentos a configurar). O star schema serve para quem consultar
  em SQL e para demonstrar a modelagem OLAP.
""")
