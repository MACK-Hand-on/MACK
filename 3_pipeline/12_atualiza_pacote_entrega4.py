# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 4
Atualiza o pacote da Entrega 4 com o que mudou depois do fechamento do modelo,
e regera o zip.

O que este script faz, em ordem:
  1. Confere que os arquivos de origem existem e estao atualizados
  2. Guarda o zip atual em 9_entrega4/_scratch/ com data e hora (nada e apagado)
  3. Copia para dentro do pacote:
       3_pipeline/Kenzie360_Modelo_Risco.ipynb  (o notebook JA EXECUTADO)
       3_pipeline/11_carga_score_gold.py        (novo)
       7_modelo/score_risco.csv                 (regerado)
  4. Regera Entrega4_Kenzie360.zip
  5. Copia o zip novo para 9_entrega4/PARA_O_DRIVE/
  6. Confere contagem de arquivos e tamanho

Como rodar (Ubuntu/WSL, com o ambiente ativado):
    kenzie
    python3 12_atualiza_pacote_entrega4.py

Pode rodar mais de uma vez sem medo.
"""

import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ==================================================================== apoio

def titulo(texto):
    print()
    print("=" * 66)
    print(f"  {texto}")
    print("=" * 66)


def passo(texto):
    print(f"\n>> {texto}")


def ok(texto):
    print(f"   [OK] {texto}")


def aviso(texto):
    print(f"   [!]  {texto}")


def erro_fatal(texto):
    print(f"\n   [ERRO] {texto}")
    print("\n   Cole esta tela no chat que eu te ajudo a destravar.\n")
    sys.exit(1)


def mb(caminho):
    return caminho.stat().st_size / 1024 / 1024


# ==================================================================== caminhos

PIPELINE = Path(__file__).resolve().parent          # 3_pipeline/
RAIZ     = PIPELINE.parent                          # raiz do projeto
ENTREGA  = RAIZ / "9_entrega4"
PACOTE   = ENTREGA / "Entrega4_Kenzie360"
ZIP      = ENTREGA / "Entrega4_Kenzie360.zip"
SCRATCH  = ENTREGA / "_scratch"
DRIVE    = ENTREGA / "PARA_O_DRIVE"

# origem -> destino dentro do pacote
COPIAR = [
    (PIPELINE / "Kenzie360_Modelo_Risco.ipynb",    PACOTE / "3_pipeline" / "Kenzie360_Modelo_Risco.ipynb"),
    (PIPELINE / "11_carga_score_gold.py",          PACOTE / "3_pipeline" / "11_carga_score_gold.py"),
    (PIPELINE / "12_atualiza_pacote_entrega4.py",  PACOTE / "3_pipeline" / "12_atualiza_pacote_entrega4.py"),
    (PIPELINE / "13_carga_lote_novo_gold.py",      PACOTE / "3_pipeline" / "13_carga_lote_novo_gold.py"),
    (PIPELINE / "score_risco.csv",                 PACOTE / "7_modelo"   / "score_risco.csv"),
    (PIPELINE / "score_lote_novo.csv",             PACOTE / "7_modelo"   / "score_lote_novo.csv"),
    (PIPELINE / "score_lote_novo_gold.csv",        PACOTE / "7_modelo"   / "score_lote_novo_gold.csv"),
]

# ==================================================================== inicio

titulo("KENZIE 360 - Atualizacao do pacote da Entrega 4")
print(f"  Pacote : {PACOTE}")

if not PACOTE.is_dir():
    erro_fatal(f"Nao encontrei a pasta do pacote em {PACOTE}")


# ------------------------------------------------- 1. conferir a origem
passo("Conferindo os arquivos de origem")

for origem, _ in COPIAR:
    if not origem.exists():
        erro_fatal(
            f"Nao encontrei {origem.name} em 3_pipeline/.\n"
            "          Rode antes o 09_modelo_risco_bot.py e o notebook."
        )
    ok(f"{origem.name}  ({mb(origem)*1024:.0f} KB)")

# o notebook so vale se estiver executado: toda celula de codigo com saida
import json
nb = json.loads((PIPELINE / "Kenzie360_Modelo_Risco.ipynb").read_text(encoding="utf-8"))
codigo = [c for c in nb["cells"] if c["cell_type"] == "code"]
sem_saida = [c for c in codigo if not c.get("outputs") and "".join(c["source"]).strip()]
if sem_saida:
    erro_fatal(
        f"O notebook tem {len(sem_saida)} celula(s) de codigo sem saida.\n"
        "          Abra no Jupyter, rode Restart Kernel and Run All Cells,\n"
        "          salve com Ctrl+S e rode este script de novo."
    )
ok(f"notebook executado: {len(codigo)} celulas de codigo, todas com saida")


# ------------------------------------------------- 2. guardar o zip atual
passo("Guardando a versao anterior do zip")

SCRATCH.mkdir(exist_ok=True)
if ZIP.exists():
    carimbo = datetime.now().strftime("%Y%m%d_%H%M")
    guardado = SCRATCH / f"Entrega4_Kenzie360_{carimbo}.zip"
    shutil.copy2(ZIP, guardado)
    ok(f"copia guardada em _scratch/{guardado.name}  ({mb(guardado):.1f} MB)")
else:
    aviso("nao havia zip anterior - seguindo")


# ------------------------------------------------- 3. copiar para o pacote
passo("Atualizando os arquivos dentro do pacote")

for origem, destino in COPIAR:
    destino.parent.mkdir(parents=True, exist_ok=True)
    novo = not destino.exists()
    shutil.copy2(origem, destino)
    marca = "NOVO" if novo else "atualizado"
    ok(f"{destino.relative_to(PACOTE)}  ({marca})")


# ------------------------------------------------- 4. regerar o zip
passo("Regerando o zip")

arquivos = sorted(p for p in PACOTE.rglob("*") if p.is_file())
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in arquivos:
        z.write(p, p.relative_to(PACOTE.parent))
ok(f"{len(arquivos)} arquivos, {mb(ZIP):.1f} MB")

# conferencia de integridade: le o zip de volta
with zipfile.ZipFile(ZIP) as z:
    ruim = z.testzip()
    dentro = len(z.namelist())
if ruim:
    erro_fatal(f"O zip saiu corrompido no arquivo {ruim}")
if dentro != len(arquivos):
    erro_fatal(f"O zip tem {dentro} entradas, esperava {len(arquivos)}")
ok("integridade conferida - o zip abre e tem tudo dentro")


# ------------------------------------------------- 5. copia para o Drive
passo("Atualizando a copia de PARA_O_DRIVE")

DRIVE.mkdir(exist_ok=True)
shutil.copy2(ZIP, DRIVE / ZIP.name)
ok(f"PARA_O_DRIVE/{ZIP.name}  ({mb(ZIP):.1f} MB)")


# ------------------------------------------------- 6. resumo
titulo("PRONTO")
print(f"""
  Zip da entrega : {ZIP}
  Arquivos       : {len(arquivos)}
  Tamanho        : {mb(ZIP):.1f} MB

  Proximos passos:
    1. Arrastar o conteudo de 9_entrega4/PARA_O_DRIVE/ para a pasta do Drive
    2. Subir Entrega4_Kenzie360.zip no Moodle
""")
