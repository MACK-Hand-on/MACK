# -*- coding: utf-8 -*-
"""A) Diagnostico da classe 'bot resolve' + varredura de limiar."""
import sys, os, numpy as np
sys.path.insert(0, os.path.expanduser("~"))
from prof2_base import *
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, confusion_matrix, accuracy_score

df = carrega(); tr, te = split(df)
y = (~df["res_bot"]).astype(int).values          # 1 = bot NAO resolve
X = prepara(df, CAT, NUM)
pre = ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20),CAT),
                         ("n","passthrough",NUM)])

def roda(w, rot):
    m = Pipeline([("p",pre),("m",LogisticRegression(max_iter=3000,class_weight=w))]).fit(X[tr],y[tr])
    p = m.predict_proba(X[te])[:,1]; yt = y[te]
    print(f"\n### {rot}   AUC {roc_auc_score(yt,p):.4f}")
    print("  lim | acur | ---- classe RISCO (nao resolve) ---- | ---- classe RESOLVE ----")
    print("      |      |  prec   recall     F1   | prec   recall     F1  | % da fila p/ humano")
    for t in [0.30,0.40,0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85]:
        pred = (p>=t).astype(int)
        cm = confusion_matrix(yt,pred,labels=[0,1])
        vn,fp,fn,vp = cm.ravel()
        pr1 = vp/(vp+fp) if vp+fp else 0; rc1 = vp/(vp+fn) if vp+fn else 0
        f11 = 2*pr1*rc1/(pr1+rc1) if pr1+rc1 else 0
        pr0 = vn/(vn+fn) if vn+fn else 0; rc0 = vn/(vn+fp) if vn+fp else 0
        f10 = 2*pr0*rc0/(pr0+rc0) if pr0+rc0 else 0
        print(f"  {t:.2f} | {accuracy_score(yt,pred)*100:4.1f} | "
              f"{pr1*100:5.1f}% {rc1*100:6.1f}% {f11*100:6.1f}% | "
              f"{pr0*100:5.1f}% {rc0*100:6.1f}% {f10*100:6.1f}% | {pred.mean()*100:5.1f}%")
    return p

print("Base de teste:", int(te.sum()), "conversas | bot resolve em",
      f"{(1-y[te].mean())*100:.1f}%  (classe minoritaria)")
p1 = roda(None, "Regressao logistica (atual)")
p2 = roda("balanced", "Regressao logistica com class_weight=balanced")
