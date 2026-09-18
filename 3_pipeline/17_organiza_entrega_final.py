# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Entrega Final
Organiza o pacote de entrega E prepara o que falta subir no Git.

O QUE ESTE SCRIPT FAZ
---------------------
FASE 1  Monta a pasta 10_entrega_final/Entrega_Final_Kenzie360/ com os arquivos
        que vao para o Moodle e para o Drive, em sete subpastas, e gera o zip.

FASE 2  Copia para o clone do repositorio (~/MACK) os arquivos novos que ainda
        nao estao versionados, e imprime os comandos git prontos para colar.

O QUE ELE DELIBERADAMENTE **NAO** COLOCA NO PACOTE
--------------------------------------------------
Material interno de preparacao nao e entrega academica, e alguns desses
arquivos citam problemas em aberto que nao devem circular:

  - Cola_QA_Banca            (cola de bolso da banca)
  - Roteiro_* / Fonte_NotebookLM_*  (falas e material de ensaio)
  - HANDOFF_*                (passagens de bastao entre nos)
  - Revisao_* / Review_*     (revisoes internas, com pendencias)
  - Pauta_*                  (pautas de reuniao)
  - Respostas_Revisao_*, Ajustes_Pos_Ensaio_*  (correcoes de ensaio)

Esses ficam na pasta do projeto e no repositorio, nao no pacote entregue.

COMO RODAR
    kenzie
    cd "/mnt/c/Users/ilans/Claude/Projects/Projeto Kenzie 360/3_pipeline"
    python3 17_organiza_entrega_final.py

Pode rodar mais de uma vez: a pasta do pacote e recriada do zero e o zip
anterior e preservado com carimbo de data.
"""

import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

# ==================================================================== apoio

def titulo(t):
    print(); print("=" * 72); print(f"  {t}"); print("=" * 72)

def passo(t): print(f"\n>> {t}")
def ok(t):    print(f"   [OK]    {t}")
def falta(t): print(f"   [FALTA] {t}")
def aviso(t): print(f"   [!]     {t}")

def erro_fatal(t, e=None):
    print(f"\n   [ERRO] {t}")
    if e: print(f"          {type(e).__name__}: {str(e)[:300]}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


# ==================================================================== caminhos

PIPELINE = Path(__file__).resolve().parent
PROJETO  = PIPELINE.parent
DOCS     = PROJETO / "1_documentos"
SAIDA    = PROJETO / "10_entrega_final"
PACOTE   = SAIDA / "Entrega_Final_Kenzie360"
DRIVE    = SAIDA / "PARA_O_DRIVE"
CLONE    = Path.home() / "MACK"

if PIPELINE.name != "3_pipeline":
    erro_fatal(f"Rode de dentro da pasta 3_pipeline. Estou em {PIPELINE}")

inicio = time.time()
titulo("KENZIE 360 - organizando a entrega final")
print(f"  projeto : {PROJETO}")
print(f"  pacote  : {PACOTE}")
print(f"  clone   : {CLONE}")


# ============================================ FASE 1 - o pacote de entrega

# (origem, destino dentro do pacote, obrigatorio)
MANIFESTO = [
    # --- 0. o indice
    (DOCS / "LEIA-ME_Entrega_Final.md",                     ".",                 True),
    (DOCS / "Kenzie360_LEIA-ME_Entrega_Final.pdf",          ".",                 False),

    # --- 1. apresentacao
    (DOCS / "Kenzie360_Apresentacao.pptx",                  "1_apresentacao",    True),
    (DOCS / "Kenzie360_Apresentacao.pdf",                   "1_apresentacao",    False),

    # --- 2. documentos: o escopo, os numeros, as decisoes
    (DOCS / "Briefing_Projeto_Kenzie360_Consolidado.pdf",   "2_documentos",      True),
    (DOCS / "Briefing_Projeto_Kenzie360_Consolidado.docx",  "2_documentos",      False),
    (DOCS / "Item3_Governanca.md",                          "2_documentos",      True),
    (DOCS / "Kenzie360_Governanca.pdf",                     "2_documentos",      False),
    (DOCS / "Item5_Trilhas_de_Carreira.md",                 "2_documentos",      True),
    (DOCS / "Kenzie360_Trilhas_de_Carreira.pdf",            "2_documentos",      False),
    (DOCS / "Features_e_Vazamento.md",                      "2_documentos",      True),
    (DOCS / "Kenzie360_Features_e_Vazamento.pdf",           "2_documentos",      False),
    (DOCS / "Horas_Lote_Novo.md",                           "2_documentos",      False),
    (DOCS / "Kenzie360_Horas_Lote_Novo.pdf",                "2_documentos",      False),
    # os que moram no pacote da Entrega 4
    (PROJETO / "9_entrega4" / "Numeros_Oficiais_Modelo13.md",   "2_documentos",  False),
    (PROJETO / "9_entrega4" / "Defesa_do_Modelo.md",            "2_documentos",  False),
    (PROJETO / "9_entrega4" / "Setup_GCP_Kenzie360.md",         "2_documentos",  False),
    (PROJETO / "9_entrega4" / "Carga_Incremental_Lote_Novo.md", "2_documentos",  False),

    # --- 3. pipeline (os scripts sao copiados em bloco mais abaixo)
    (PIPELINE / "Kenzie360_Modelo_Risco.ipynb",             "3_pipeline",        True),
    (PROJETO / "requirements.txt",                          "3_pipeline",        False),

    # --- 4. modelo
    (PIPELINE / "coef_simulador.json",                      "4_modelo",          True),
    (PIPELINE / "score_risco.csv",                           "4_modelo",         False),
    (PIPELINE / "score_lote_novo.csv",                       "4_modelo",         False),
    (PIPELINE / "fila_correcao.csv",                         "4_modelo",         False),
    (PIPELINE / "tempo_ate_humano.csv",                      "4_modelo",         False),

    # --- 5. simulador
    (PIPELINE / "simulador_v2.html",                        "5_simulador",       True),

    # --- 6. painel (exportado a mao do Looker para 1_documentos/, uma vez)
    (DOCS / "Kenzie360_Painel_Looker.pdf",                  "6_painel",          False),
    (DOCS / "Painel_Looker_link.txt",                       "6_painel",          False),
]

# os scripts da pipeline, na ordem
SCRIPTS = sorted([p for p in PIPELINE.glob("*.py")
                  if p.name != "17_organiza_entrega_final.py"])

passo("FASE 1/2 - montando o pacote")

if PACOTE.exists():
    shutil.rmtree(PACOTE)
for sub in (".", "1_apresentacao", "2_documentos", "3_pipeline", "4_modelo",
            "5_simulador", "6_painel"):
    (PACOTE / sub).mkdir(parents=True, exist_ok=True)
DRIVE.mkdir(parents=True, exist_ok=True)

copiados, faltando = 0, []
for origem, destino, obrigatorio in MANIFESTO:
    alvo = PACOTE / destino / origem.name
    if origem.exists():
        shutil.copy2(origem, alvo)
        copiados += 1
    else:
        faltando.append((origem, obrigatorio))

for s in SCRIPTS:
    shutil.copy2(s, PACOTE / "3_pipeline" / s.name)
    copiados += 1
sql = PIPELINE / "sql"
if sql.is_dir():
    shutil.copytree(sql, PACOTE / "3_pipeline" / "sql", dirs_exist_ok=True)
    ok("pasta sql/ copiada")

ok(f"{copiados} arquivos no pacote ({len(SCRIPTS)} scripts da pipeline)")

obrigatorios_faltando = [o for o, ob in faltando if ob]
for origem, obrigatorio in faltando:
    (falta if obrigatorio else aviso)(f"{'OBRIGATORIO ' if obrigatorio else 'opcional '}{origem.name}")

if obrigatorios_faltando:
    print()
    aviso("faltam arquivos OBRIGATORIOS. Resolva antes de entregar:")
    for o in obrigatorios_faltando:
        print(f"        esperado em: {o}")
    print("\n        Se o arquivo existe com outro nome, renomeie ou me avise.")

# um aviso especifico, porque e o unico que exige acao manual
painel = PACOTE / "6_painel"
if not any(painel.iterdir()):
    aviso("a pasta 6_painel esta vazia. Exporte o painel do Looker em PDF "
          "(Compartilhar > Baixar como PDF), salve como "
          "1_documentos/Kenzie360_Painel_Looker.pdf e o link de visualizacao "
          "em 1_documentos/Painel_Looker_link.txt - depois rode este script de "
          "novo, que ele leva os dois para o pacote sozinho.")

# ------------------------------------------------- o zip
passo("Gerando o zip")

ZIP = SAIDA / "Entrega_Final_Kenzie360.zip"
if ZIP.exists():
    carimbo = datetime.now().strftime("%Y%m%d_%H%M")
    backup = SAIDA / f"_anterior_Entrega_Final_{carimbo}.zip"
    shutil.move(str(ZIP), str(backup))
    ok(f"zip anterior preservado como {backup.name}")

try:
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(PACOTE.rglob("*")):
            if arq.is_file():
                z.write(arq, arq.relative_to(PACOTE.parent))
except Exception as e:
    erro_fatal("Falhei ao gerar o zip.", e)

with zipfile.ZipFile(ZIP) as z:
    if z.testzip() is not None:
        erro_fatal("O zip saiu corrompido.")
    n = len(z.namelist())

mb = ZIP.stat().st_size / 1_048_576
ok(f"{ZIP.name} - {n} arquivos, {mb:.1f} MB, integridade conferida")

shutil.copy2(ZIP, DRIVE / ZIP.name)
ok(f"copia em {DRIVE.name}/ para arrastar no Drive")

if mb > 18:
    aviso(f"{mb:.1f} MB pode estourar o limite do Moodle. Se estourar, tire a "
          f"pasta 4_modelo (os CSVs) e reenvie - o conteudo dela e reproduzivel "
          f"rodando a pipeline.")


# ============================================ FASE 2 - o que falta no Git

passo("FASE 2/2 - preparando o que falta subir no Git")

if not (CLONE / ".git").is_dir():
    aviso(f"nao achei um clone do repositorio em {CLONE}")
    print("        Se o seu clone esta em outro lugar, edite a variavel CLONE "
          "no topo deste script.")
    print("        Fase 2 pulada - a Fase 1 esta pronta.")
else:
    # (origem, destino relativo dentro do repositorio)
    PARA_O_GIT = []

    # scripts e artefatos da pipeline
    for s in SCRIPTS:
        PARA_O_GIT.append((s, Path("3_pipeline") / s.name))
    for nome in ("Kenzie360_Modelo_Risco.ipynb", "simulador_v2.html",
                 "coef_simulador.json"):
        p = PIPELINE / nome
        if p.exists():
            PARA_O_GIT.append((p, Path("3_pipeline") / nome))
    if sql.is_dir():
        for q in sql.glob("*.sql"):
            PARA_O_GIT.append((q, Path("3_pipeline") / "sql" / q.name))

    # documentos: tudo o que e entrega, na pasta da sprint 5
    # No Git fica a FONTE. Os PDFs dos documentos sao render do markdown que
    # esta ao lado: eles vao no pacote de entrega (o zip do Moodle), nao no
    # repositorio, e 1_documentos/mkpdf.py os reconstroi a qualquer momento.
    # Duas excecoes deliberadas:
    #   - Kenzie360_Apresentacao.pptx - e a fonte do deck, nao tem markdown
    #   - Kenzie360_Apresentacao.pdf  - nao sai do .pptx sem PowerPoint, logo
    #                                   nao e reproduzivel a partir do repo
    # Os guias do painel (Guia_*_Gi.md) sao instrucoes de trabalho para uma
    # pessoa do time, nao entrega: ficam na pasta do projeto, fora do Git.
    DOCS_GIT = [
        "LEIA-ME_Entrega_Final.md",
        "Item3_Governanca.md",
        "Item5_Trilhas_de_Carreira.md",
        "Features_e_Vazamento.md",
        "Horas_Lote_Novo.md",
        "Kenzie360_Apresentacao.pptx",
        "Kenzie360_Apresentacao.pdf",
    ]
    for nome in DOCS_GIT:
        p = DOCS / nome
        if p.exists():
            PARA_O_GIT.append((p, Path("1_documentos") / "sprint5" / nome))

    # a ferramenta que gera os PDFs dos documentos - sem ela, os PDFs do
    # pacote de entrega nao sao reproduziveis a partir do repositorio
    if (DOCS / "mkpdf.py").exists():
        PARA_O_GIT.append((DOCS / "mkpdf.py", Path("1_documentos") / "mkpdf.py"))

    novos, atualizados = [], []
    for origem, rel in PARA_O_GIT:
        alvo = CLONE / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if not alvo.exists():
            novos.append(str(rel))
        elif origem.stat().st_size != alvo.stat().st_size or \
             origem.stat().st_mtime > alvo.stat().st_mtime:
            atualizados.append(str(rel))
        else:
            continue
        shutil.copy2(origem, alvo)

    ok(f"{len(novos)} arquivos novos, {len(atualizados)} atualizados")
    for r in novos[:40]:       print(f"        novo       {r}")
    if len(novos) > 40:        print(f"        ... e mais {len(novos)-40}")
    for r in atualizados[:20]: print(f"        atualizado {r}")
    if len(atualizados) > 20:  print(f"        ... e mais {len(atualizados)-20}")

    if not novos and not atualizados:
        ok("o repositorio ja esta em dia - nada para copiar")

    titulo("AGORA RODE ESTES COMANDOS, UM POR VEZ")
    print(f"""
  cd {CLONE}
  git pull
  git status

  # confira a lista. NAO deve aparecer:
  #   - infra/environments/dev/.terraform.lock.hcl   (e do Jhonny, dispara a esteira)
  #   - qualquer .csv da base completa               (grande demais para o Git)
  #   - _LIXO_pode_apagar/ ou arquivos orfaos

  git add -A
  git status            # confira de novo, depois do add

  git commit -m "Sprint 5: entrega final, apresentacao da banca e views de monitoramento

Pipeline: 14_cria_gold_painel, 15_cria_vw_monitoramento, 16_horas_lote_novo,
17_organiza_entrega_final e o simulador v2.
Documentos: LEIA-ME da entrega final, itens 3 e 5 do escopo, features e
vazamento anotado, a deriva traduzida em horas, e os guias do painel.
Apresentacao da banca de 17/09 com o roteiro.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CJMgmALiGudaoCH7JWjpug"

  git push
""")

titulo("PRONTO")
print(f"""
  PACOTE      {PACOTE}
  ZIP         {ZIP}  ({mb:.1f} MB)
  PARA O DRIVE {DRIVE}

  Ainda na mao:
    1. exportar o painel do Looker em PDF para 6_painel/
    2. subir o zip no Moodle
    3. arrastar o zip e os PDFs para a pasta do Drive
    4. rodar os comandos git acima

  Tempo total: {time.time()-inicio:.0f}s
""")
