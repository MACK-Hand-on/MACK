# -*- coding: utf-8 -*-
"""A fila de correcao de scripts: onde a Kenzie falha, ordenado por quanto custa."""
import warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
df=pd.read_csv("../2_dados/atual_v8/dataset_kenzie360_atendimentos_v8.csv",sep=";",encoding="utf-8-sig",low_memory=False)
# rode antes: python3 09d_tempo_ate_humano.py
tmp=pd.read_csv("tempo_ate_humano.csv",encoding="utf-8-sig")
df=df.merge(tmp[["id_conversa","min_ate_humano"]],on="id_conversa",how="left")
df=df[~df["categoria_assunto"].isin(["Disparo Ativo","Ruido / Nao-atendimento"])]
df["falhou"]=~df["resolvido_bot"].astype(str).str.strip().str.lower().isin(["true","1","sim"])
g=df.groupby("categoria_assunto").agg(
    volume=("id_conversa","size"),
    taxa_falha=("falhou","mean"),
    falhas=("falhou","sum"),
    horas_espera=("min_ate_humano", lambda s: s.sum()/60)).reset_index()
g["taxa_falha"]*=100
g=g.sort_values("horas_espera",ascending=False)
tot=g["horas_espera"].sum()
g["%_do_total"]=g["horas_espera"]/tot*100
g["acum"]=g["%_do_total"].cumsum()
print("FILA DE CORRECAO — base de 6 meses, demandas reais\n")
print(f"{'assunto':<32}{'volume':>8}{'falha%':>8}{'falhas':>8}{'h espera':>10}{'% total':>9}{'acum%':>8}")
print("-"*83)
for _,r in g.iterrows():
    print(f"{r['categoria_assunto'][:30]:<32}{r['volume']:>8,.0f}{r['taxa_falha']:>8.1f}{r['falhas']:>8,.0f}"
          f"{r['horas_espera']:>10,.0f}{r['%_do_total']:>9.1f}{r['acum']:>8.1f}".replace(",","."))
print(f"\ntotal: {tot:,.0f} horas de espera em 6 meses".replace(",","."))
print(f"os 3 primeiros assuntos concentram {g['%_do_total'].head(3).sum():.0f}% de toda a espera")
