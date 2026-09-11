# -*- coding: utf-8 -*-
"""Base comum dos experimentos do feedback do professor (Sprint 4)."""
import hashlib, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
CSV = "2_dados/atual_v8/dataset_kenzie360_atendimentos_v8.csv"

def carrega():
    df = pd.read_csv(CSV, sep=";", encoding="utf-8-sig", low_memory=False)
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    df["hora"] = df["data_hora"].dt.hour
    df["dia_semana"] = df["data_hora"].dt.dayofweek
    tv = lambda s: s.astype(str).str.strip().str.lower().isin(["true","1","sim"])
    df["res_bot"] = tv(df["resolvido_bot"])
    df["reabertura"] = df["reabertura"].astype(str).str.strip().str.lower()
    df["contatos_faixa"] = pd.cut(pd.to_numeric(df["contatos_previos"],errors="coerce").fillna(0),
                                  [-1,0,1,2,4,8,999], labels=["0","1","2","3-4","5-8","9+"]).astype(str)
    # populacao: fora disparo ativo e ruido
    df = df[~df["categoria_assunto"].isin(["Disparo Ativo","Ruido / Nao-atendimento"])].reset_index(drop=True)
    return df

CAT = ["segmento_cliente","arquetipo","perfil_tecnologico","faixa_etaria","idioma","origem",
       "canal_entrada","categoria_assunto","produto_relacionado","reabertura","contatos_faixa"]
NUM = ["hora","dia_semana"]

def split(df):
    b = df["id_cliente"].astype(str).map(lambda s:int(hashlib.md5(s.encode()).hexdigest(),16)%100)
    return (b<75).values, (b>=75).values

def prepara(df, cat, num):
    d = df.copy()
    for c in cat: d[c] = d[c].fillna("(vazio)").astype(str)
    for c in num: d[c] = pd.to_numeric(d[c],errors="coerce").fillna(-1)
    return d[cat+num]
