# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 5
Cria na camada gold as duas views do GRAFICO DE MONITORAMENTO
(historico x lote novo).

POR QUE ESTE SCRIPT EXISTE
--------------------------
A Gi precisa de UM grafico com as duas populacoes lado a lado: as 7.712
conversas do historico e as 1.227 do lote novo. O Looker Studio nao junta duas
fontes num grafico so sem "mistura de dados" (blend), que e exatamente onde
erro de join acontece - e pior: o grafico teria que comparar 7.712 com 1.227
em valor absoluto, o que nao diz nada.

Entao a juncao e o percentual sao feitos aqui, em SQL, uma vez. A Gi arrasta
tres campos no Looker e acabou.

O que este script cria:

  1. vw_monitoramento_faixas   VIEW com 6 linhas (3 faixas x 2 origens):
                               origem, faixa, quantas conversas, % da fila
                               daquela origem, e a taxa de resolucao.
                               E a fonte do grafico de barras agrupadas.

  2. vw_monitoramento_delta    VIEW com 3 linhas (uma por faixa): o % no
                               historico, o % no lote novo, e a diferenca em
                               pontos percentuais, ja formatada ("+10,1 pp").
                               E a fonte dos tres indicadores que mostram
                               QUANTO a distribuicao andou.

Pre-requisito: 13_carga_lote_novo_gold.py e 14_cria_gold_painel.py ja rodados
(este script le a vw_painel_modelo e a vw_painel_lote_novo criadas por eles).

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    cd ~/MACK/3_pipeline      # ou a pasta onde estao os outros scripts
    python3 15_cria_vw_monitoramento.py

Pode rodar mais de uma vez sem medo: as views sao recriadas.
"""

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

VIEW_HIST = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_painel_modelo"
VIEW_LOTE = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_painel_lote_novo"

VIEW_FAIXAS = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_monitoramento_faixas"
VIEW_DELTA  = f"{cfg.PROJETO}.{cfg.DS_GOLD}.vw_monitoramento_delta"

# o que os documentos oficiais dizem, para conferir na tela
ESPERADO_HIST = {"Baixo": 26.9, "Medio": 40.2, "Alto": 32.9}   # Numeros_Oficiais_Modelo13
ESPERADO_LOTE = {"Baixo": 21.1, "Medio": 36.0, "Alto": 42.9}   # Carga_Incremental_Lote_Novo
TOLERANCIA = 0.6   # pontos percentuais


SQL_FAIXAS = f"""
CREATE OR REPLACE VIEW `{VIEW_FAIXAS}`
OPTIONS(description="Distribuicao das faixas de risco no historico e no lote novo, em % de cada populacao. Fonte do grafico de monitoramento. Sprint 5.")
AS
WITH base AS (
  -- as duas populacoes empilhadas, com um rotulo que vira a legenda do grafico
  SELECT 'Historico - 7.712 conversas' AS origem, 1 AS origem_ordem,
         faixa_operacional, faixa_ordem, resolveu
  FROM `{VIEW_HIST}`
  UNION ALL
  SELECT 'Lote novo - 1.227, ultima semana', 2,
         faixa_operacional, faixa_ordem, resolveu
  FROM `{VIEW_LOTE}`
)
SELECT
  origem,
  origem_ordem,
  faixa_operacional,
  faixa_ordem,
  COUNT(*) AS conversas,
  -- percentual DENTRO da propria origem: e isto que torna as duas comparaveis,
  -- porque 7.712 e 1.227 nunca poderiam ser comparados em valor absoluto
  COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY origem) AS pct_da_fila,
  AVG(resolveu) AS taxa_resolucao
FROM base
GROUP BY origem, origem_ordem, faixa_operacional, faixa_ordem
"""

SQL_DELTA = f"""
CREATE OR REPLACE VIEW `{VIEW_DELTA}`
OPTIONS(description="Quanto cada faixa andou do historico para o lote novo, em pontos percentuais. Fonte dos indicadores de deriva. Sprint 5.")
AS
WITH h AS (SELECT faixa_operacional, faixa_ordem, pct_da_fila, taxa_resolucao
           FROM `{VIEW_FAIXAS}` WHERE origem_ordem = 1),
     l AS (SELECT faixa_operacional, pct_da_fila, taxa_resolucao
           FROM `{VIEW_FAIXAS}` WHERE origem_ordem = 2)
SELECT
  h.faixa_operacional,
  h.faixa_ordem,
  h.pct_da_fila                      AS pct_historico,
  l.pct_da_fila                      AS pct_lote_novo,
  l.pct_da_fila - h.pct_da_fila      AS delta,
  -- ja formatado para caber dentro de um indicador do Looker
  CONCAT(IF(l.pct_da_fila >= h.pct_da_fila, '+', ''),
         FORMAT('%.1f', (l.pct_da_fila - h.pct_da_fila) * 100),
         ' pp')                      AS delta_rotulo,
  h.taxa_resolucao                   AS resolucao_historico,
  l.taxa_resolucao                   AS resolucao_lote_novo
FROM h JOIN l USING (faixa_operacional)
"""


# ==================================================================== execucao

inicio = time.time()
titulo("KENZIE 360 - views do grafico de monitoramento")

try:
    cliente = bigquery.Client(project=cfg.PROJETO)
except Exception as e:
    erro_fatal("Nao consegui falar com o BigQuery. Rodou o 'gcloud auth "
               "application-default login'?", e)

# ------------------------------------------------- 0. as fontes existem?
passo("Conferindo se as views de origem ja existem")
for v in (VIEW_HIST, VIEW_LOTE):
    try:
        cliente.get_table(v)
        ok(f"{v.split('.')[-1]} encontrada")
    except Exception as e:
        erro_fatal(f"Nao achei {v}. Rode antes o 13_carga_lote_novo_gold.py "
                   f"e o 14_cria_gold_painel.py.", e)

# ------------------------------------------------- 1. cria as views
passo("Criando vw_monitoramento_faixas")
try:
    cliente.query(SQL_FAIXAS, location=cfg.REGIAO).result()
    ok("view criada")
except Exception as e:
    erro_fatal("Falhei ao criar a vw_monitoramento_faixas.", e)

passo("Criando vw_monitoramento_delta")
try:
    cliente.query(SQL_DELTA, location=cfg.REGIAO).result()
    ok("view criada")
except Exception as e:
    erro_fatal("Falhei ao criar a vw_monitoramento_delta.", e)

# ------------------------------------------------- 2. conferencia na tela
passo("Conferindo os numeros contra os documentos oficiais")

sql = f"""SELECT origem_ordem, faixa_operacional, faixa_ordem, conversas,
                 ROUND(100 * pct_da_fila, 1)    AS pct,
                 ROUND(100 * taxa_resolucao, 1) AS resolve
          FROM `{VIEW_FAIXAS}`
          ORDER BY origem_ordem, faixa_ordem"""

linhas = list(cliente.query(sql, location=cfg.REGIAO).result())
if len(linhas) != 6:
    aviso(f"esperava 6 linhas (3 faixas x 2 origens), vieram {len(linhas)}")

print()
print("   origem       faixa    conversas      % da fila   resolve")
print("   " + "-" * 58)
divergencias = []
for l in linhas:
    nome = "historico" if l["origem_ordem"] == 1 else "lote novo"
    esperado = (ESPERADO_HIST if l["origem_ordem"] == 1 else ESPERADO_LOTE)
    alvo = esperado.get(l["faixa_operacional"])
    marca = " "
    if alvo is not None and abs(l["pct"] - alvo) > TOLERANCIA:
        marca = "*"
        divergencias.append((nome, l["faixa_operacional"], l["pct"], alvo))
    print(f"   {nome:11s}  {l['faixa_operacional']:6s}  {l['conversas']:8d}   "
          f"{l['pct']:8.1f}%{marca}  {l['resolve']:6.1f}%")

print()
if divergencias:
    aviso("as linhas com * divergem do documento oficial em mais de "
          f"{TOLERANCIA} ponto:")
    for nome, faixa, veio, alvo in divergencias:
        print(f"        {nome} / {faixa}: BigQuery {veio:.1f}%  x  documento {alvo:.1f}%")
    print("\n        Nao e necessariamente erro - pode ser que o documento tenha")
    print("        sido escrito com uma contagem anterior. Mas ANTES de por no")
    print("        painel, decidam qual dos dois e a verdade e acertem o outro.")
else:
    ok("os seis numeros batem com Numeros_Oficiais_Modelo13.md e "
       "Carga_Incremental_Lote_Novo.md")

passo("O quanto cada faixa andou")
sql2 = f"""SELECT faixa_operacional,
                  ROUND(100 * pct_historico, 1) AS h,
                  ROUND(100 * pct_lote_novo, 1) AS l,
                  delta_rotulo
           FROM `{VIEW_DELTA}` ORDER BY faixa_ordem"""
print()
print("   faixa     historico   lote novo   variacao")
print("   " + "-" * 46)
for l in cliente.query(sql2, location=cfg.REGIAO).result():
    print(f"   {l['faixa_operacional']:8s}  {l['h']:8.1f}%  {l['l']:9.1f}%   "
          f"{l['delta_rotulo']:>8s}")


# ------------------------------------------------- 3. recado para a Gi
titulo("PRONTO - o que a Gi precisa fazer no Looker")
print(f"""
  Duas fontes de dados novas (conector BigQuery, projeto {cfg.PROJETO},
  conjunto {cfg.DS_GOLD}):

    vw_monitoramento_faixas   -> o grafico de barras (historico x lote novo)
    vw_monitoramento_delta    -> os tres indicadores de variacao

  GRAFICO DE BARRAS - "Coluna agrupada"
    Dimensao ................. faixa_operacional
    Dimensao de detalhamento . origem            (vira a legenda, 2 barras)
    Metrica .................. pct_da_fila       agregacao MEDIA, formato %
    Classificar .............. faixa_ordem       crescente
    Desmarcar "Mostrar total" e deixar a legenda embaixo.

  NUNCA use "Contagem de registros" neste grafico: sao 7.712 contra 1.227,
  e as barras do lote novo ficariam invisiveis. O percentual ja vem pronto
  na coluna pct_da_fila.

  MESMO GRAFICO, OUTRA METRICA - troque pct_da_fila por taxa_resolucao e voce
  tem a prova de que o score continua separando no lote que o modelo nunca viu.

  INDICADORES - tres "Scorecards" da vw_monitoramento_delta, um por faixa
  (filtro faixa_operacional = Baixo / Medio / Alto), metrica delta_rotulo.

  ATENCAO: a faixa do meio e "Medio", SEM acento, nas duas views.

  Tempo total: {time.time()-inicio:.0f}s
""")
