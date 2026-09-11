# -*- coding: utf-8 -*-
"""B) Modelos mais complexos nas MESMAS 13 variaveis."""
import sys, os, time, numpy as np
sys.path.insert(0, os.path.expanduser("~"))
from prof2_base import *
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, confusion_matrix
from xgboost import XGBClassifier

df = carrega(); tr, te = split(df)
y = (~df["res_bot"]).astype(int).values
X = prepara(df, CAT, NUM)
pre = ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20,sparse_output=False),CAT),
                         ("n","passthrough",NUM)])
yt = y[te]

def avalia(nome, p, t=0.50):
    auc = roc_auc_score(yt,p)
    vn,fp,fn,vp = confusion_matrix(yt,(p>=t).astype(int),labels=[0,1]).ravel()
    pr0 = vn/(vn+fn) if vn+fn else 0
    # melhor F1 da classe RESOLVE varrendo limiar
    melhor=(0,0,0)
    for tt in np.arange(0.20,0.95,0.01):
        a,b,c,d = confusion_matrix(yt,(p>=tt).astype(int),labels=[0,1]).ravel()
        pp = a/(a+c) if a+c else 0; rr = a/(a+b) if a+b else 0
        ff = 2*pp*rr/(pp+rr) if pp+rr else 0
        if ff>melhor[0]: melhor=(ff,tt,pp)
    print(f"{nome:38s} AUC {auc:.4f} | Gini {2*auc-1:.4f} | prec RESOLVE@0,50 {pr0*100:5.1f}% "
          f"| melhor F1 RESOLVE {melhor[0]*100:4.1f}% (lim {melhor[1]:.2f}, prec {melhor[2]*100:.1f}%)")
    return auc

t0=time.time()
mods = [
  ("Gradient Boosting (Hist)",     HistGradientBoostingClassifier(max_iter=300,learning_rate=0.06,random_state=42)),
 ("XGBoost (padrao)",             XGBClassifier(n_estimators=400,max_depth=5,learning_rate=0.05,
                                                subsample=0.8,colsample_bytree=0.8,eval_metric="auc",
                                                random_state=42,n_jobs=-1)),
 ("XGBoost (regularizado)",       XGBClassifier(n_estimators=700,max_depth=4,learning_rate=0.03,
                                                subsample=0.8,colsample_bytree=0.7,min_child_weight=20,
                                                reg_lambda=3.0,eval_metric="auc",random_state=42,n_jobs=-1)),
]
print("=== MESMAS 13 VARIAVEIS, MESMO SPLIT POR CLIENTE ===")
for nome, m in mods:
    p = Pipeline([("p",pre),("m",m)]).fit(X[tr],y[tr]).predict_proba(X[te])[:,1]
    avalia(nome, p)
print(f"\n({time.time()-t0:.0f}s)")
