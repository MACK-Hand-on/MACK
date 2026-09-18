# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 5
Traduz o monitoramento em HORAS: quanto de espera evitavel existe no lote novo,
comparado com o historico.

POR QUE ESTE SCRIPT EXISTE
--------------------------
A pagina de monitoramento mostrava so a distribuicao das faixas: "a faixa Alto
subiu 10 pontos". Isso e verdade e nao diz o que custa. Este script responde a
pergunta de negocio: **quantas horas de espera do cliente essa mudanca
representa.**

A conta usa o tempo real de cada conversa, nao uma media aplicada por cima: o
min_ate_humano (intervalo entre a primeira mensagem e a primeira fala do
atendente) ja esta calculado em tempo_ate_humano.csv pelo 09d.

O que este script cria:

  1. tb_tempo_ate_humano      TABELA - as 13.567 conversas do semestre que
                              chegaram a um humano, com o tempo de menu de cada
                              uma. Carregada do tempo_ate_humano.csv.

  2. vw_monitoramento_horas   VIEW com 6 linhas (3 faixas x 2 origens):
                              conversas, quantas chegam ao humano, horas de
                              espera, e - a coluna que importa -
                              horas_por_1000, que torna 7.712 e 1.227
                              comparaveis.

Pre-requisito: 14_cria_gold_painel.py e 15_cria_vw_monitoramento.py rodados.

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    cd "/mnt/c/Users/ilans/Claude/Projects/Projeto Kenzie 360/3_pipeline"
    python3 16_horas_lote_novo.py

Pode rodar mais de uma vez sem medo.
"""

import sys
import time
from pathlib import Path

from google.cloud import bigquery

import config_kenzie as cfg


# ==================================================================== apoio

def titulo(t):
    print(); print("=" * 70); print(f"  {t}"); print("=" * 70)

def passo(t): print(f"\n>> {t}")
def ok(t):    print(f"   [OK] {t}")
def aviso(t): print(f"   [!]  {t}")

def erro_fatal(t, e=None):
    print(f"\n   [ERRO] {t}")
    if e: print(f"          {type(e).__name__}: {str(e)[:300]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


# ==================================================================== config

PASTA = Path(__file__).resolve().parent
CSV_TEMPO = PASTA / "tempo_ate_humano.csv"

TB_TEMPO  = f"{cfg.PROJETO}.{cfg.DS_GOLD}.tb_tempo_ate_humano"
VIEW_HIST = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_painel_modelo"
VIEW_LOTE = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_painel_lote_novo"
VIEW_HORAS = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_monitoramento_horas"

# o que a conferencia local deu em 15/09 - horas por 1.000 conversas da fila
ESPERADO = {(1, "Baixo"): 20, (1, "Medio"): 39, (1, "Alto"): 37,
            (2, "Baixo"): 15, (2, "Medio"): 33, (2, "Alto"): 50}
TOLERANCIA = 2   # horas por 1.000

SCHEMA_TEMPO = [
    bigquery.SchemaField("id_conversa", "STRING", mode="REQUIRED",
                         description="Chave da conversa"),
    bigquery.SchemaField("min_ate_humano", "FLOAT64", mode="REQUIRED",
                         description="Minutos entre a primeira mensagem e a primeira fala do atendente. NAO e a duracao total da conversa."),
]

SQL_HORAS = f"""
CREATE OR REPLACE VIEW `{VIEW_HORAS}`
OPTIONS(description="Espera evitavel em horas por faixa de risco, no historico e no lote novo. A coluna horas_por_1000 e a unica comparavel entre as duas populacoes. Sprint 5.")
AS
WITH base AS (
  SELECT 'Historico - 7.712 conversas' AS origem, 1 AS origem_ordem,
         p.faixa_operacional, p.faixa_ordem, t.min_ate_humano
  FROM `{VIEW_HIST}` p
  LEFT JOIN `{TB_TEMPO}` t USING (id_conversa)
  UNION ALL
  SELECT 'Lote novo - 1.227, ultima semana', 2,
         p.faixa_operacional, p.faixa_ordem, t.min_ate_humano
  FROM `{VIEW_LOTE}` p
  LEFT JOIN `{TB_TEMPO}` t USING (id_conversa)
)
SELECT
  origem,
  origem_ordem,
  faixa_operacional,
  faixa_ordem,
  COUNT(*)                                  AS conversas,
  COUNTIF(min_ate_humano IS NOT NULL)       AS chegam_humano,
  SUM(min_ate_humano) / 60                  AS horas_espera,
  -- a coluna comparavel: 7.712 e 1.227 nunca poderiam ser comparados em horas
  -- absolutas, mas "horas a cada mil conversas que entram na fila" sim
  SUM(min_ate_humano) / 60
      / SUM(COUNT(*)) OVER (PARTITION BY origem) * 1000  AS horas_por_1000,
  AVG(min_ate_humano)                       AS min_medio
FROM base
GROUP BY origem, origem_ordem, faixa_operacional, faixa_ordem
"""


# ==================================================================== execucao

inicio = time.time()
titulo("KENZIE 360 - a deriva traduzida em horas")

try:
    cliente = bigquery.Client(project=cfg.PROJETO)
except Exception as e:
    erro_fatal("Nao consegui falar com o BigQuery. Rodou o 'gcloud auth "
               "application-default login'?", e)

# ------------------------------------------------- 0. pre-requisitos
passo("Conferindo os pre-requisitos")
if not CSV_TEMPO.exists():
    erro_fatal(f"Nao achei {CSV_TEMPO.name} nesta pasta. Rode antes o "
               f"09d_tempo_ate_humano.py.")
ok(f"{CSV_TEMPO.name} encontrado")

for v in (VIEW_HIST, VIEW_LOTE):
    try:
        cliente.get_table(v)
        ok(f"{v.split('.')[-1]} encontrada")
    except Exception as e:
        erro_fatal(f"Nao achei {v}. Rode antes o 14_cria_gold_painel.py.", e)

# ------------------------------------------------- 1. carrega o tempo
passo("Carregando tb_tempo_ate_humano")

# ATENCAO: este CSV e separado por VIRGULA, nao por ponto-e-virgula como os
# outros do projeto. Foi gravado pelo 09d com o padrao do pandas.
cfg_carga = bigquery.LoadJobConfig(
    schema=SCHEMA_TEMPO,
    source_format=bigquery.SourceFormat.CSV,
    field_delimiter=",",
    skip_leading_rows=1,
    encoding="UTF-8",
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)
try:
    with open(CSV_TEMPO, "rb") as f:
        cliente.load_table_from_file(f, TB_TEMPO, job_config=cfg_carga,
                                     location=cfg.REGIAO).result()
except Exception as e:
    erro_fatal("Falhei ao carregar a tb_tempo_ate_humano.", e)

t = cliente.get_table(TB_TEMPO)
ok(f"{t.num_rows} conversas carregadas")
if t.num_rows != 13567:
    aviso(f"esperava 13.567 conversas (as que chegam a um humano no semestre), "
          f"vieram {t.num_rows}")

sql0 = f"""SELECT ROUND(AVG(min_ate_humano),1) AS media,
                  ROUND(SUM(min_ate_humano)/60) AS horas
           FROM `{TB_TEMPO}`"""
l = list(cliente.query(sql0, location=cfg.REGIAO).result())[0]
print(f"        media {l['media']} min por conversa  ·  {int(l['horas'])} h no semestre")
if abs(l["media"] - 13.1) > 0.2 or abs(l["horas"] - 2966) > 20:
    aviso("esperava 13,1 min e 2.966 h - os numeros do Caso de Negocio")

# ------------------------------------------------- 2. cria a view
passo("Criando vw_monitoramento_horas")
try:
    cliente.query(SQL_HORAS, location=cfg.REGIAO).result()
    ok("view criada")
except Exception as e:
    erro_fatal("Falhei ao criar a vw_monitoramento_horas.", e)

# ------------------------------------------------- 3. conferencia
passo("A espera evitavel, faixa a faixa")

sql = f"""SELECT origem_ordem, faixa_operacional, faixa_ordem, conversas,
                 chegam_humano,
                 ROUND(horas_espera)    AS horas,
                 ROUND(horas_por_1000)  AS por_mil,
                 ROUND(min_medio, 1)    AS min_medio
          FROM `{VIEW_HORAS}`
          ORDER BY origem_ordem, faixa_ordem"""

linhas = list(cliente.query(sql, location=cfg.REGIAO).result())
print()
print("   origem       faixa   conversas  chegam ao humano   espera   h/1.000 da fila")
print("   " + "-" * 76)
divergencias = []
for l in linhas:
    nome = "historico" if l["origem_ordem"] == 1 else "lote novo"
    alvo = ESPERADO.get((l["origem_ordem"], l["faixa_operacional"]))
    marca = " "
    if alvo is not None and abs(l["por_mil"] - alvo) > TOLERANCIA:
        marca = "*"
        divergencias.append((nome, l["faixa_operacional"], l["por_mil"], alvo))
    print(f"   {nome:11s}  {l['faixa_operacional']:6s}  {l['conversas']:8d}  "
          f"{l['chegam_humano']:11d} ({100*l['chegam_humano']/l['conversas']:4.1f}%)  "
          f"{l['horas']:6.0f} h  {l['por_mil']:9.0f} h{marca}")

print()
if divergencias:
    aviso("as linhas com * divergem da conferencia local de 15/09:")
    for nome, faixa, veio, alvo in divergencias:
        print(f"        {nome} / {faixa}: BigQuery {veio:.0f} h  x  conferido {alvo} h")
else:
    ok("bate com a conferencia feita em 15/09 sobre os CSVs")

# ------------------------------------------------- 4. a leitura de negocio
passo("A leitura de negocio")

sql2 = f"""
WITH a AS (
  SELECT origem_ordem,
         SUM(horas_por_1000)                                        AS total_mil,
         SUM(IF(faixa_operacional='Alto', horas_por_1000, 0))        AS alto_mil
  FROM `{VIEW_HORAS}` GROUP BY origem_ordem
)
SELECT
  ROUND(MAX(IF(origem_ordem=1, total_mil, NULL)))  AS tot_h,
  ROUND(MAX(IF(origem_ordem=2, total_mil, NULL)))  AS tot_n,
  ROUND(MAX(IF(origem_ordem=1, alto_mil,  NULL)))  AS alto_h,
  ROUND(MAX(IF(origem_ordem=2, alto_mil,  NULL)))  AS alto_n
FROM a
"""
r = list(cliente.query(sql2, location=cfg.REGIAO).result())[0]
th, tn, ah, an = r["tot_h"], r["tot_n"], r["alto_h"], r["alto_n"]
delta = an - ah
pct = 100 * delta / ah if ah else 0

print(f"""
   A cada 1.000 conversas que entram na fila:

   espera total          historico {th:>4.0f} h     lote novo {tn:>4.0f} h
   so na faixa Alto      historico {ah:>4.0f} h     lote novo {an:>4.0f} h   ({delta:+.0f} h, {pct:+.0f}%)

   A espera TOTAL praticamente nao mudou. O que mudou foi ONDE ela esta:
   migrou das faixas Baixo e Medio para a faixa Alto - exatamente o grupo
   que o modelo manda encaminhar primeiro.
""")

titulo("PRONTO - o que por no painel")
print(f"""
  Fonte nova no Looker (BigQuery, {cfg.PROJETO} / {cfg.DS_GOLD}):

    vw_monitoramento_horas

  GRAFICO - "Coluna agrupada", do lado do grafico de distribuicao
    Dimensao ................. faixa_operacional
    Dimensao de detalhamento . origem
    Metrica .................. horas_por_1000    agregacao MEDIA
    Classificar .............. faixa_ordem crescente
    Classificacao secundaria . origem_ordem crescente
    Titulo ................... "A espera evitavel migrou para a faixa Alto"

  INDICADOR - "Indicador", metrica horas_por_1000, filtro faixa_operacional =
  Alto e origem_ordem = 2. E o numero de {an:.0f} h por mil conversas.

  NAO use a coluna horas_espera num grafico que compare as duas origens: 744 h
  contra 120 h nao diz nada, porque as populacoes tem tamanhos diferentes.
  A coluna comparavel e horas_por_1000.

  Tempo total: {time.time()-inicio:.0f}s
""")
