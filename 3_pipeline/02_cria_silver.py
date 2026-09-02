# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2 - Trilha B
Etapa 2 de 3: CAMADA SILVER (TRUSTED)

Le o arquivo sql/02_silver.sql, troca o placeholder do projeto e executa
cada bloco, mostrando o progresso e o custo de cada um.

Como rodar:
    kenzie
    python3 02_cria_silver.py

Pode rodar quantas vezes quiser: os comandos sao CREATE OR REPLACE.
"""

import re
import sys
import time

from google.cloud import bigquery

import config_kenzie as cfg

ARQUIVO_SQL = cfg.PASTA_SQL / "02_silver.sql"


def titulo(texto):
    print()
    print("=" * 66)
    print(f"  {texto}")
    print("=" * 66)


def erro_fatal(texto, excecao=None):
    print(f"\n   [ERRO] {texto}")
    if excecao:
        print(f"          {type(excecao).__name__}: {str(excecao)[:400]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


def formata_seg(s):
    return f"{s:.0f}s" if s < 60 else f"{s/60:.1f}min"


def formata_num(n):
    return f"{n:,}".replace(",", ".")


titulo("KENZIE 360 - Camada SILVER")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Origem  : {cfg.DS_BRONZE}")
print(f"  Destino : {cfg.DS_SILVER}")

if not ARQUIVO_SQL.exists():
    erro_fatal(
        f"Nao encontrei {ARQUIVO_SQL}. "
        "Confira se a pasta 'sql' esta dentro da pasta do projeto."
    )

cliente = bigquery.Client(project=cfg.PROJETO)

# ---------------------------------------------------------------- parse
texto_sql = ARQUIVO_SQL.read_text(encoding="utf-8").replace("@PROJETO", cfg.PROJETO)

# Divide nos marcadores "-- BLOCO: nome" que estejam no inicio da linha
partes = re.split(r"^-- BLOCO:\s*(.+)$", texto_sql, flags=re.MULTILINE)
# partes = [preambulo, nome1, sql1, nome2, sql2, ...]
blocos = [(partes[i].strip(), partes[i + 1].strip()) for i in range(1, len(partes), 2)]

if not blocos:
    erro_fatal("Nao encontrei nenhum bloco no arquivo SQL.")

print(f"\n  {len(blocos)} blocos encontrados: {', '.join(n for n, _ in blocos)}")

# ---------------------------------------------------------------- execucao
inicio_geral = time.time()
total_mb = 0.0

for i, (nome, comando) in enumerate(blocos, start=1):
    print(f"\n>> {i}/{len(blocos)}  criando silver.{nome} ...", end=" ", flush=True)
    t0 = time.time()
    try:
        job = cliente.query(comando, location=cfg.REGIAO)
        job.result()
    except Exception as e:
        print()
        erro_fatal(f"Falhei no bloco '{nome}'.", e)

    mb = (job.total_bytes_processed or 0) / 1_048_576
    total_mb += mb
    print(f"pronto em {formata_seg(time.time() - t0)} (varreu {mb:.0f} MB)")

# ---------------------------------------------------------------- validacao
titulo("VALIDACAO")

sql_valida = f"""
SELECT
  'atendimentos'                                      AS tabela,
  COUNT(*)                                            AS linhas,
  COUNT(DISTINCT id_conversa)                         AS chaves_distintas,
  COUNTIF(data_hora IS NULL)                          AS datas_invalidas,
  COUNTIF(csat IS NOT NULL)                           AS com_csat,
  CAST(MIN(data_ref) AS STRING)                       AS primeira_data,
  CAST(MAX(data_ref) AS STRING)                       AS ultima_data
FROM `{cfg.PROJETO}.{cfg.DS_SILVER}.atendimentos`
UNION ALL
SELECT
  'mensagens',
  COUNT(*),
  COUNT(DISTINCT CONCAT(id_conversa, '-', CAST(ordem AS STRING))),
  COUNTIF(momento IS NULL),
  COUNTIF(sentimento IS NOT NULL),
  CAST(MIN(data_ref) AS STRING),
  CAST(MAX(data_ref) AS STRING)
FROM `{cfg.PROJETO}.{cfg.DS_SILVER}.mensagens`
ORDER BY tabela
"""

try:
    job = cliente.query(sql_valida, location=cfg.REGIAO)
    linhas = list(job.result())
except Exception as e:
    erro_fatal("Falhei na consulta de validacao.", e)

total_mb += (job.total_bytes_processed or 0) / 1_048_576

esperado = {
    "atendimentos": cfg.TOTAL_ATENDIMENTOS,
    "mensagens": cfg.TOTAL_MENSAGENS,
}

problemas = []
for r in linhas:
    print(f"\n   [{r.tabela}]")
    print(f"      linhas ............... {formata_num(r.linhas)}")
    print(f"      chaves distintas ..... {formata_num(r.chaves_distintas)}")
    print(f"      datas invalidas ...... {formata_num(r.datas_invalidas)}")
    print(f"      periodo .............. {r.primeira_data} a {r.ultima_data}")
    rotulo = "com csat" if r.tabela == "atendimentos" else "com sentimento"
    print(f"      {rotulo:<21}{formata_num(r.com_csat)}")

    if r.linhas != esperado[r.tabela]:
        problemas.append(
            f"{r.tabela}: {formata_num(r.linhas)} linhas, esperado {formata_num(esperado[r.tabela])}"
        )
    if r.linhas != r.chaves_distintas:
        problemas.append(
            f"{r.tabela}: ha chaves repetidas ({formata_num(r.linhas - r.chaves_distintas)} duplicatas)"
        )
    if r.datas_invalidas:
        problemas.append(
            f"{r.tabela}: {formata_num(r.datas_invalidas)} datas nao converteram"
        )

print(f"\n   Custo total desta execucao: {total_mb:.0f} MB varridos "
      f"({total_mb/1_048_576*100:.4f}% da franquia mensal)")

if problemas:
    print("\n   [ATENCAO] Pontos que precisam ser investigados:")
    for p in problemas:
        print(f"      - {p}")
    print("\n   Cole esta tela no chat antes de seguir para a gold.\n")
    sys.exit(1)

titulo(f"SILVER CONCLUIDA em {formata_seg(time.time() - inicio_geral)}")
print("""
  Tudo bateu: contagem, unicidade das chaves e conversao de datas.

  Avise no chat que a silver fechou - a gold vem depois da EDA,
  desenhada pelos achados em vez de por palpite.
""")
