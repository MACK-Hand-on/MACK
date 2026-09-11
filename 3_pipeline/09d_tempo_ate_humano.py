# -*- coding: utf-8 -*-
"""
Tempo que o cliente passa COM A KENZIE antes de falar com um humano.

Nao e a duracao total da conversa (essa inclui o atendimento humano). E o
intervalo entre a primeira mensagem e a primeira fala do atendente. E esse
numero que sustenta a conta de espera evitavel do Caso de Negocio.

COMO RODAR (a partir da pasta 3_pipeline):  python3 09d_tempo_ate_humano.py
SAIDA: tempo_ate_humano.csv  (id_conversa; min_ate_humano)
"""
import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")

M = "../2_dados/atual_v8/dataset_kenzie360_mensagens_v8.csv"
msg = pd.read_csv(M, sep=";", encoding="utf-8-sig", low_memory=False)
msg["timestamp"] = pd.to_datetime(msg["timestamp"], errors="coerce")

inicio = msg.groupby("id_conversa")["timestamp"].min()
hum = msg[msg["remetente"] == "Atendente Humano"].groupby("id_conversa")["timestamp"].min()

t = pd.concat([inicio.rename("t0"), hum.rename("t1")], axis=1).dropna()
t["min_ate_humano"] = (t["t1"] - t["t0"]).dt.total_seconds() / 60
t = t.reset_index()[["id_conversa", "min_ate_humano"]]
t.to_csv("tempo_ate_humano.csv", index=False, encoding="utf-8-sig")

print(f"conversas que chegaram a um humano : {len(t):,}".replace(",", "."))
print(f"tempo medio com a Kenzie antes      : {t['min_ate_humano'].mean():.1f} min")
print(f"mediana                             : {t['min_ate_humano'].median():.1f} min")
print(f"total de espera no semestre          : {t['min_ate_humano'].sum()/60:,.0f} h".replace(",", "."))
print("\nGravado: tempo_ate_humano.csv")
