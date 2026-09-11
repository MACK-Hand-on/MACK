# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 4
Etapa final do modelo de risco: levar o score para a CAMADA GOLD.

O que este script faz, em ordem:
  1. Confere que o score_risco.csv existe e tem as 7.712 linhas esperadas
  2. Confere que as 10 colunas estao la, com os nomes certos
  3. Cria a tabela kenzie360_gold.tb_score_risco com schema explicito
  4. Carrega o CSV direto do disco (nao passa pelo bucket - e um arquivo pequeno)
  5. Le a tabela de volta e confere a distribuicao das tres faixas

Esta e a tabela que o Looker Studio vai ler para montar a aba de resultados.

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    cd 3_pipeline
    python3 11_carga_score_gold.py

Pode rodar mais de uma vez sem medo: cada execucao substitui a carga anterior.
Se o score_risco.csv nao existir, rode antes:  python3 09_modelo_risco_bot.py
"""

import sys
import time
from pathlib import Path

from google.cloud import bigquery

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


def aviso(texto):
    print(f"   [!]  {texto}")


def erro_fatal(texto, excecao=None):
    print(f"\n   [ERRO] {texto}")
    if excecao:
        print(f"          {type(excecao).__name__}: {str(excecao)[:300]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


# ==================================================================== config

TABELA = "tb_score_risco"
DESTINO = f"{cfg.PROJETO}.{cfg.DS_GOLD}.{TABELA}"

ARQUIVO = Path(__file__).resolve().parent / "score_risco.csv"

LINHAS_ESPERADAS = 7712

# Schema explicito: falha alto se a origem mudar de formato - e isso e bom.
# A ordem TEM que ser a mesma do cabecalho do CSV.
SCHEMA = [
    bigquery.SchemaField("id_conversa",       "STRING",  mode="REQUIRED",
                         description="Identificador da conversa"),
    bigquery.SchemaField("id_cliente",        "STRING",  mode="REQUIRED",
                         description="Identificador do cliente"),
    bigquery.SchemaField("categoria_assunto", "STRING",
                         description="Assunto da conversa (10 categorias)"),
    bigquery.SchemaField("segmento_cliente",  "STRING",
                         description="CDE, Correntista Nacional, etc."),
    bigquery.SchemaField("contatos_faixa",    "STRING",
                         description="Recorrencia em faixas: 0, 1, 2, 3-4, 5-8, 9+"),
    bigquery.SchemaField("reabertura",        "BOOL",
                         description="A conversa e reabertura de um caso anterior"),
    bigquery.SchemaField("risco",             "FLOAT64",
                         description="Probabilidade de a Kenzie NAO resolver (0 a 1)"),
    bigquery.SchemaField("faixa_operacional", "STRING",
                         description="Baixo (<0,65) / Medio (0,65-0,80) / Alto (>0,80)"),
    bigquery.SchemaField("quintil",           "INT64",
                         description="1 a 5, so para o backtest"),
    bigquery.SchemaField("falhou",            "INT64",
                         description="Desfecho real: 1 = a Kenzie nao resolveu"),
]

# Distribuicao oficial, de Numeros_Oficiais_Modelo13.md
ESPERADO = {"Baixo": 2078, "Medio": 3098, "Alto": 2536}


# ==================================================================== inicio

titulo("KENZIE 360 - Score de risco na camada GOLD")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Regiao  : {cfg.REGIAO}")
print(f"  Destino : {DESTINO}")

inicio = time.time()

# ------------------------------------------------- 1. o arquivo de origem
passo("Conferindo o arquivo de origem")

if not ARQUIVO.exists():
    erro_fatal(
        f"Nao encontrei {ARQUIVO.name} em 3_pipeline/.\n"
        "          Rode antes:  python3 09_modelo_risco_bot.py"
    )

with open(ARQUIVO, encoding="utf-8-sig") as f:
    cabecalho = f.readline().strip().split(cfg.SEPARADOR)
    linhas = sum(1 for _ in f)

esperado_cab = [c.name for c in SCHEMA]
if cabecalho != esperado_cab:
    erro_fatal(
        "O cabecalho do CSV nao bate com o schema.\n"
        f"          encontrado : {cabecalho}\n"
        f"          esperado   : {esperado_cab}\n"
        "          Provavel causa: o arquivo foi gravado pelo NOTEBOOK, que usa\n"
        "          menos colunas. O arquivo certo vem do 09_modelo_risco_bot.py."
    )
ok(f"cabecalho com as {len(cabecalho)} colunas certas")

if linhas != LINHAS_ESPERADAS:
    aviso(f"o CSV tem {linhas:,} linhas, esperava {LINHAS_ESPERADAS:,}".replace(",", "."))
    aviso("nao vou parar por isso, mas confira se o 09_ rodou na base v8 inteira")
else:
    ok(f"{linhas:,}".replace(",", ".") + " linhas, exatamente o conjunto de teste")


# ------------------------------------------------- 2. conexao com o BigQuery
passo("Conectando no BigQuery")

try:
    cliente = bigquery.Client(project=cfg.PROJETO)
except Exception as e:
    erro_fatal(
        "Nao consegui autenticar no GCP.\n"
        "          Rode antes:  gcloud auth application-default login", e)
ok(f"autenticado no projeto {cfg.PROJETO}")

# o dataset gold ja existe desde a Sprint 2, mas conferir e barato
try:
    cliente.get_dataset(f"{cfg.PROJETO}.{cfg.DS_GOLD}")
    ok(f"dataset {cfg.DS_GOLD} encontrado")
except Exception as e:
    erro_fatal(f"Nao encontrei o dataset {cfg.DS_GOLD}.", e)


# ------------------------------------------------- 3. a carga
passo(f"Carregando {ARQUIVO.name} em {TABELA}")

config_carga = bigquery.LoadJobConfig(
    schema=SCHEMA,
    source_format=bigquery.SourceFormat.CSV,
    field_delimiter=cfg.SEPARADOR,
    skip_leading_rows=1,        # pula o cabecalho (e o BOM junto com ele)
    encoding="UTF-8",
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)

t0 = time.time()
try:
    with open(ARQUIVO, "rb") as f:
        job = cliente.load_table_from_file(
            f, DESTINO, job_config=config_carga, location=cfg.REGIAO)
    job.result()
except Exception as e:
    erro_fatal("Falhei ao carregar a tabela.", e)

tabela = cliente.get_table(DESTINO)
ok(f"{tabela.num_rows:,} linhas gravadas em {time.time()-t0:.0f}s".replace(",", "."))


# ------------------------------------------------- 4. a conferencia
passo("Conferindo o que chegou na tabela")

sql = f"""
    SELECT
      faixa_operacional,
      COUNT(*)                                   AS conversas,
      ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_da_fila,
      ROUND(100 * (1 - AVG(falhou)), 1)          AS pct_kenzie_resolve,
      ROUND(MIN(risco), 3)                       AS risco_min,
      ROUND(MAX(risco), 3)                       AS risco_max
    FROM `{DESTINO}`
    GROUP BY faixa_operacional
    ORDER BY risco_min
"""
try:
    resultado = list(cliente.query(sql, location=cfg.REGIAO).result())
except Exception as e:
    erro_fatal("A tabela carregou, mas a consulta de conferencia falhou.", e)

print()
print("   faixa    conversas   % da fila   Kenzie resolve   risco")
print("   " + "-" * 58)
tudo_ok = True
for linha in resultado:
    faixa = linha["faixa_operacional"]
    marca = ""
    if faixa in ESPERADO:
        if linha["conversas"] != ESPERADO[faixa]:
            marca = f"  <- esperava {ESPERADO[faixa]}"
            tudo_ok = False
    print(f"   {faixa:7s} {linha['conversas']:9,d} {linha['pct_da_fila']:10.1f}% "
          f"{linha['pct_kenzie_resolve']:14.1f}% "
          f"   {linha['risco_min']:.3f}-{linha['risco_max']:.3f}{marca}"
          .replace(",", "."))

print()
if tudo_ok:
    ok("a distribuicao bate com Numeros_Oficiais_Modelo13.md")
else:
    aviso("a distribuicao NAO bate com os numeros oficiais - avise o grupo antes de usar")


# ------------------------------------------------- 5. o recado para a Gi
titulo("PRONTO - o que a Gi precisa saber")
print(f"""
  Fonte de dados no Looker Studio:
      Conector : BigQuery
      Projeto  : {cfg.PROJETO}
      Conjunto : {cfg.DS_GOLD}
      Tabela   : {TABELA}

  Campos uteis:
      faixa_operacional   Baixo / Medio / Alto   <- SEM acento em "Medio"
      risco               0 a 1, a nota do modelo
      falhou              1 = a Kenzie nao resolveu (para taxa de resolucao use 1 - AVG)
      quintil             1 a 5, para o grafico do backtest
      categoria_assunto   para a fila de correcao

  Tempo total: {time.time()-inicio:.0f}s
""")
