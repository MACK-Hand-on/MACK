# -*- coding: utf-8 -*-
"""O texto acrescenta algo? Testado na configuracao FINAL (demandas reais, alvo = bot nao resolve)."""
import hashlib, warnings
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
CSV="/mnt/user-data/uploads/Projeto Kenzie 360/6_entrega2/7_base_completa/dataset_kenzie360_atendimentos_v8.csv.gz"
df=pd.read_csv(CSV,sep=";",encoding="utf-8-sig",compression="gzip",low_memory=False)
df["data_hora"]=pd.to_datetime(df["data_hora"],errors="coerce")
df["hora"],df["dia_semana"]=df["data_hora"].dt.hour,df["data_hora"].dt.dayofweek
df["txt"]=df["primeira_mensagem_cliente"].fillna("").astype(str)
CAT=["segmento_cliente","arquetipo","perfil_tecnologico","faixa_etaria","idioma","origem","canal_entrada","categoria_assunto","produto_relacionado"]
NUM=["contatos_previos","hora","dia_semana"]
for c in CAT: df[c]=df[c].fillna("(vazio)").astype(str)
for c in NUM: df[c]=pd.to_numeric(df[c],errors="coerce").fillna(-1)
df=df[~df["categoria_assunto"].isin(["Disparo Ativo","Ruido / Nao-atendimento"])].reset_index(drop=True)
y=(~df["resolvido_bot"].astype(str).str.strip().str.lower().isin(["true","1","sim"])).astype(int)
bk=df["id_cliente"].astype(str).map(lambda s:int(hashlib.md5(s.encode()).hexdigest(),16)%100)
tr,te=bk<75,bk>=75
oh=lambda cols: OneHotEncoder(handle_unknown="ignore",min_frequency=20)
tf=lambda: TfidfVectorizer(analyzer="char_wb",ngram_range=(3,5),min_df=3,sublinear_tf=True,max_features=40000)
cfg={"so as colunas (tabular)":ColumnTransformer([("c",oh(CAT),CAT),("n","passthrough",NUM)]),
     "so o texto da 1a mensagem":ColumnTransformer([("t",tf(),"txt")]),
     "colunas + texto":ColumnTransformer([("c",oh(CAT),CAT),("n","passthrough",NUM),("t",tf(),"txt")]),
     "colunas SEM o assunto":ColumnTransformer([("c",oh(CAT),[c for c in CAT if c!="categoria_assunto"]),("n","passthrough",NUM)])}
cols=CAT+NUM+["txt"]
print(f"{'features':<28}{'AUC':>8}")
print("-"*36)
for n,pre in cfg.items():
    m=Pipeline([("p",pre),("m",LogisticRegression(max_iter=3000))]).fit(df.loc[tr,cols],y[tr])
    print(f"{n:<28}{roc_auc_score(y[te],m.predict_proba(df.loc[te,cols])[:,1]):>8.3f}")
