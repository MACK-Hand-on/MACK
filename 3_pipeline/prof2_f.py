# -*- coding: utf-8 -*-
"""F) O simulador consegue mostrar a recorrencia funcionando? E exporta coeficientes."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~"))
from prof2_base import *
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

df = carrega(); tr, te = split(df)
y = (~df["res_bot"]).astype(int).values
X = prepara(df, CAT, NUM)
pre = ColumnTransformer([("c",OneHotEncoder(handle_unknown="ignore",min_frequency=20),CAT),
                         ("n","passthrough",NUM)])
pipe = Pipeline([("p",pre),("m",LogisticRegression(max_iter=3000))]).fit(X[tr],y[tr])
print("AUC de conferencia:", round(roc_auc_score(y[te], pipe.predict_proba(X[te])[:,1]),4))

# --- o gradiente de recorrencia que o simulador vai mostrar ---
base = {"segmento_cliente":"CDE","arquetipo":"Expatriado Corporativo","perfil_tecnologico":"Medio",
        "faixa_etaria":"35-44","idioma":"PT","origem":"Receptivo","canal_entrada":"WhatsApp",
        "produto_relacionado":"Conta Corrente","reabertura":"false","contatos_faixa":"0",
        "hora":14,"dia_semana":2}
for k,v in list(base.items()):
    if k in CAT and v not in set(df[k].astype(str)):
        print("  ! valor inexistente:", k, v, "->", sorted(set(df[k].astype(str)))[:6])

print("\n=== O QUE O SIMULADOR MOSTRA: mesmo cliente, mesmo assunto, contatos crescendo ===")
for assunto in ["Bloqueio TED/PIX","Cambio","Saldo e Extrato"]:
    linha=[]
    for faixa in ["0","1","2","3-4","5-8","9+"]:
        r = dict(base, categoria_assunto=assunto, contatos_faixa=faixa)
        p = pipe.predict_proba(pd.DataFrame([r])[CAT+NUM])[0,1]
        linha.append(f"{faixa}:{p:.3f}")
    r = dict(base, categoria_assunto=assunto, contatos_faixa="3-4", reabertura="true")
    pr = pipe.predict_proba(pd.DataFrame([r])[CAT+NUM])[0,1]
    print(f"  {assunto:20s} " + "  ".join(linha) + f"   | 3-4 + reabertura: {pr:.3f}")

# --- exporta coeficientes para o simulador ---
enc = pipe.named_steps["p"].named_transformers_["c"]
nomes = list(enc.get_feature_names_out(CAT)) + NUM
coefs = pipe.named_steps["m"].coef_[0]
out = {"intercepto": float(pipe.named_steps["m"].intercept_[0]),
       "coef": {n: round(float(c),6) for n,c in zip(nomes,coefs)},
       "categorias": {c: sorted(set(df[c].astype(str))) for c in CAT}}
p = os.path.expanduser("~/coef_simulador.json")
json.dump(out, open(p,"w"), ensure_ascii=False)
print(f"\ncoeficientes exportados: {len(coefs)} termos -> {p} ({os.path.getsize(p)/1024:.1f} KB)")
