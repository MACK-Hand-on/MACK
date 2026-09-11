# -*- coding: utf-8 -*-
"""E) Fecho: modelo complexo + variaveis novas + interacoes, tudo junto."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~"))
from prof2_base import CAT, NUM, split, prepara
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

df = pd.read_pickle(os.path.expanduser("~/df_hist.pkl"))
tr, te = split(df); y = (~df["res_bot"]).astype(int).values

# interacoes explicitas (o prof pediu "combinar variaveis")
df["ass_x_arq"]  = df["categoria_assunto"]+" | "+df["arquetipo"]
df["ass_x_cont"] = df["categoria_assunto"]+" | "+df["contatos_faixa"]
df["ass_x_reab"] = df["categoria_assunto"]+" | "+df["reabertura"].astype(str)

CATX = CAT+["ant_res_bot_c","mesmo_assunto","ant_area","dias_faixa",
            "ass_x_arq","ass_x_cont","ass_x_reab"]
NUMX = NUM+["sim_caminho","taxa_area_ant","hist_taxa"]

def roda(rot, cat, num, mod):
    X = prepara(df, cat, num)
    pre = ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20,
                                                sparse_output=True),cat),("n","passthrough",num)])
    if isinstance(mod, HistGradientBoostingClassifier):
        pre = ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20,
                                                    sparse_output=False),cat),("n","passthrough",num)])
    p = Pipeline([("p",pre),("m",mod)]).fit(X[tr],y[tr]).predict_proba(X[te])[:,1]
    print(f"  {rot:50s} AUC {roc_auc_score(y[te],p):.4f}")

print("=== TUDO JUNTO: variaveis novas + interacoes + modelos complexos ===")
roda("LR — 13 variaveis (modelo atual)", CAT, NUM, LogisticRegression(max_iter=4000))
roda("LR + interacoes assunto x (arq/contatos/reab)",
     CAT+["ass_x_arq","ass_x_cont","ass_x_reab"], NUM, LogisticRegression(max_iter=4000))
roda("LR + historico + interacoes (23 variaveis)", CATX, NUMX, LogisticRegression(max_iter=5000))
roda("XGBoost + historico + interacoes", CATX, NUMX,
     XGBClassifier(n_estimators=600,max_depth=4,learning_rate=0.03,subsample=0.8,
                   colsample_bytree=0.7,min_child_weight=20,reg_lambda=3.0,
                   eval_metric="auc",random_state=42,n_jobs=-1))
roda("Gradient Boosting + historico + interacoes", CATX, NUMX,
     HistGradientBoostingClassifier(max_iter=300,learning_rate=0.05,random_state=42))
print("\n  TETO TEORICO da base: 0.6736")
