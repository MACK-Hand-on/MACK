# -*- coding: utf-8 -*-
"""D) O TETO TEORICO da base: qual AUC um modelo PERFEITO alcancaria?
   O gerador sorteia resolvido_bot com probabilidade conhecida:
     p_res = min(p_bot[categoria] * 1.185 * fator_bot, 0.95)
     fator_bot = max(0.45, 1 - 0.07*min(contatos_previos,6) - 0.18*reabertura)
   Ou seja, o desfecho depende SO de: categoria, contatos_previos, reabertura."""
import sys, os, re, numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~"))
from prof2_base import *
from sklearn.metrics import roc_auc_score

GER = "4_gerador_da_base/gerar_dataset_cde_v8.py"
txt = open(GER, encoding="utf-8").read()
PBOT = {m.group(1): float(m.group(2))
        for m in re.finditer(r'^\s*"([^"]+)":\{"peso_cde".*?"p_bot":([\d.]+)', txt, re.M)}
print("p_bot lido do gerador:", len(PBOT), "categorias")
for k,v in sorted(PBOT.items(), key=lambda x:x[1]): print(f"   {k:42s} {v:.2f}")

df = carrega(); tr, te = split(df)
y = (~df["res_bot"]).astype(int).values

cp  = pd.to_numeric(df["contatos_previos"], errors="coerce").fillna(0).clip(upper=6)
rea = df["reabertura"].isin(["true","1","sim","verdadeiro"]).astype(float)
fator = np.maximum(0.45, 1 - 0.07*cp - 0.18*rea)
pres  = np.minimum(df["categoria_assunto"].map(PBOT).fillna(np.nan) * 1.185 * fator, 0.95)
ok    = pres.notna().values
print(f"\nlinhas com categoria mapeada: {ok.sum()} de {len(df)}")

sel = te & ok
p_verdadeiro = (1 - pres[sel]).values      # probabilidade REAL de NAO resolver
teto = roc_auc_score(y[sel], p_verdadeiro)
print("\n" + "="*68)
print(f"  TETO TEORICO da base (modelo onisciente):   AUC {teto:.4f}   Gini {2*teto-1:.4f}")
print(f"  Nosso modelo (regressao logistica, 13 var): AUC 0.6729   Gini 0.3457")
print(f"  Quanto falta para o teto:                   {teto-0.6729:+.4f}")
print("="*68)

# quanto do teto ja capturamos
print(f"\n  aproveitamento do sinal disponivel: {(0.6729-0.5)/(teto-0.5)*100:.1f}%")

# e a precisao maxima da classe RESOLVE, com a probabilidade verdadeira
from sklearn.metrics import confusion_matrix
yt = y[sel]
print("\n  Mesmo com a probabilidade VERDADEIRA, a classe RESOLVE daria:")
melhor=(0,0,0,0)
for t in np.arange(0.20,0.95,0.01):
    vn,fp,fn,vp = confusion_matrix(yt,(p_verdadeiro>=t).astype(int),labels=[0,1]).ravel()
    pr0 = vn/(vn+fn) if vn+fn else 0; rc0 = vn/(vn+fp) if vn+fp else 0
    f10 = 2*pr0*rc0/(pr0+rc0) if pr0+rc0 else 0
    if f10>melhor[0]: melhor=(f10,t,pr0,rc0)
print(f"    melhor F1 possivel: {melhor[0]*100:.1f}%  (limiar {melhor[1]:.2f}, "
      f"precisao {melhor[2]*100:.1f}%, recall {melhor[3]*100:.1f}%)")
print(f"    nosso modelo hoje:  50.0%  (limiar 0,75, precisao 38,5%)")
