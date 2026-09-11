# -*- coding: utf-8 -*-
"""
MODELO DEFINITIVO — risco de a Kenzie NAO resolver a conversa, medido na abertura.

13 variaveis, com a recorrencia em faixas. E o mesmo modelo do notebook
Kenzie360_Modelo_Risco.ipynb; este script existe para rodar tudo de uma vez e
gravar o arquivo de score que o painel e a camada gold consomem.

COMO RODAR (a partir da pasta 3_pipeline):
    pip install -r ../requirements.txt
    python3 09_modelo_risco_bot.py

SAIDA: score_risco.csv, com uma linha por conversa do conjunto de teste.
"""
import hashlib, warnings
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (roc_auc_score, accuracy_score, confusion_matrix,
                             precision_score, recall_score, f1_score)
warnings.filterwarnings("ignore")

# ---------------------------------------------------------------- 1. os dados
# caminho relativo: funciona na maquina de qualquer pessoa do grupo
CSV = "../2_dados/atual_v8/dataset_kenzie360_atendimentos_v8.csv"
df = pd.read_csv(CSV, sep=";", encoding="utf-8-sig", low_memory=False)

df["data_hora"]  = pd.to_datetime(df["data_hora"], errors="coerce")
df["hora"]       = df["data_hora"].dt.hour
df["dia_semana"] = df["data_hora"].dt.dayofweek

# "true"/"1"/"sim" viram True; qualquer outra coisa vira False
tv = lambda s: s.astype(str).str.strip().str.lower().isin(["true", "1", "sim"])
df["reabertura"] = df["reabertura"].astype(str).str.strip().str.lower()

# a recorrencia entra em FAIXAS, nao como numero cru: a diferenca entre o
# 1o e o 2o contato importa muito mais que entre o 11o e o 12o
df["contatos_faixa"] = pd.cut(
    pd.to_numeric(df["contatos_previos"], errors="coerce").fillna(0),
    [-1, 0, 1, 2, 4, 8, 999],
    labels=["0", "1", "2", "3-4", "5-8", "9+"]).astype(str)

# ------------------------------------------------------------ 2. a populacao
# Disparo Ativo e Ruido nunca geram atendimento: nao ha o que rotear.
# Deixa-los dentro inflava o AUC de 0,665 para 0,703 sem nenhum merito.
antes = len(df)
df = df[~df["categoria_assunto"].isin(["Disparo Ativo", "Ruido / Nao-atendimento"])]
df = df.reset_index(drop=True)

y = (~tv(df["resolvido_bot"])).astype(int).values   # ALVO = a Kenzie NAO resolveu

# --------------------------------------------------------- 3. as 13 variaveis
CAT = ["segmento_cliente", "arquetipo", "perfil_tecnologico", "faixa_etaria",
       "idioma", "origem", "canal_entrada", "categoria_assunto",
       "produto_relacionado", "reabertura", "contatos_faixa"]
NUM = ["hora", "dia_semana"]
for c in CAT: df[c] = df[c].fillna("(vazio)").astype(str)
for c in NUM: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(-1)
X = df[CAT + NUM]

# ------------------------------------------- 4. treino e teste POR CLIENTE
# um cliente inteiro cai de um lado so. Separar por conversa deixaria o mesmo
# cliente nos dois lados e o modelo o reconheceria em vez de generalizar.
bucket = df["id_cliente"].astype(str).map(
    lambda s: int(hashlib.md5(s.encode()).hexdigest(), 16) % 100)
tr, te = (bucket < 75).values, (bucket >= 75).values

print("POPULACAO")
print(f"  demandas reais            : {len(df):,}".replace(",", "."))
print(f"  excluidas (disparo/ruido) : {antes-len(df):,}".replace(",", "."))
print(f"  treino                    : {tr.sum():,} conversas de {df.loc[tr,'id_cliente'].nunique():,} clientes".replace(",", "."))
print(f"  teste                     : {te.sum():,} conversas de {df.loc[te,'id_cliente'].nunique():,} clientes".replace(",", "."))
print(f"  clientes em comum         : {len(set(df.loc[tr,'id_cliente']) & set(df.loc[te,'id_cliente']))}")
print(f"\n  a Kenzie NAO resolve em   : {y[te].mean()*100:.1f}% das conversas de teste")
print(f"  BASELINE (chutar sempre 'nao resolve') : {max(y[te].mean(), 1-y[te].mean())*100:.1f}%")

# ------------------------------------------------------------- 5. o treino
pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", min_frequency=20), CAT),
                         ("n", "passthrough", NUM)])
lr = Pipeline([("p", pre), ("m", LogisticRegression(max_iter=3000))]).fit(X[tr], y[tr])
rf = Pipeline([("p", pre), ("m", RandomForestClassifier(
        n_estimators=300, min_samples_leaf=50, random_state=42, n_jobs=-1))]).fit(X[tr], y[tr])
p   = lr.predict_proba(X[te])[:, 1]
prf = rf.predict_proba(X[te])[:, 1]
yt  = y[te]
auc = roc_auc_score(yt, p)

print("\nRESULTADO")
print(f"  acuracia (limiar 0,50)         : {accuracy_score(yt, (p>=.5).astype(int))*100:.1f}%")
print(f"  AUC      (regressao logistica) : {auc:.4f}")
print(f"  Gini     (2*AUC-1)             : {2*auc-1:.4f}")
print(f"  AUC      (random forest)       : {roc_auc_score(yt, prf):.4f}   <- mais complexo NAO melhora")
print(f"  TETO TEORICO da base           : 0.6736   <- ver prof2_d.py")

vn, fp, fn, vp = confusion_matrix(yt, (p >= .5).astype(int), labels=[0, 1]).ravel()
print(f"\n  matriz em 0,50: VN {vn}  FP {fp}  FN {fn}  VP {vp}")
print(f"  classe RISCO  : precisao {precision_score(yt,p>=.5)*100:.1f}%  recall {recall_score(yt,p>=.5)*100:.1f}%  F1 {f1_score(yt,p>=.5)*100:.1f}%")
print(f"  classe RESOLVE: precisao {vn/(vn+fn)*100:.1f}%  recall {vn/(vn+fp)*100:.1f}%")

# --------------------------------------------- 6. as tres faixas operacionais
# Faixa serve para DIAGNOSTICAR; limiar serve para DECIDIR. Os cortes abaixo
# sao decisao de negocio, tirada da capacidade da operacao — nao da estatistica.
CORTE_BAIXO, CORTE_ALTO = 0.65, 0.80
faixa_op = np.where(p < CORTE_BAIXO, "Baixo",
            np.where(p < CORTE_ALTO, "Medio", "Alto"))

print(f"\nAS TRES FAIXAS OPERACIONAIS  (cortes {CORTE_BAIXO} e {CORTE_ALTO})")
for nome in ["Baixo", "Medio", "Alto"]:
    s = faixa_op == nome
    print(f"  {nome:6s} {s.sum():5d} conversas ({s.mean()*100:4.1f}% da fila)  "
          f"a Kenzie resolve {(1-yt[s].mean())*100:5.1f}%")

# ------------------------------------------------- 7. o backtest por quintil
# a prova de que o score ordena: duracao e abandono NAO sao variaveis do
# modelo, e mesmo assim acompanham a nota.
quintil = pd.qcut(p, 5, labels=[1, 2, 3, 4, 5]).astype(int)
dur = pd.to_numeric(df.loc[te, "duracao_seg"], errors="coerce").values / 60
ab  = (tv(df.loc[te, "transferencia_iniciada"]) & ~tv(df.loc[te, "humano_atendeu"])).values

print("\nBACKTEST — o modelo nunca viu duracao nem abandono")
print("  faixa | resolve | duracao media | abandono")
for q in [1, 2, 3, 4, 5]:
    s = quintil == q
    print(f"    {q}   |  {(1-yt[s].mean())*100:5.1f}% |    {np.nanmean(dur[s]):5.1f} min  |  {ab[s].mean()*100:4.1f}%")

# ---------------------------------------------------------- 8. os coeficientes
nomes = lr.named_steps["p"].get_feature_names_out()
coef  = lr.named_steps["m"].coef_[0]
o = np.argsort(coef)
limpa = lambda n: n.replace("c__", "").replace("n__", "")
print("\nO QUE MAIS AUMENTA O RISCO")
for i in o[::-1][:6]: print(f"   {limpa(nomes[i]):<48}{coef[i]:+.2f}")
print("\nO QUE MAIS DIMINUI")
for i in o[:5]:       print(f"   {limpa(nomes[i]):<48}{coef[i]:+.2f}")

# -------------------------------------------------------------- 9. a saida
saida = pd.DataFrame({
    "id_conversa":       df.loc[te, "id_conversa"].values,
    "id_cliente":        df.loc[te, "id_cliente"].values,
    "categoria_assunto": df.loc[te, "categoria_assunto"].values,
    "segmento_cliente":  df.loc[te, "segmento_cliente"].values,
    "contatos_faixa":    df.loc[te, "contatos_faixa"].values,
    "reabertura":        df.loc[te, "reabertura"].values,
    "risco":             np.round(p, 6),
    "faixa_operacional": faixa_op,     # Baixo / Medio / Alto -> e esta que o painel usa
    "quintil":           quintil,      # 1 a 5 -> so para o backtest
    "falhou":            yt,
})
saida.to_csv("score_risco.csv", sep=";", index=False, encoding="utf-8-sig")
print(f"\nGravado: score_risco.csv  ({len(saida):,} linhas)".replace(",", "."))
print("  Proximo passo (Jonathas): carregar este arquivo na gold como tb_score_risco.")
