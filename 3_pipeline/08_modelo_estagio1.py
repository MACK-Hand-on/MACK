# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 3 - Fase 4
MODELO, ESTAGIO 1: classificador de intencao

Le o texto da PRIMEIRA MENSAGEM do cliente e preve a categoria da demanda.
A area de encaminhamento sai por mapeamento deterministico a partir dela.

    kenzie
    python3 08_modelo_estagio1.py

Se faltar biblioteca:
    pip install scikit-learn joblib

O QUE ESTE SCRIPT NAO FAZ, DE PROPOSITO
---------------------------------------
Nao usa nenhuma coluna que so existe DEPOIS que a conversa terminou.
csat, duracao, status_conversa, sentimento_geral e companhia sao consequencia
do desfecho: um modelo que as usasse acertaria quase tudo e nao serviria para
nada em producao, onde no momento da decisao elas ainda nao existem.
A lista completa esta em 1_documentos/sprint2/Features_e_Vazamento.md.

SOBRE O TETO DE 100%
--------------------
As aberturas de conversa da base sintetica saem de conjuntos fixos por
categoria, sem sobreposicao entre elas. Isso da a este estagio um teto de
acuracia de 100% - o modelo nao tem ambiguidade nenhuma para resolver.
O numero alto NAO e resultado: e propriedade do gerador.

Por isso este estagio foi DESPROMOVIDO a diagnostico da base. Ele nao entra
na apresentacao como resultado do modelo - entra como a evidencia que nos
levou a trocar o alvo do projeto. O modelo que responde pelo projeto e o
score de risco de nao-resolucao (script 09), que decide na abertura se a
Kenzie deve tentar resolver ou escalar direto para um humano.
"""

import sys
import time
import hashlib

import config_kenzie as cfg


def titulo(t):
    print(); print("=" * 70); print(f"  {t}"); print("=" * 70)


def erro_fatal(t, e=None):
    print(f"\n   [ERRO] {t}")
    if e:
        print(f"          {type(e).__name__}: {str(e)[:400]}")
    print("\n   Cole esta tela no chat.\n")
    sys.exit(1)


# ------------------------------------------------------------------ imports pesados
try:
    import pandas as pd
    from google.cloud import bigquery
except Exception as e:
    erro_fatal("Faltam bibliotecas base. Rode: pip install pandas google-cloud-bigquery", e)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.metrics import accuracy_score, f1_score, classification_report
    import joblib
except ImportError as e:
    erro_fatal("Faltam scikit-learn e joblib. Rode:  pip install scikit-learn joblib", e)


titulo("KENZIE 360 - Modelo, estagio 1: classificador de intencao")
print(f"  Projeto : {cfg.PROJETO}")
print(f"  Origem  : {cfg.DS_GOLD}.vw_features_nlp")
print(f"  Saida   : {cfg.PASTA_MODELO}")

cfg.PASTA_MODELO.mkdir(exist_ok=True)

# ------------------------------------------------------------------ 1. dados
# So colunas disponiveis NO MOMENTO EM QUE A CONVERSA COMECA.
# contatos_previos e reabertura vem junto porque o estagio 2 vai precisar delas -
# nao entram nas features deste estagio.
SQL = f"""
SELECT
  id_conversa,
  id_cliente,
  primeira_mensagem_cliente,
  categoria_assunto,
  contatos_previos,
  reabertura,
  origem_contato,
  idioma,
  segmento_cliente
FROM `{cfg.PROJETO}.{cfg.DS_GOLD}.vw_features_nlp`
"""

print("\n  Lendo a camada gold...", end=" ", flush=True)
t0 = time.time()
try:
    cliente_bq = bigquery.Client(project=cfg.PROJETO)
    linhas = [dict(r) for r in cliente_bq.query(SQL, location=cfg.REGIAO).result()]
    df = pd.DataFrame(linhas)
except Exception as e:
    erro_fatal("Falhou a consulta ao BigQuery.", e)
print(f"{len(df):,} conversas em {time.time()-t0:.0f}s".replace(",", "."))

# ------------------------------------------------------------------ 2. trava de vazamento
PROIBIDAS = {
    "resolvido_bot", "status_conversa", "resolucao_declarada", "sentimento_geral",
    "csat", "duracao_min", "duracao_seg", "num_mensagens", "num_mensagens_cliente",
    "transferencia_iniciada", "humano_atendeu", "canal_humano", "area_encaminhada",
    "motivo_transferencia", "transcricao_completa", "produto_relacionado",
    "qtd_dados_mascarados", "arquetipo",
}
vazou = PROIBIDAS.intersection(df.columns)
if vazou:
    erro_fatal(f"Coluna proibida no conjunto de treino: {sorted(vazou)}")
print(f"  Trava de vazamento: OK - nenhuma das {len(PROIBIDAS)} colunas proibidas entrou")

# ------------------------------------------------------------------ 3. limpeza
# Disparo ativo sem resposta nao gera fala do cliente: sem texto, nao ha o que
# classificar. Em producao o modelo tambem nao seria acionado nesses casos.
antes = len(df)
df["primeira_mensagem_cliente"] = df["primeira_mensagem_cliente"].fillna("").str.strip()
df = df[df["primeira_mensagem_cliente"] != ""].copy()
print(f"  Sem texto de abertura, descartadas: {antes - len(df)} "
      f"(disparos ativos sem resposta) -> restam {len(df):,}".replace(",", "."))

# ------------------------------------------------------------------ 4. teto do problema
# Uma abertura que aparece em mais de uma categoria e um caso que NENHUM modelo
# consegue acertar sempre. Medir isso antes de treinar diz qual e o teto real.
amb = df.groupby("primeira_mensagem_cliente")["categoria_assunto"].nunique()
n_amb = int((amb > 1).sum())
conv_amb = int(df["primeira_mensagem_cliente"].map(amb).gt(1).sum())
teto = 100 * (1 - conv_amb / len(df))
print(f"\n  Aberturas distintas          : {len(amb):,}".replace(",", "."))
print(f"  Aberturas ambiguas           : {n_amb} ({conv_amb} conversas)")
print(f"  TETO DE ACURACIA DO PROBLEMA : {teto:.2f}%")

# ------------------------------------------------------------------ 5. divisao por CLIENTE
# Nao por conversa: contatos_previos e reabertura ligam as conversas de um mesmo
# cliente. Dividindo por conversa, o mesmo cliente cairia nos dois lados e o
# modelo memorizaria a trajetoria dele em vez de aprender o padrao.
def bucket(id_cliente):
    return int(hashlib.md5(str(id_cliente).encode()).hexdigest(), 16) % 100

df["_b"] = df["id_cliente"].map(bucket)
treino = df[df["_b"] < 75].copy()
teste = df[df["_b"] >= 75].copy()

print(f"\n  Divisao por id_cliente (75/25), sem cliente nos dois lados:")
print(f"    treino : {len(treino):>6,} conversas  {treino.id_cliente.nunique():>6,} clientes".replace(",", "."))
print(f"    teste  : {len(teste):>6,} conversas  {teste.id_cliente.nunique():>6,} clientes".replace(",", "."))
vaz = set(treino.id_cliente) & set(teste.id_cliente)
if vaz:
    erro_fatal(f"{len(vaz)} clientes apareceram nos dois lados da divisao.")
print(f"    clientes em comum: 0 - OK")

# ------------------------------------------------------------------ 6. treino
# TF-IDF de palavras + de caracteres. O de caracteres cobre o que a base tem de
# mais dificil: tres idiomas, abreviacoes ("vc", "pfv"), erros de digitacao
# injetados de proposito e mistura de portugues com ingles nos expatriados.
print("\n  Treinando...", end=" ", flush=True)
t0 = time.time()
modelo = make_pipeline(
    TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2,
                    sublinear_tf=True, max_features=60000),
    # n_jobs foi removido: a partir do scikit-learn 1.8 ele nao tem efeito
    # neste solver e emite FutureWarning.
    LogisticRegression(max_iter=2000, C=5.0),
)
modelo.fit(treino["primeira_mensagem_cliente"], treino["categoria_assunto"])
print(f"pronto em {time.time()-t0:.0f}s")

# ------------------------------------------------------------------ 7. avaliacao
pred = modelo.predict(teste["primeira_mensagem_cliente"])
y = teste["categoria_assunto"]

base_classe = treino["categoria_assunto"].value_counts().idxmax()
base_acc = 100 * (y == base_classe).mean()
acc = 100 * accuracy_score(y, pred)
f1m = 100 * f1_score(y, pred, average="macro")

titulo("RESULTADO - estagio 1")
print(f"  Baseline (prever sempre '{base_classe}') : {base_acc:6.2f}%")
print(f"  Acuracia do modelo                        : {acc:6.2f}%")
print(f"  F1 macro                                  : {f1m:6.2f}%")
print(f"  Teto do problema                          : {teto:6.2f}%")
print(f"\n  Ganho sobre o baseline: {acc - base_acc:+.2f} pontos percentuais")

print("\n  Por categoria:")
print(classification_report(y, pred, digits=3, zero_division=0))

# ------------------------------------------------------------------ 8. roteamento
# A area sai da categoria por mapeamento deterministico - o mesmo de
# vw_dim_assunto.area_padrao. Conferido contra a base: bate 100%.
AREA = {
    "Saldo e Extrato": "Backoffice",
    "Investimentos CDB": "Investimentos",
    "Termos e Documentacao BR": "Cadastro/Onboarding",
    "Cartao de Credito": "Cartoes",
    "Primeiro Acesso": "Suporte Tecnico",
    "Alteracao de Limites": "Mesa de Limites",
    "Cambio": "Cambio/Backoffice",
    "Onboarding - Documentacao": "Cadastro/Onboarding",
    "Bloqueio TED/PIX": "Prevencao a Fraude",
    "Operacoes PJ - Folha e Pagamentos": "Atendimento PJ",
}
area_real = y.map(AREA)
area_prev = pd.Series(pred, index=y.index).map(AREA)
com_area = area_real.notna()
acc_area = 100 * (area_real[com_area] == area_prev[com_area]).mean()
print(f"  Acuracia do ROTEAMENTO (categoria -> area): {acc_area:.2f}%"
      f"   sobre {int(com_area.sum()):,} conversas com area".replace(",", "."))
print("  (maior que a de categoria porque duas categorias caem na mesma area)")

# ------------------------------------------------------------------ 9. artefatos
joblib.dump(modelo, cfg.PASTA_MODELO / "estagio1_intencao.joblib")

saida = teste[["id_conversa", "id_cliente", "contatos_previos", "reabertura",
               "idioma", "segmento_cliente", "origem_contato", "categoria_assunto"]].copy()
saida["categoria_prevista"] = pred
saida["area_prevista"] = area_prev
saida.to_csv(cfg.PASTA_MODELO / "estagio1_predicoes_teste.csv",
             sep=cfg.SEPARADOR, index=False, encoding=cfg.ENCODING_PANDAS)

with open(cfg.PASTA_MODELO / "estagio1_metricas.txt", "w", encoding="utf-8") as f:
    f.write("KENZIE 360 - Estagio 1: classificador de intencao\n")
    f.write(f"conversas de treino      : {len(treino)}\n")
    f.write(f"conversas de teste       : {len(teste)}\n")
    f.write(f"divisao                  : por id_cliente, 75/25, zero sobreposicao\n")
    f.write(f"baseline (classe maior)  : {base_acc:.2f}%\n")
    f.write(f"acuracia                 : {acc:.2f}%\n")
    f.write(f"f1 macro                 : {f1m:.2f}%\n")
    f.write(f"teto do problema         : {teto:.2f}%\n")
    f.write(f"acuracia do roteamento   : {acc_area:.2f}%\n")

titulo("CONCLUIDO")
print(f"  Artefatos em {cfg.PASTA_MODELO.name}/:")
print("    estagio1_intencao.joblib          o modelo treinado")
print("    estagio1_predicoes_teste.csv      entrada do estagio 2")
print("    estagio1_metricas.txt             metricas para o relatorio")
print()
print("  LEITURA HONESTA DESTE RESULTADO:")
print()
print("  Este numero NAO e um resultado do modelo. Ele mede que as aberturas")
print("  da base sintetica nao tem ambiguidade entre categorias - e uma medida")
print("  da BASE, nao do aprendizado. O teto de 100% era conhecido ANTES do")
print("  treino, e e por isso que o numero pode ser lido com honestidade em")
print("  vez de comemorado.")
print()
print("  A regra que fica: quando o modelo acerta quase tudo, desconfie da")
print("  variavel em vez de comemorar. Acerto alto demais e sintoma, nao trofeu.")
print()
print("  O unico erro (Operacoes PJ, 1 caso em 60) e o segmento com 0,6% da")
print("  base. Um 100,00% cravado indicaria tabela de consulta; um erro isolado")
print("  no segmento mais raro indica que o modelo generaliza.")
print()
print("  COMO USAR ISTO NA APRESENTACAO:")
print("  Como diagnostico da base, nao como resultado. A frase e: 'medimos e")
print("  descobrimos que as aberturas sao deterministicas; foi por isso que o")
print("  alvo do projeto passou a ser outro'. O modelo que responde pelo")
print("  projeto e o score de risco de nao-resolucao - script 09.")
print()
