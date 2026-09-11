# -*- coding: utf-8 -*-
"""
=============================================================================
 KENZIE 360 - ESTAGIO 1 DO CICLO: CARGA INCREMENTAL, DEMONSTRADA
=============================================================================
 O QUE ESTE SCRIPT FAZ

 Demonstra o ciclo de ponta a ponta sem inventar dado: segura a ultima semana
 da base, treina so com o que veio antes, e trata essa semana como se fosse o
 lote que chegou depois. Pontua o lote novo com o modelo treinado e verifica
 se o desempenho se sustenta.

 E o que responde a pergunta "e quando entrar dado novo, funciona?".

 O QUE ESTE SCRIPT NAO FAZ

 Nao escreve no BigQuery. A carga incremental de verdade exige UMA mudanca no
 01_carga_bronze.py, linha 153:

     write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE   <- hoje
     write_disposition=bigquery.WriteDisposition.WRITE_APPEND     <- incremental

 A silver ja deduplica por chave de negocio com
 ROW_NUMBER() OVER (PARTITION BY chave ORDER BY _ingestion_ts DESC),
 e a gold sao views. Nada mais precisa mudar - por isso a alteracao e de
 uma linha e nao de um pipeline.

 COMO RODAR
     python 10_lote_novo.py
=============================================================================
"""
import hashlib, warnings
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
warnings.filterwarnings("ignore")

CSV          = "../2_dados/atual_v8/dataset_kenzie360_atendimentos_v8.csv"
DIAS_DO_LOTE = 7           # tamanho da "semana que chegou depois"
FORA         = ["Disparo Ativo", "Ruido / Nao-atendimento"]
CORTE_BAIXO, CORTE_ALTO = 0.65, 0.80

CATEGORICAS = ["segmento_cliente","arquetipo","perfil_tecnologico","faixa_etaria",
               "idioma","origem","canal_entrada","categoria_assunto","produto_relacionado",
               "reabertura","contatos_faixa"]
NUMERICAS   = ["hora","dia_semana"]

def preparar(d):
    d = d.copy()
    d["data_hora"]  = pd.to_datetime(d["data_hora"], errors="coerce")
    d["hora"]       = d["data_hora"].dt.hour
    d["dia_semana"] = d["data_hora"].dt.dayofweek
    d["reabertura"] = d["reabertura"].astype(str).str.strip().str.lower()
    d["contatos_faixa"] = pd.cut(
        pd.to_numeric(d["contatos_previos"], errors="coerce").fillna(0),
        [-1,0,1,2,4,8,999], labels=["0","1","2","3-4","5-8","9+"]).astype(str)
    for c in CATEGORICAS: d[c] = d[c].fillna("(vazio)").astype(str)
    for c in NUMERICAS:   d[c] = pd.to_numeric(d[c], errors="coerce").fillna(-1)
    d["y"] = (~d["resolvido_bot"].astype(str).str.strip().str.lower()
                .isin(["true","1","sim"])).astype(int)
    return d

def faixas(nota):
    return np.where(nota < CORTE_BAIXO, "Baixo",
             np.where(nota < CORTE_ALTO, "Médio", "Alto"))

# ---------------------------------------------------------------- 1. o corte
df = preparar(pd.read_csv(CSV, sep=";", encoding="utf-8-sig", low_memory=False))
df = df[~df["categoria_assunto"].isin(FORA)].sort_values("data_hora").reset_index(drop=True)

fim   = df["data_hora"].max()
corte = fim - pd.Timedelta(days=DIAS_DO_LOTE)
hist  = df[df["data_hora"] <  corte].copy()
novo  = df[df["data_hora"] >= corte].copy()

print("="*74)
print("1. O CORTE NO TEMPO")
print(f"   base completa   : {len(df):,} conversas".replace(",","."))
print(f"   historico       : {len(hist):,} conversas  ate {corte:%d/%m/%Y}".replace(",","."))
print(f"   LOTE NOVO       : {len(novo):,} conversas  de {corte:%d/%m} a {fim:%d/%m/%Y}".replace(",","."))
print("   (o lote novo nunca e visto pelo treino - e o que o torna um teste honesto)")

# ------------------------------------------------- 2. treino so com o passado
X_h, y_h = hist[CATEGORICAS + NUMERICAS], hist["y"].values
preparo = ColumnTransformer([
    ("categoricas", OneHotEncoder(handle_unknown="ignore", min_frequency=20), CATEGORICAS),
    ("numericas",   "passthrough", NUMERICAS)])
modelo = Pipeline([("preparo", preparo), ("regressao", LogisticRegression(max_iter=3000))])
modelo.fit(X_h, y_h)

# referencia: desempenho no proprio historico, por cliente (mesma regra do notebook)
balde = hist["id_cliente"].astype(str).map(lambda s: int(hashlib.md5(s.encode()).hexdigest(),16) % 100)
te_h  = (balde >= 75).values
mod_ref = Pipeline([("preparo", preparo), ("regressao", LogisticRegression(max_iter=3000))])
mod_ref.fit(X_h[~te_h], y_h[~te_h])
p_ref = mod_ref.predict_proba(X_h[te_h])[:,1]
auc_ref = roc_auc_score(y_h[te_h], p_ref)
fx_ref = pd.Series(faixas(p_ref)).value_counts(normalize=True) * 100

print("\n" + "="*74)
print("2. REFERENCIA - o que o modelo faz no historico que ele conhece")
print(f"   AUC                 {auc_ref:.4f}")
print(f"   nota mediana        {np.median(p_ref):.3f}")
for f in ["Baixo","Médio","Alto"]:
    print(f"   faixa {f:6s}       {fx_ref.get(f,0):5.1f}% da fila")

# ------------------------------------------------ 3. pontuar o lote que chegou
X_n, y_n = novo[CATEGORICAS + NUMERICAS], novo["y"].values
p_novo = modelo.predict_proba(X_n)[:,1]
auc_novo = roc_auc_score(y_n, p_novo)
fx_novo = pd.Series(faixas(p_novo)).value_counts(normalize=True) * 100

print("\n" + "="*74)
print("3. O LOTE NOVO, PONTUADO")
print(f"   conversas           {len(novo):,}".replace(",","."))
print(f"   AUC                 {auc_novo:.4f}")
print(f"   nota mediana        {np.median(p_novo):.3f}")
print(f"   acuracia            {accuracy_score(y_n,(p_novo>=.5).astype(int))*100:.1f}%")
print(f"   nao resolvido       {y_n.mean()*100:.1f}%")

# --------------------------------------------------- 4. o monitor de deriva
print("\n" + "="*74)
print("4. MONITOR DE DERIVA - o lote novo se parece com o historico?")
print(f"   {'medida':<22}{'referencia':>12}{'lote novo':>12}{'diferenca':>12}")
print("   " + "-"*58)
print(f"   {'AUC':<22}{auc_ref:>12.4f}{auc_novo:>12.4f}{auc_novo-auc_ref:>+12.4f}")
print(f"   {'nota mediana':<22}{np.median(p_ref):>12.3f}{np.median(p_novo):>12.3f}{np.median(p_novo)-np.median(p_ref):>+12.3f}")
for f in ["Baixo","Médio","Alto"]:
    a, b = fx_ref.get(f,0), fx_novo.get(f,0)
    print(f"   {'faixa '+f:<22}{a:>11.1f}%{b:>11.1f}%{b-a:>+11.1f}pp")

alarme = (abs(auc_novo-auc_ref) > 0.05) or any(
    abs(fx_novo.get(f,0)-fx_ref.get(f,0)) > 10 for f in ["Baixo","Médio","Alto"])
print()
if alarme:
    print("   >> ALERTA: o lote novo destoa do historico. Reavaliar o modelo.")
else:
    print("   >> OK: o lote novo se comporta como o historico. O modelo se sustenta.")
print("   (limites: AUC +-0,05 | qualquer faixa +-10 pontos percentuais)")

# ------------------------------------ 4b. quando dispara, o script investiga
if alarme:
    print("\n" + "="*74)
    print("4b. DIAGNOSTICO - deriva real ou artefato?")
    print("   Um alarme so vale se vier com a causa. Os dois suspeitos de sempre:")
    print()
    tv = lambda c: c.astype(str).str.lower().isin(["true","1","sim"])
    print(f"   {'suspeito 1: o cliente mudou':<38}{'historico':>11}{'lote novo':>11}")
    print(f"   {'  contatos anteriores (media)':<38}{hist['contatos_previos'].mean():>11.2f}{novo['contatos_previos'].mean():>11.2f}")
    print(f"   {'  % com 5+ contatos':<38}{(hist['contatos_previos']>=5).mean()*100:>10.1f}%{(novo['contatos_previos']>=5).mean()*100:>10.1f}%")
    print(f"   {'  % reabertura':<38}{tv(hist['reabertura']).mean()*100:>10.1f}%{tv(novo['reabertura']).mean()*100:>10.1f}%")
    print()
    top = hist["categoria_assunto"].value_counts(normalize=True).head(4).index
    print(f"   {'suspeito 2: a demanda mudou':<38}{'historico':>11}{'lote novo':>11}")
    for cat in top:
        a_ = (hist["categoria_assunto"]==cat).mean()*100
        b_ = (novo["categoria_assunto"]==cat).mean()*100
        print(f"   {'  '+cat[:34]:<38}{a_:>10.1f}%{b_:>10.1f}%")
    print()
    print("   A recorrencia media, mes a mes:")
    rec = df.groupby(df["data_hora"].dt.to_period("M"))["contatos_previos"].mean()
    print("     " + "  ".join(f"{str(k)[-2:]}/{v:.1f}" for k,v in rec.items()))
    print()
    print("   LEITURA: numa base sintetica que comeca do zero, o contador de")
    print("   contatos anteriores so cresce - ninguem tem historico em fevereiro.")
    print("   Se o mix de assuntos ficou estavel e so a recorrencia subiu, o alarme")
    print("   e ARTEFATO da base finita, nao deriva de populacao. Em producao o")
    print("   historico do cliente nao comeca no dia 1, entao o efeito nao aparece.")
    print()
    print("   Consequencia pratica: para avaliar um lote novo, a referencia tem")
    print("   que ser um periodo comparavel - nao a base inteira desde o inicio.")

# ------------------------------------------------------ 5. saida operacional
saida = novo[["id_conversa","id_cliente","categoria_assunto","segmento_cliente"]].copy()
saida["risco"] = p_novo.round(4)
saida["faixa"] = faixas(p_novo)
saida["desfecho_real"] = y_n
saida.to_csv("score_lote_novo.csv", index=False, sep=";", encoding="utf-8-sig")
print("\n" + "="*74)
print("5. SAIDA")
print(f"   score_lote_novo.csv - {len(saida):,} linhas".replace(",","."))
print("   e esta tabela que a gold publicaria para o Looker ler.")
print("\n   distribuicao do lote novo por faixa:")
for f in ["Baixo","Médio","Alto"]:
    s = saida["faixa"] == f
    if s.sum():
        print(f"     {f:6s} {s.sum():5d} conversas  -  a Kenzie resolveu {(1-y_n[s.values].mean())*100:.1f}%")
