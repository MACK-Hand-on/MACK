# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 4
Publica o SCORE DO LOTE NOVO na camada gold, como tb_score_lote_novo.

Para que serve: o 10_lote_novo.py demonstra a carga incremental - treina so no
historico e pontua a semana seguinte, que o treino nunca viu. Esta tabela leva
esse resultado para o Looker, permitindo uma pagina de MONITORAMENTO ao lado da
pagina de resultados.

  tb_score_risco       7.712 linhas   corte por CLIENTE   -> pagina de resultados
  tb_score_lote_novo   1.227 linhas   corte por TEMPO     -> pagina de monitoramento

O que este script faz, em ordem:
  1. Confere o score_lote_novo.csv gerado pelo 10_lote_novo.py
  2. PADRONIZA os nomes e valores para ficarem iguais aos de tb_score_risco
       faixa         -> faixa_operacional
       desfecho_real -> falhou
       "Médio"       -> "Medio"   (sem acento, como na outra tabela)
     Sem isso a Gi teria que montar dois filtros diferentes para a mesma coisa.
  3. Grava score_lote_novo_gold.csv (a versao padronizada, fica no disco
     para conferencia) e carrega na gold
  4. Le a tabela de volta e confere a distribuicao das tres faixas

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    python3 13_carga_lote_novo_gold.py

Pode rodar mais de uma vez sem medo: cada execucao substitui a carga anterior.
Se o score_lote_novo.csv nao existir, rode antes:  python3 10_lote_novo.py
"""

import csv
import sys
import time
import unicodedata
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


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


# ==================================================================== config

TABELA  = "tb_score_lote_novo"
DESTINO = f"{cfg.PROJETO}.{cfg.DS_GOLD}.{TABELA}"

PASTA       = Path(__file__).resolve().parent
ORIGEM      = PASTA / "score_lote_novo.csv"
PADRONIZADO = PASTA / "score_lote_novo_gold.csv"

LINHAS_ESPERADAS = 1227

# como o 10_lote_novo.py escreve
CABECALHO_ORIGEM = ["id_conversa", "id_cliente", "categoria_assunto",
                    "segmento_cliente", "risco", "faixa", "desfecho_real"]

# como a gold publica - mesmos nomes de tb_score_risco
SCHEMA = [
    bigquery.SchemaField("id_conversa",       "STRING", mode="REQUIRED",
                         description="Identificador da conversa"),
    bigquery.SchemaField("id_cliente",        "STRING", mode="REQUIRED",
                         description="Identificador do cliente"),
    bigquery.SchemaField("categoria_assunto", "STRING",
                         description="Assunto da conversa"),
    bigquery.SchemaField("segmento_cliente",  "STRING",
                         description="CDE, Correntista Nacional, etc."),
    bigquery.SchemaField("risco",             "FLOAT64",
                         description="Probabilidade de a Kenzie NAO resolver (0 a 1)"),
    bigquery.SchemaField("faixa_operacional", "STRING",
                         description="Baixo (<0,65) / Medio (0,65-0,80) / Alto (>0,80)"),
    bigquery.SchemaField("falhou",            "INT64",
                         description="Desfecho real: 1 = a Kenzie nao resolveu"),
]

ESPERADO = {"Baixo": 259, "Medio": 442, "Alto": 526}


# ==================================================================== inicio

titulo("KENZIE 360 - Score do lote novo na camada GOLD")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Destino : {DESTINO}")

inicio = time.time()

# ------------------------------------------------- 1. conferir a origem
passo("Conferindo o arquivo de origem")

if not ORIGEM.exists():
    erro_fatal(
        f"Nao encontrei {ORIGEM.name} em 3_pipeline/.\n"
        "          Rode antes:  python3 10_lote_novo.py"
    )

with open(ORIGEM, encoding="utf-8-sig", newline="") as f:
    leitor = csv.reader(f, delimiter=cfg.SEPARADOR)
    cabecalho = next(leitor)
    linhas = list(leitor)

if cabecalho != CABECALHO_ORIGEM:
    erro_fatal(
        "O cabecalho do CSV nao bate com o que o 10_lote_novo.py escreve.\n"
        f"          encontrado : {cabecalho}\n"
        f"          esperado   : {CABECALHO_ORIGEM}"
    )
ok(f"cabecalho com as {len(cabecalho)} colunas certas")

if len(linhas) != LINHAS_ESPERADAS:
    aviso(f"{len(linhas)} linhas, esperava {LINHAS_ESPERADAS} - confira o recorte de data")
else:
    ok(f"{len(linhas):,}".replace(",", ".") + " linhas, exatamente o lote novo")


# ------------------------------------------------- 2. padronizar
passo("Padronizando para os nomes de tb_score_risco")

i_faixa = CABECALHO_ORIGEM.index("faixa")
trocadas = 0
for linha in linhas:
    limpo = sem_acento(linha[i_faixa])
    if limpo != linha[i_faixa]:
        trocadas += 1
    linha[i_faixa] = limpo

with open(PADRONIZADO, "w", encoding="utf-8-sig", newline="") as f:
    escritor = csv.writer(f, delimiter=cfg.SEPARADOR)
    escritor.writerow([c.name for c in SCHEMA])
    escritor.writerows(linhas)

ok(f"faixa -> faixa_operacional  ·  desfecho_real -> falhou")
ok(f'{trocadas} valores "Médio" viraram "Medio" (sem acento)')
ok(f"gravado {PADRONIZADO.name} para conferencia")


# ------------------------------------------------- 3. carregar
passo("Conectando no BigQuery")

try:
    cliente = bigquery.Client(project=cfg.PROJETO)
except Exception as e:
    erro_fatal(
        "Nao consegui autenticar no GCP.\n"
        "          Rode antes:  gcloud auth application-default login", e)
ok(f"autenticado no projeto {cfg.PROJETO}")

passo(f"Carregando em {TABELA}")

config_carga = bigquery.LoadJobConfig(
    schema=SCHEMA,
    source_format=bigquery.SourceFormat.CSV,
    field_delimiter=cfg.SEPARADOR,
    skip_leading_rows=1,
    encoding="UTF-8",
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)

t0 = time.time()
try:
    with open(PADRONIZADO, "rb") as f:
        job = cliente.load_table_from_file(
            f, DESTINO, job_config=config_carga, location=cfg.REGIAO)
    job.result()
except Exception as e:
    erro_fatal("Falhei ao carregar a tabela.", e)

tabela = cliente.get_table(DESTINO)
ok(f"{tabela.num_rows:,}".replace(",", ".") + f" linhas gravadas em {time.time()-t0:.0f}s")


# ------------------------------------------------- 4. conferir
passo("Conferindo o que chegou na tabela")

sql = f"""
    SELECT
      faixa_operacional,
      COUNT(*)                                          AS conversas,
      ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS pct_da_fila,
      ROUND(100 * (1 - AVG(falhou)), 1)                 AS pct_kenzie_resolve
    FROM `{DESTINO}`
    GROUP BY faixa_operacional
    ORDER BY MIN(risco)
"""
try:
    resultado = list(cliente.query(sql, location=cfg.REGIAO).result())
except Exception as e:
    erro_fatal("A tabela carregou, mas a consulta de conferencia falhou.", e)

print()
print("   faixa    conversas   % da fila   Kenzie resolve")
print("   " + "-" * 48)
tudo_ok = True
for linha in resultado:
    faixa = linha["faixa_operacional"]
    marca = ""
    if faixa in ESPERADO and linha["conversas"] != ESPERADO[faixa]:
        marca = f"  <- esperava {ESPERADO[faixa]}"
        tudo_ok = False
    print(f"   {faixa:7s} {linha['conversas']:9d} {linha['pct_da_fila']:10.1f}% "
          f"{linha['pct_kenzie_resolve']:14.1f}%{marca}")

print()
if tudo_ok:
    ok("a distribuicao bate com Carga_Incremental_Lote_Novo.md")
else:
    aviso("a distribuicao NAO bate com o documentado - avise o grupo antes de usar")


# ------------------------------------------------- 5. recado
titulo("PRONTO - a pagina de monitoramento")
print(f"""
  Fonte de dados no Looker Studio:
      Conector : BigQuery
      Projeto  : {cfg.PROJETO}
      Conjunto : {cfg.DS_GOLD}
      Tabela   : {TABELA}

  Os campos tem os MESMOS nomes de tb_score_risco, de proposito:
  faixa_operacional · risco · falhou · categoria_assunto · segmento_cliente

  O grafico que conta a historia: distribuicao por faixa nas DUAS tabelas,
  lado a lado. Historico 26,6 / 40,5 / 32,8  contra  lote novo 21,1 / 36,0 / 42,9.
  A faixa Alto sobe 10 pontos - e o slide do monitor de deriva.

  Ressalva obrigatoria: uma semana, 1.227 conversas, base sintetica.
  O alarme e ARTEFATO de base finita (a recorrencia so cresce), nao deriva real.

  Tempo total: {time.time()-inicio:.0f}s
""")
