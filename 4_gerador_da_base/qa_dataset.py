# -*- coding: utf-8 -*-
"""QA / varredura completa do dataset Kenzie 360 (somente leitura)."""
import pandas as pd, numpy as np, re
c = pd.read_csv("dataset_kenzie360_atendimentos.csv", sep=";", encoding="utf-8-sig")
m = pd.read_csv("dataset_kenzie360_mensagens.csv", sep=";", encoding="utf-8-sig")

achados = []
def check(nome, ok, detalhe=""):
    achados.append((("OK " if ok else "!! "), nome, detalhe))
    print(("OK  " if ok else "!!  ") + nome + ((" -> " + detalhe) if detalhe else ""))

print("="*70); print("VARREDURA DE QA - KENZIE 360"); print("="*70)
print(f"Conversas: {len(c):,} x {c.shape[1]} | Mensagens: {len(m):,} x {m.shape[1]}")

print("\n[1] INTEGRIDADE ESTRUTURAL")
check("id_conversa unico (conversas)", c["id_conversa"].duplicated().sum()==0, f"{c['id_conversa'].duplicated().sum()} dups")
check("sem linhas totalmente vazias", c.isna().all(axis=1).sum()==0)
check("clientes unicos ~15k", c["id_cliente"].nunique()>=14000, f"{c['id_cliente'].nunique()}")
dtypes_ok = True
check("colunas esperadas presentes",
      set(["id_conversa","status_conversa","resolvida","origem","csat","transcricao_completa"]).issubset(c.columns))

print("\n[2] INTEGRIDADE REFERENCIAL")
conv_ids=set(c["id_conversa"]); msg_ids=set(m["id_conversa"])
check("toda mensagem tem conversa", len(msg_ids-conv_ids)==0, f"{len(msg_ids-conv_ids)} orfas")
check("toda conversa tem mensagem", len(conv_ids-msg_ids)==0, f"{len(conv_ids-msg_ids)} sem msg")
cnt=m.groupby("id_conversa").size()
merged=c.set_index("id_conversa")["num_mensagens"]
dif=(merged - cnt.reindex(merged.index)).abs()
check("num_mensagens confere com a tabela de mensagens", (dif.fillna(-1)==0).all(), f"{int((dif!=0).sum())} divergencias")

print("\n[3] ORDEM E TIMESTAMPS")
m_s=m.sort_values(["id_conversa","ordem"])
# ordem sequencial 1..n
def ordem_ok(g):
    return list(g)==list(range(1,len(g)+1))
bad_ordem=0
for cid,g in m_s.groupby("id_conversa")["ordem"]:
    if not ordem_ok(g.values): bad_ordem+=1
check("ordem sequencial (1..n) por conversa", bad_ordem==0, f"{bad_ordem} conversas com problema")
# timestamps nao decrescentes
m_s["ts"]=pd.to_datetime(m_s["timestamp"])
dec=m_s.groupby("id_conversa")["ts"].apply(lambda s: (s.diff().dt.total_seconds().fillna(0)<0).any())
check("timestamps nao-decrescentes na conversa", dec.sum()==0, f"{int(dec.sum())} conversas com retrocesso")
# janela de datas
dh=pd.to_datetime(c["data_hora"])
check("data_hora dentro de ~6 meses (fev-ago/2026)", (dh.min()>=pd.Timestamp('2026-02-01')) and (dh.max()<=pd.Timestamp('2026-08-19')), f"{dh.min()} a {dh.max()}")

print("\n[4] CONSISTENCIA LOGICA (status/flags)")
prim=m_s.groupby("id_conversa")["remetente"].first()
pm=c.set_index("id_conversa")["origem"]; prim_al=prim.reindex(pm.index)
ok_at=(prim_al[pm=="Ativo"]=="Kenzie").all(); ok_re=(prim_al[pm=="Receptivo"]=="Cliente").all()
check("1a msg: Ativo->Kenzie e Receptivo->Cliente", bool(ok_at and ok_re), f"ativo_ok={ok_at} recep_ok={ok_re}")
ult=m_s.groupby("id_conversa")["remetente"].last()
term_cli=c.merge(ult.rename("ult"),on="id_conversa")
mask_bad_end=(term_cli["ult"]=="Cliente") & (~term_cli["status_conversa"].str.contains("Abandon|Ruido|Sem resposta|Opt-out|engano|contexto|resolvido",case=False,na=False))
check("so abandono/ruido terminam no cliente", mask_bad_end.sum()==0, f"{int(mask_bad_end.sum())} conversas fecham no cliente indevidamente")
# resolvido_bot <-> status
check("resolvido_bot=True == status 'Resolvida pelo bot'",
      (c["resolvido_bot"]==(c["status_conversa"]=="Resolvida pelo bot")).all())
# humano presente <-> flag
tem_hum=m.groupby("id_conversa")["remetente"].apply(lambda s:(s=="Atendente Humano").any())
cc=c.merge(tem_hum.rename("tem_hum"),on="id_conversa")
check("humano_atendeu == existe Atendente Humano nas msgs",
      (cc["humano_atendeu"]==cc["tem_hum"]).all(), f"{int((cc['humano_atendeu']!=cc['tem_hum']).sum())} divergencias")
check("transferencia_iniciada e superset de humano_atendeu",
      bool(c[c["humano_atendeu"]]["transferencia_iniciada"].all()))
ch=c["canal_humano"].fillna("").astype(str)!=""
check("canal_humano preenchido == humano_atendeu", (ch==c["humano_atendeu"]).all(), f"{int((ch!=c['humano_atendeu']).sum())} divergencias")
area=c["area_encaminhada"].fillna("").astype(str)!=""
check("area_encaminhada so quando humano atendeu", (area & ~c["humano_atendeu"]).sum()==0, f"{int((area & ~c['humano_atendeu']).sum())}")
# resolvida dominio
check("resolvida em dominio esperado", set(c["resolvida"].unique()).issubset({"Sim","Nao","Desconhecido","Nao aplicavel"}), str(set(c["resolvida"].unique())))
# origem dominio
check("origem em {Ativo,Receptivo}", set(c["origem"].unique())=={"Ativo","Receptivo"}, str(set(c["origem"].unique())))
# status Opt-out/Sem resposta => origem Ativo
ativo_status=c[c["status_conversa"].isin(["Opt-out / descadastro","Sem resposta (disparo ativo)"])]
check("opt-out/sem-resposta sempre origem Ativo", (ativo_status["origem"]=="Ativo").all(), f"{int((ativo_status['origem']!='Ativo').sum())}")

print("\n[5] DOMINIOS E NULOS")
check("csat entre 1 e 5 (ou nulo)", c["csat"].dropna().between(1,5).all(), f"min {c['csat'].min()} max {c['csat'].max()}")
check("% csat em branco plausivel (50-85%)", 0.50<=c["csat"].isna().mean()<=0.85, f"{100*c['csat'].isna().mean():.1f}%")
sent_cli=m[m["remetente"]=="Cliente"]["sentimento"]
check("sentimento do cliente em dominio", set(sent_cli.dropna().unique()).issubset({"Negativo","Neutro","Positivo"}), str(set(sent_cli.unique())))
sent_bot=m[m["remetente"]!="Cliente"]["sentimento"].fillna("")
check("sentimento vazio p/ bot/humano", (sent_bot=="").all(), f"{int((sent_bot!='').sum())} com sentimento")
check("tipo_midia em dominio", set(m["tipo_midia"].unique())=={"texto","imagem","audio"}, str(set(m["tipo_midia"].unique())))
check("midia so no cliente", (m[m["remetente"]!="Cliente"]["tipo_midia"]=="texto").all())
check("produto N/A so em ruido/ativo", set(c[c["produto_relacionado"]=="N/A"]["status_conversa"].unique()).issubset({"Ruido - contato por engano","Cliente ja havia resolvido","Contato sem contexto (oi/teste)","Opt-out / descadastro","Sem resposta (disparo ativo)"}))

print("\n[6] FAIXAS / OUTLIERS")
check("duracao_seg >= 0", (c["duracao_seg"]>=0).all(), f"min {c['duracao_seg'].min()}")
check("num_mensagens >= 1", (c["num_mensagens"]>=1).all(), f"min {c['num_mensagens'].min()}")
check("num_mensagens_cliente <= num_mensagens", (c["num_mensagens_cliente"]<=c["num_mensagens"]).all())
g=c.groupby("id_cliente").size()
check("teto de contatos por cliente (super-usuario)", g.max()<=45, f"max {g.max()} contatos (cap=45)")
check("reabertura apenas com contatos_previos>0", ((c["reabertura"]) & (c["contatos_previos"]==0)).sum()==0)

print("\n[7] TEXTO / IDIOMA / SENTIMENTO")
# idioma consistente conversa x mensagens
idc=c.set_index("id_conversa")["idioma"]
mm=m.merge(idc.rename("idioma_conv"),on="id_conversa")
check("idioma consistente entre conversa e mensagens", (mm["idioma"]==mm["idioma_conv"]).all(), f"{int((mm['idioma']!=mm['idioma_conv']).sum())} divergencias")
check("sem texto vazio em mensagens", (m["texto"].fillna("").str.strip()=="").sum()==0, f"{int((m['texto'].fillna('').str.strip()=='').sum())} vazios")
# anti-vazamento por idioma
NEG={"PT":["frustrado","absurdo","pessimo","paciencia","insatisfeito","urgencia","continua","nao resolveu","encerrar","concorrente","reclamar","insatisfeito"],
     "EN":["frustrated","unacceptable","terrible","patience","unhappy","urgently","still","didn't","close my account","competitor","complain"],
     "ES":["frustrado","absurdo","pesimo","paciencia","insatisfecho","urgencia","sigue","no lo resolvio","cerrar","competencia","reclamar"]}
POS={"PT":["obrigado","excelente","perfeito","otimo","satisfeito","parabens","deu certo","funcionou","consegui","valeu","resolvido","thanks"],
     "EN":["thank","excellent","perfect","great","satisfied","awesome","worked","solved","resolved"],
     "ES":["gracias","excelente","perfecto","satisfecho","genial","funciono","resuelto"]}
cli=m[m["remetente"]=="Cliente"].copy()
def has(ws,t): t=str(t).lower(); return any(w in t for w in ws)
for lg in ["PT","EN","ES"]:
    s=cli[cli["idioma"]==lg]; ng=s[s["sentimento"]=="Negativo"]; ps=s[s["sentimento"]=="Positivo"]
    rn=ng["texto"].apply(lambda x:has(NEG[lg],x)).mean() if len(ng) else 1
    rp=ps["texto"].apply(lambda x:has(POS[lg],x)).mean() if len(ps) else 1
    check(f"anti-vazamento {lg} (neg>=85%, pos>=90%)", rn>=0.85 and rp>=0.90, f"neg {100*rn:.1f}% pos {100*rp:.1f}%")

print("\n[8] DISTRIBUICOES-CHAVE (referencia)")
print("Segmento:", (c["segmento_cliente"].value_counts(normalize=True)*100).round(1).to_dict())
print("Origem:", (c["origem"].value_counts(normalize=True)*100).round(1).to_dict())
print("Resolucao bot: %.1f%% | Transf iniciada: %.1f%% | Humano atendeu: %.1f%%"%(100*c["resolvido_bot"].mean(),100*c["transferencia_iniciada"].mean(),100*c["humano_atendeu"].mean()))
print("Recorrentes(2+): %.1f%% | Reaberturas: %.1f%%"%(100*(g>=2).mean(),100*c["reabertura"].mean()))
print("CSAT humano: %.2f | geral: %.2f"%(c[c["humano_atendeu"]]["csat"].mean(),c["csat"].mean()))

print("\n"+"="*70)
falhas=[a for a in achados if a[0]=="!! "]
print(f"RESULTADO: {len(achados)-len(falhas)}/{len(achados)} checagens OK | {len(falhas)} alertas")
for _,n,d in falhas: print("  !! "+n+((" -> "+d) if d else ""))

print("\n[9] V8 - PADRONIZACAO E DESCARACTERIZACAO (LGPD)")
# 9.1 zero PII bruto
_PII=[(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b","CPF"),(r"[\w.\-]+@[\w\-]+\.[A-Za-z]{2,}","EMAIL"),
      (r"\+?\d{2}\s\d{2}\s9\d{4}-\d{4}","TELEFONE"),(r"\b\d{5}-\d\b","CONTA")]
_tot=sum(int(m["texto"].str.contains(rx,regex=True,na=False).sum()) for rx,_ in _PII)
check("zero dado pessoal bruto (CPF/email/tel/conta)", _tot==0, f"{_tot} ocorrencias")
check("mascaramento presente e rastreavel", m["contem_dado_mascarado"].sum()>0,
      f"{int(m['contem_dado_mascarado'].sum()):,} msgs mascaradas ({100*m['contem_dado_mascarado'].mean():.1f}%)")
check("qtd_dados_mascarados bate com as mensagens",
      int(c["qtd_dados_mascarados"].sum())==int(m["contem_dado_mascarado"].sum()),
      f"conv={int(c['qtd_dados_mascarados'].sum())} vs msg={int(m['contem_dado_mascarado'].sum())}")
check("id_cliente pseudonimizado (hash, nao sequencial)",
      bool(c["id_cliente"].str.match(r"^CLI-[0-9A-F]{12}$").all()), str(c["id_cliente"].iloc[0]))
# 9.2 identidade canonica da Kenzie
_ident=r"^(Ola! Sou a Kenzie, assistente virtual do banco\.|Hello! I'm Kenzie, the bank's virtual assistant\.|Hola! Soy Kenzie, asistente virtual del banco\.)"
_pk=m[(m["remetente"]=="Kenzie")&(m["ordem"].isin([1,2]))]
_first_bot=_pk.sort_values(["id_conversa","ordem"]).groupby("id_conversa").head(1)["texto"]
check("1a fala da Kenzie usa identidade canonica", bool(_first_bot.str.match(_ident).all()),
      f"{100*_first_bot.str.match(_ident).mean():.1f}%")
# 9.3 transcricao padronizada
check("transcricao no formato '[NN] Remetente: texto'",
      bool(c["transcricao_completa"].str.match(r"^\[01\] (Cliente|Kenzie): ").all()))
# 9.4 coerencia segmento x conteudo
_nac=c[c["segmento_cliente"].isin(["Correntista Nacional","PJ"])]
_pat=r"passaporte|passport|morando fora|residencia no exterior|domicilio en el exterior|proof of address abroad|aqui no exterior|foreign number|vivo fuera"
check("nacional/PJ nao fala como expatriado",
      int(_nac["primeira_mensagem_cliente"].str.contains(_pat,case=False,na=False).sum())==0,
      f"{int(_nac['primeira_mensagem_cliente'].str.contains(_pat,case=False,na=False).sum())} casos")
_pj=c[c["segmento_cliente"]=="PJ"]
check("PJ nao pergunta 'o que e CPF'", int((_pj["categoria_assunto"]=="Termos e Documentacao BR").sum())==0)
check("PJ tem tema corporativo proprio", "Operacoes PJ - Folha e Pagamentos" in set(_pj["categoria_assunto"]))

print("\n"+"="*70)
_f2=[a for a in achados if a[0]=="!! "]
print(f"RESULTADO FINAL: {len(achados)-len(_f2)}/{len(achados)} checagens OK | {len(_f2)} alertas")
for _,n_,d_ in _f2: print("  !! "+n_+((" -> "+d_) if d_ else ""))
