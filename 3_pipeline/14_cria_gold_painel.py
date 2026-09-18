# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 5
Cria na camada gold os dois objetos que faltavam para o painel do modelo.

POR QUE ESTE SCRIPT EXISTE
--------------------------
A tb_score_risco tem a nota e a faixa, mas NAO tem duracao nem abandono - e o
grafico de backtest depende dessas duas colunas justamente porque o modelo nunca
as viu. Elas moram na vw_wide_atendimento. Em vez de pedir para a Gi cruzar duas
fontes dentro do Looker (que e onde erro de join acontece), o cruzamento e feito
aqui, em SQL, uma vez.

O que este script cria:

  1. vw_painel_modelo        VIEW - tb_score_risco cruzada com vw_wide_atendimento
                             por id_conversa. E a fonte UNICA da pagina de
                             resultados: faixa, quintil, nota, desfecho, duracao,
                             abandono e mensagens, na mesma linha.
                             Traz tambem faixa_ordem e quintil_rotulo, para o
                             Looker ordenar sem ninguem precisar configurar nada.

  2. tb_fila_correcao        TABELA - as 10 linhas de fila_correcao.csv: volume,
                             taxa de falha e acumulado por assunto, sobre as
                             31.042 demandas reais. E o grafico de Pareto que
                             vira recomendacao de negocio.

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    python3 14_cria_gold_painel.py

Pode rodar mais de uma vez sem medo.
"""

import csv
import sys
import time
from pathlib import Path

from google.cloud import bigquery

import config_kenzie as cfg


# ==================================================================== apoio

def titulo(t):
    print(); print("=" * 66); print(f"  {t}"); print("=" * 66)

def passo(t): print(f"\n>> {t}")
def ok(t):    print(f"   [OK] {t}")
def aviso(t): print(f"   [!]  {t}")

def erro_fatal(t, e=None):
    print(f"\n   [ERRO] {t}")
    if e: print(f"          {type(e).__name__}: {str(e)[:300]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


# ==================================================================== config

PASTA  = Path(__file__).resolve().parent
CSV_FILA = PASTA / "fila_correcao.csv"

VIEW   = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_painel_modelo"
VIEW_LN = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_painel_lote_novo"
TABELA = f"{cfg.PROJETO}.{cfg.DS_GOLD}.tb_fila_correcao"

SCORE  = f"{cfg.PROJETO}.{cfg.DS_GOLD}.tb_score_risco"
WIDE   = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_wide_atendimento"
LOTE   = f"{cfg.PROJETO}.{cfg.DS_GOLD}.tb_score_lote_novo"

SQL_VIEW = f"""
CREATE OR REPLACE VIEW `{VIEW}`
OPTIONS(description="Fonte unica da pagina de resultados do modelo: score de risco cruzado com duracao e abandono. Sprint 5.")
AS
SELECT
  s.id_conversa,
  s.id_cliente,
  s.categoria_assunto,
  s.segmento_cliente,
  s.contatos_faixa,
  s.reabertura,
  s.risco,
  s.faixa_operacional,
  -- ordem explicita: sem isto o Looker ordena Alto, Baixo, Medio (alfabetico)
  CASE s.faixa_operacional
       WHEN 'Baixo' THEN 1
       WHEN 'Medio' THEN 2
       WHEN 'Alto'  THEN 3
  END                                        AS faixa_ordem,
  s.quintil,
  CONCAT(CAST(s.quintil AS STRING), 'o quintil') AS quintil_rotulo,
  s.falhou,
  -- 1 quando a Kenzie RESOLVEU. A media desta coluna e a taxa de resolucao.
  1 - s.falhou                               AS resolveu,
  -- as duas colunas que o modelo NUNCA viu, e que sustentam o backtest
  w.duracao_min,
  w.fila_abandonada,
  CASE WHEN w.fila_abandonada THEN 1 ELSE 0 END AS abandonou,
  w.num_mensagens
FROM `{SCORE}` s
LEFT JOIN `{WIDE}` w USING (id_conversa)
"""

SQL_VIEW_LN = f"""
CREATE OR REPLACE VIEW `{VIEW_LN}`
OPTIONS(description="Score do lote novo com a mesma ordenacao de faixa da vw_painel_modelo, para a pagina de monitoramento. Sprint 5.")
AS
SELECT
  id_conversa, id_cliente, categoria_assunto, segmento_cliente,
  risco, faixa_operacional,
  CASE faixa_operacional
       WHEN 'Baixo' THEN 1
       WHEN 'Medio' THEN 2
       WHEN 'Alto'  THEN 3
  END              AS faixa_ordem,
  falhou,
  1 - falhou       AS resolveu
FROM `{LOTE}`
"""

# como o fila_correcao.csv esta gravado
CAB_FILA = ["categoria_assunto", "volume", "taxa_falha", "falhas", "% do total", "acumulado"]

SCHEMA_FILA = [
    bigquery.SchemaField("categoria_assunto", "STRING", mode="REQUIRED",
                         description="Assunto da conversa"),
    bigquery.SchemaField("volume",            "INT64",
                         description="Conversas do assunto nas 31.042 demandas reais"),
    bigquery.SchemaField("taxa_falha",        "FLOAT64",
                         description="% de conversas do assunto que a Kenzie NAO resolveu"),
    bigquery.SchemaField("falhas",            "INT64",
                         description="Conversas nao resolvidas do assunto"),
    bigquery.SchemaField("pct_do_total",      "FLOAT64",
                         description="Participacao do assunto no total de falhas"),
    bigquery.SchemaField("acumulado",         "FLOAT64",
                         description="Acumulado de falhas, do assunto de maior volume de falhas para baixo"),
]


# ==================================================================== inicio

titulo("KENZIE 360 - Objetos de gold para o painel do modelo")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  View    : vw_painel_modelo")
print(f"  Tabela  : tb_fila_correcao")

inicio = time.time()

passo("Conectando no BigQuery")
try:
    cliente = bigquery.Client(project=cfg.PROJETO)
except Exception as e:
    erro_fatal("Nao consegui autenticar no GCP.\n"
               "          Rode antes:  gcloud auth application-default login", e)
ok(f"autenticado no projeto {cfg.PROJETO}")

# confere que as duas fontes existem antes de tentar cruzar
passo("Conferindo as fontes")
for nome, ref in [("tb_score_risco", SCORE), ("vw_wide_atendimento", WIDE)]:
    try:
        cliente.get_table(ref); ok(f"{nome} encontrada")
    except Exception as e:
        erro_fatal(f"Nao encontrei {nome} na gold.\n"
                   "          A tb_score_risco vem do 11_carga_score_gold.py.", e)


# ------------------------------------------------- 1. a view
passo("Criando vw_painel_modelo")
try:
    cliente.query(SQL_VIEW, location=cfg.REGIAO).result()
except Exception as e:
    erro_fatal("Falhei ao criar a view.", e)
ok("vw_painel_modelo criada")

# a mesma ordenacao para o lote novo: sem isto o Looker ordena alfabeticamente
# e a pagina de monitoramento sai com Alto na frente de Baixo
try:
    cliente.get_table(LOTE)
    cliente.query(SQL_VIEW_LN, location=cfg.REGIAO).result()
    ok("vw_painel_lote_novo criada")
except Exception as e:
    aviso("nao criei a vw_painel_lote_novo: a tb_score_lote_novo nao existe ainda.")
    aviso("rode antes:  python3 13_carga_lote_novo_gold.py")

passo("Conferindo a view")
sql = f"""
    SELECT
      faixa_operacional, faixa_ordem,
      COUNT(*)                                          AS conversas,
      ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS pct_da_fila,
      ROUND(100 * AVG(resolveu), 1)                     AS pct_resolve,
      ROUND(AVG(duracao_min), 1)                        AS duracao_media,
      ROUND(100 * AVG(abandonou), 1)                    AS pct_abandono
    FROM `{VIEW}`
    GROUP BY faixa_operacional, faixa_ordem
    ORDER BY faixa_ordem
"""
try:
    linhas = list(cliente.query(sql, location=cfg.REGIAO).result())
except Exception as e:
    erro_fatal("A view foi criada, mas a consulta de conferencia falhou.", e)

ESPERADO = {"Baixo": (2078, 47.5), "Medio": (3098, 27.6), "Alto": (2536, 17.1)}
print()
print("   faixa    conversas  % da fila  resolve  duracao  abandono")
print("   " + "-" * 60)
tudo_ok = True
nulos = False
for l in linhas:
    f = l["faixa_operacional"]
    marca = ""
    if f in ESPERADO and l["conversas"] != ESPERADO[f][0]:
        marca = f"  <- esperava {ESPERADO[f][0]}"; tudo_ok = False
    if l["duracao_media"] is None: nulos = True
    print(f"   {f:7s} {l['conversas']:9d} {l['pct_da_fila']:9.1f}% "
          f"{l['pct_resolve']:7.1f}% {str(l['duracao_media']):>8} min "
          f"{l['pct_abandono']:7.1f}%{marca}")
print()
if nulos:
    aviso("duracao veio vazia: o cruzamento por id_conversa nao casou. Avise no chat.")
elif tudo_ok:
    ok("distribuicao e taxas batem com Numeros_Oficiais_Modelo13.md")
else:
    aviso("a distribuicao NAO bate com os numeros oficiais - avise o grupo antes de usar")


# ------------------------------------------------- 1b. conferencia por quintil
# E a tabela do grafico 3. Tem que bater com Numeros_Oficiais_Modelo13.md, e a
# duracao aqui vem da wide (duracao_min), nao do CSV - por isso se confere.
passo("Conferindo o backtest por quintil")

sql_q = f"""
    SELECT
      quintil,
      COUNT(*)                            AS conversas,
      ROUND(100 * AVG(resolveu), 1)       AS pct_resolve,
      ROUND(AVG(duracao_min), 1)          AS duracao_media,
      ROUND(100 * AVG(abandonou), 1)      AS pct_abandono
    FROM `{VIEW}`
    GROUP BY quintil
    ORDER BY quintil
"""
try:
    qs = list(cliente.query(sql_q, location=cfg.REGIAO).result())
except Exception as e:
    erro_fatal("Nao consegui conferir os quintis.", e)

# do 1o ao 5o, conforme a fonte unica da verdade
OFICIAL = {1: 50.7, 2: 33.8, 3: 26.9, 4: 21.0, 5: 15.2}
print()
print("   quintil  conversas  resolve   (oficial)   duracao   abandono")
print("   " + "-" * 62)
divergiu = False
for l in qs:
    q = l["quintil"]
    of = OFICIAL.get(q)
    marca_q = ""
    if of is not None and abs(l["pct_resolve"] - of) > 0.15:
        marca_q = "  <- DIVERGE"; divergiu = True
    print(f"   {q:^7d} {l['conversas']:9d} {l['pct_resolve']:7.1f}% "
          f"{of if of else 0:9.1f}% {l['duracao_media']:8.1f} min "
          f"{l['pct_abandono']:8.1f}%{marca_q}")
print()
if divergiu:
    aviso("a taxa de resolucao por quintil NAO bate com os numeros oficiais.")
else:
    ok("a resolucao por quintil bate com Numeros_Oficiais_Modelo13.md")
print("   Use a coluna duracao/abandono acima como referencia no guia do painel:")
print("   sao estes os valores que o Looker vai mostrar, nao os do CSV.")


# ------------------------------------------------- 2. a tabela de Pareto
passo("Carregando tb_fila_correcao")

if not CSV_FILA.exists():
    aviso(f"nao encontrei {CSV_FILA.name} - pulando a tabela de Pareto.")
    aviso("gere com:  python3 09c_fila_de_correcao.py")
else:
    with open(CSV_FILA, encoding="utf-8-sig", newline="") as f:
        leitor = csv.reader(f, delimiter=cfg.SEPARADOR)
        cab = next(leitor)
        dados = [l for l in leitor if l and l[0].strip()]

    if cab != CAB_FILA:
        erro_fatal("O cabecalho do fila_correcao.csv nao bate com o esperado.\n"
                   f"          encontrado : {cab}\n"
                   f"          esperado   : {CAB_FILA}")

    # "% do total" nao e nome valido de coluna no BigQuery: vira pct_do_total
    tmp = PASTA / "fila_correcao_gold.csv"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=cfg.SEPARADOR)
        w.writerow([c.name for c in SCHEMA_FILA]); w.writerows(dados)

    cfg_carga = bigquery.LoadJobConfig(
        schema=SCHEMA_FILA,
        source_format=bigquery.SourceFormat.CSV,
        field_delimiter=cfg.SEPARADOR,
        skip_leading_rows=1,
        encoding="UTF-8",
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    try:
        with open(tmp, "rb") as f:
            cliente.load_table_from_file(f, TABELA, job_config=cfg_carga,
                                         location=cfg.REGIAO).result()
    except Exception as e:
        erro_fatal("Falhei ao carregar tb_fila_correcao.", e)

    t = cliente.get_table(TABELA)
    ok(f"{t.num_rows} assuntos carregados")
    if t.num_rows != 10:
        aviso(f"esperava 10 assuntos, veio {t.num_rows}")

    sql3 = f"""SELECT categoria_assunto, volume, ROUND(taxa_falha,1) AS taxa_falha,
                      falhas, ROUND(acumulado,1) AS acumulado
               FROM `{TABELA}` ORDER BY falhas DESC LIMIT 3"""
    print()
    print("   os tres assuntos que concentram a falha")
    print("   " + "-" * 58)
    for l in cliente.query(sql3, location=cfg.REGIAO).result():
        print(f"   {l['categoria_assunto']:28s} {l['volume']:5d} conversas  "
              f"falha {l['taxa_falha']:4.1f}%  acumulado {l['acumulado']:4.1f}%")


# ------------------------------------------------- 3. recado
titulo("PRONTO - o que a Gi precisa saber")
print(f"""
  Fontes de dados a criar no Looker Studio (conector BigQuery, projeto
  {cfg.PROJETO}, conjunto {cfg.DS_GOLD}):

    vw_painel_modelo      -> pagina de resultados (graficos 1, 2 e 3)
    tb_fila_correcao      -> grafico 4, o Pareto por assunto
    vw_painel_lote_novo   -> pagina de monitoramento (NAO use a tabela crua:
                             a view traz faixa_ordem e resolveu prontos)

  Na vw_painel_modelo, use:
    faixa_operacional  com ordenacao por faixa_ordem  (1 Baixo, 2 Medio, 3 Alto)
    resolveu           media = taxa de resolucao      (ja e 1 - falhou)
    abandonou          media = taxa de abandono
    duracao_min        media = duracao media
    quintil_rotulo     eixo do backtest, ordenado por quintil

  ATENCAO: a faixa do meio e "Medio", SEM acento, nas tres fontes.

  Tempo total: {time.time()-inicio:.0f}s
""")
