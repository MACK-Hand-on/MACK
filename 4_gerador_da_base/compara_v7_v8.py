# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2
Comparador v7 x v8 do gemeo estatistico.

Roda localmente (sem BigQuery) e mostra lado a lado o que mudou.
Use para decidir se a v8 deve substituir a v7 como base oficial.

    python3 compara_v7_v8.py
"""
import pandas as pd
from pathlib import Path

DADOS = Path(__file__).resolve().parent.parent / "2_dados"
LER = dict(sep=";", encoding="utf-8-sig")

pares = [("v7", DADOS / "historico_v7" / "dataset_kenzie360_atendimentos.csv"),
         ("v8", DADOS / "atual_v8"     / "dataset_kenzie360_atendimentos_v8.csv")]
faltando = [str(f) for _, f in pares if not f.exists()]
if faltando:
    raise SystemExit("Nao encontrei:\n  " + "\n  ".join(faltando))

d = {v: pd.read_csv(f, **LER) for v, f in pares}
for v in d:
    d[v]["_dt"] = pd.to_datetime(d[v]["data_hora"])

def linha(rot, f, fmt="{:.1f}", nota=""):
    a, b = f(d["v7"]), f(d["v8"])
    print(f"  {rot:<40} {fmt.format(a):>9} {fmt.format(b):>9}   {nota}")

print("=" * 78)
print("  KENZIE 360 - COMPARACAO v7 x v8")
print("=" * 78)
print(f"\n  {'indicador':<40} {'v7':>9} {'v8':>9}")
print("  " + "-" * 62)

print("\n  [ESTRUTURA - deve ficar igual]")
linha("conversas", lambda x: len(x), "{:.0f}")
linha("clientes distintos", lambda x: x.id_cliente.nunique(), "{:.0f}")
linha("colunas", lambda x: x.shape[1], "{:.0f}")
linha("clientes recorrentes (%)", lambda x: 100*(x.groupby('id_cliente').size()>1).mean())
linha("CDE (%)", lambda x: 100*(x.segmento_cliente=='CDE').mean())

print("\n  [L1 - SAZONALIDADE]")
linha("volume medio/dia", lambda x: x._dt.dt.date.value_counts().mean())
linha("desvio padrao/dia", lambda x: x._dt.dt.date.value_counts().std())
linha("variacao do volume (%)", lambda x: 100*x._dt.dt.date.value_counts().std()/x._dt.dt.date.value_counts().mean(), nota="<- alvo: subir")
linha("menor dia", lambda x: x._dt.dt.date.value_counts().min(), "{:.0f}")
linha("maior dia", lambda x: x._dt.dt.date.value_counts().max(), "{:.0f}")
linha("razao segunda / domingo", lambda x: (x._dt.dt.dayofweek==0).sum()/max((x._dt.dt.dayofweek==6).sum(),1), "{:.2f}", "<- alvo: > 1")

print("\n  [L3 - FUSO HORARIO]")
com = lambda x: 100*x._dt.dt.hour.between(8,19).mean()
linha("volume 8h-19h BRT, geral (%)", com)
linha("  ... clientes CDE (%)", lambda x: 100*x[x.segmento_cliente=='CDE']._dt.dt.hour.between(8,19).mean(), nota="<- alvo: cair")
linha("  ... clientes nacionais (%)", lambda x: 100*x[x.segmento_cliente!='CDE']._dt.dt.hour.between(8,19).mean(), nota="<- alvo: manter alto")
linha("volume na madrugada 0h-6h (%)", lambda x: 100*x._dt.dt.hour.between(0,5).mean())

print("\n  [L5 - ATRITO ACUMULADO]")
bot_por = lambda x, n: 100*x[x.contatos_previos==n].resolvido_bot.mean()
linha("bot resolve - 1o contato (%)", lambda x: bot_por(x,0))
linha("bot resolve - 3o contato (%)", lambda x: bot_por(x,3), nota="<- alvo: cair na v8")
linha("bot resolve - 5o contato (%)", lambda x: bot_por(x,5), nota="<- alvo: cair na v8")
linha("bot resolve - em reabertura (%)", lambda x: 100*x[x.reabertura==True].resolvido_bot.mean())
linha("bot resolve - fora de reabertura (%)", lambda x: 100*x[x.reabertura!=True].resolvido_bot.mean())
linha("negativo em reabertura (%)", lambda x: 100*(x[x.reabertura==True].sentimento_geral=='Negativo').mean())
linha("negativo fora de reabertura (%)", lambda x: 100*(x[x.reabertura!=True].sentimento_geral=='Negativo').mean())
linha("CSAT em reabertura", lambda x: x[x.reabertura==True].csat.mean(), "{:.2f}")
linha("CSAT fora de reabertura", lambda x: x[x.reabertura!=True].csat.mean(), "{:.2f}")

print("\n  [EFEITOS COLATERAIS - acompanhar]")
linha("resolucao pelo bot, geral (%)", lambda x: 100*x.resolvido_bot.mean())
linha("transferencia iniciada (%)", lambda x: 100*x.transferencia_iniciada.mean())
linha("humano atendeu (%)", lambda x: 100*x.humano_atendeu.mean())
linha("reaberturas (%)", lambda x: 100*(x.reabertura==True).mean())
linha("CSAT geral", lambda x: x.csat.mean(), "{:.2f}")
linha("abandono (%)", lambda x: 100*(x.status_conversa=='Abandonada pelo cliente').mean())
linha("duracao media (min)", lambda x: x.duracao_seg.mean()/60)

print("\n  [SCHEMA]")
c7, c8 = list(d["v7"].columns), list(d["v8"].columns)
c7 = [c for c in c7 if c != "_dt"]; c8 = [c for c in c8 if c != "_dt"]
print(f"    colunas identicas e na mesma ordem: {'SIM' if c7 == c8 else 'NAO'}")
if c7 != c8:
    print(f"    so na v7: {set(c7)-set(c8)}\n    so na v8: {set(c8)-set(c7)}")

print("\n" + "=" * 78)
print("""
  COMO LER
  --------
  L1, L3 e L5 sao as correcoes: as colunas v8 devem se afastar da v7.
  "Efeitos colaterais" sao consequencias esperadas do atrito - o bot resolve
  menos porque agora o cliente reincidente e mais dificil, e isso realimenta
  a reabertura. Se esses numeros parecerem exagerados, da para calibrar os
  parametros atrito_* no CONFIG do gerador.
""")
