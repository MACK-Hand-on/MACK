# -*- coding: utf-8 -*-
"""C) Variaveis de historico sugeridas pelo professor.
   Tudo olhando SO para o atendimento ANTERIOR do mesmo cliente (passado)."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~"))
from prof2_base import *
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

df = carrega()
df = df.sort_values(["id_cliente","data_hora"]).reset_index(drop=True)
g = df.groupby("id_cliente", sort=False)

# --- desfecho e caminho do atendimento ANTERIOR ---
df["ant_res_bot"]   = g["res_bot"].shift(1)
df["ant_assunto"]   = g["categoria_assunto"].shift(1)
df["ant_produto"]   = g["produto_relacionado"].shift(1)
df["ant_area"]      = g["area_encaminhada"].shift(1)
df["ant_csat"]      = pd.to_numeric(g["csat"].shift(1), errors="coerce")
df["ant_data"]      = g["data_hora"].shift(1)
df["dias_desde_ult"]= (df["data_hora"]-df["ant_data"]).dt.total_seconds()/86400

# --- "% do caminho igual ao do atendimento anterior" (proxy de menu) ---
mesmo_ass = (df["categoria_assunto"]==df["ant_assunto"]).astype(float)
mesmo_pro = (df["produto_relacionado"]==df["ant_produto"]).astype(float)
df["sim_caminho"] = np.where(df["ant_assunto"].isna(), -1, (mesmo_ass+mesmo_pro)/2)
df["mesmo_assunto"] = np.where(df["ant_assunto"].isna(), "(primeiro)",
                        np.where(mesmo_ass==1,"igual","diferente"))

# --- historico acumulado do cliente ate ANTES desta conversa ---
res_num = df["res_bot"].astype(float)
df["hist_n"]    = g.cumcount()
soma_ant        = g["res_bot"].apply(lambda s: s.astype(float).shift(1).cumsum()).values
df["hist_taxa"] = np.where(df["hist_n"]>0, soma_ant/df["hist_n"].replace(0,np.nan), -1)
df["hist_taxa"] = df["hist_taxa"].fillna(-1)

# --- categoricas em texto ---
df["ant_res_bot_c"] = df["ant_res_bot"].map({True:"resolveu",False:"nao_resolveu"}).fillna("(primeiro)")
df["ant_area"]      = df["ant_area"].fillna("(primeiro)").astype(str)
df["dias_faixa"]    = pd.cut(df["dias_desde_ult"], [-1,0.0417,1,7,30,9999],
                             labels=["<1h","<1d","1-7d","7-30d","30d+"]).astype(str)
df["dias_faixa"]    = df["dias_faixa"].replace("nan","(primeiro)")

tr, te = split(df)
y = (~df["res_bot"]).astype(int).values

# --- taxa de resolucao da AREA do atendimento anterior (proxy "operador"), so com TREINO ---
base = df.loc[tr].groupby("ant_area")["res_bot"].agg(["mean","size"])
media_global = df.loc[tr,"res_bot"].mean()
K = 50   # suavizacao
enc = ((base["mean"]*base["size"] + media_global*K)/(base["size"]+K)).to_dict()
df["taxa_area_ant"] = df["ant_area"].map(enc).fillna(media_global)

pre_f = lambda cat: ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20),cat),
                                       ("n","passthrough",[c for c in TODAS_NUM if c in cat+TODAS_NUM])])

def testa(rot, cat, num):
    X = prepara(df, cat, num)
    pre = ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20),cat),
                             ("n","passthrough",num)])
    m = Pipeline([("p",pre),("m",LogisticRegression(max_iter=4000))]).fit(X[tr],y[tr])
    auc = roc_auc_score(y[te], m.predict_proba(X[te])[:,1])
    print(f"  {rot:52s} AUC {auc:.4f}  ({len(cat)+len(num)} variaveis)")
    return auc

TODAS_NUM = NUM
print("=== VARIAVEIS DE HISTORICO (sugestao do professor) ===")
print(f"  conversas com atendimento anterior: {(df['hist_n']>0).sum()} de {len(df)} "
      f"({(df['hist_n']>0).mean()*100:.1f}%)\n")

a0 = testa("modelo atual (13)", CAT, NUM)
testa("+ desfecho do atendimento anterior",            CAT+["ant_res_bot_c"], NUM)
testa("+ mesmo assunto que o anterior",                CAT+["mesmo_assunto"], NUM)
testa("+ similaridade do caminho (numerica)",          CAT, NUM+["sim_caminho"])
testa("+ area do atendimento anterior",                CAT+["ant_area"], NUM)
testa("+ taxa de resolucao dessa area (target enc.)",  CAT, NUM+["taxa_area_ant"])
testa("+ taxa historica de resolucao do cliente",      CAT, NUM+["hist_taxa"])
testa("+ tempo desde o ultimo atendimento",            CAT+["dias_faixa"], NUM)
print()
aT = testa("TUDO junto",
     CAT+["ant_res_bot_c","mesmo_assunto","ant_area","dias_faixa"],
     NUM+["sim_caminho","taxa_area_ant","hist_taxa"])
print(f"\n  ganho total: {aT-a0:+.4f} de AUC")
df.to_pickle(os.path.expanduser("~/df_hist.pkl"))
