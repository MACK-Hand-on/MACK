# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2 - Trilha 0
Teste de fumaca da fundacao GCP.

Como rodar (com o ambiente ativado, de dentro de 3_pipeline/):
    python3 00_teste_conexao.py

O script faz 5 checagens e imprime um relatorio no final.
Nao cria, nao altera e nao apaga nada na nuvem. E so leitura.
"""

import sys
from pathlib import Path

# Os caminhos vem do config, que sabe onde os dados moram na estrutura
# de pastas do projeto (2_dados/).
try:
    import config_kenzie as cfg
    ARQ_ATENDIMENTOS = cfg.CSV_ATENDIMENTOS
    ARQ_MENSAGENS = cfg.CSV_MENSAGENS
except Exception:
    # se o config nao carregar, procura ao lado do script (modo de emergencia)
    PASTA = Path(__file__).resolve().parent
    ARQ_ATENDIMENTOS = PASTA / "dataset_kenzie360_atendimentos.csv"
    ARQ_MENSAGENS = PASTA / "dataset_kenzie360_mensagens.csv"

resultados = []


def registrar(nome, ok, detalhe=""):
    resultados.append((nome, ok, detalhe))
    marcador = "OK   " if ok else "FALHA"
    print(f"[{marcador}] {nome}")
    if detalhe:
        print(f"         {detalhe}")


print("=" * 62)
print("  KENZIE 360 - Teste de fumaca da fundacao GCP")
print("=" * 62)
print()

# ---------------------------------------------------------------- 1/5
print(">> 1/5  Bibliotecas Python")
try:
    import pandas as pd
    from google.cloud import bigquery
    from google.cloud import storage
    registrar(
        "Bibliotecas instaladas",
        True,
        f"pandas {pd.__version__} | google-cloud-bigquery e storage presentes",
    )
except ImportError as e:
    registrar(
        "Bibliotecas instaladas",
        False,
        f"Faltou instalar: {e.name}. Rode novamente o pip install do Passo 9.3.",
    )
    print("\nSem as bibliotecas nao da para continuar. Encerrando.")
    sys.exit(1)

# ---------------------------------------------------------------- 2/5
print("\n>> 2/5  Credenciais (application-default login)")
projeto = None
try:
    import google.auth

    credenciais, projeto = google.auth.default()
    if projeto:
        registrar("Credenciais encontradas", True, f"Projeto padrao: {projeto}")
    else:
        registrar(
            "Credenciais encontradas",
            False,
            "Autenticou, mas sem projeto padrao. Rode: gcloud config set project SEU-PROJECT-ID",
        )
except Exception as e:
    registrar(
        "Credenciais encontradas",
        False,
        f"{type(e).__name__}. Rode no CMD: gcloud auth application-default login",
    )

# ---------------------------------------------------------------- 3/5
print("\n>> 3/5  Acesso ao BigQuery")
try:
    cliente_bq = bigquery.Client()
    consulta = "SELECT 1 AS teste"
    config = bigquery.QueryJobConfig(maximum_bytes_billed=10_000_000)  # teto de 10 MB
    linhas = list(cliente_bq.query(consulta, job_config=config).result())
    datasets = list(cliente_bq.list_datasets())
    nomes = ", ".join(d.dataset_id for d in datasets) if datasets else "nenhum ainda (normal nesta etapa)"
    registrar(
        "BigQuery respondeu",
        linhas[0].teste == 1,
        f"Datasets no projeto: {nomes}",
    )
except Exception as e:
    registrar(
        "BigQuery respondeu",
        False,
        f"{type(e).__name__}: {str(e)[:180]}",
    )

# ---------------------------------------------------------------- 4/5
print("\n>> 4/5  Acesso ao Cloud Storage")
try:
    cliente_gcs = storage.Client()
    buckets = [b.name for b in cliente_gcs.list_buckets()]
    esperados_raw = [b for b in buckets if b.startswith("kenzie360-raw")]
    esperados_tf = [b for b in buckets if b.startswith("kenzie360-tfstate")]
    tudo_ok = bool(esperados_raw) and bool(esperados_tf)
    detalhe = f"Buckets visiveis: {', '.join(buckets) if buckets else 'nenhum'}"
    if not tudo_ok:
        detalhe += " | Faltou criar o bucket de RAW e/ou o de tfstate (Passo 7)."
    registrar("Cloud Storage respondeu", tudo_ok, detalhe)
except Exception as e:
    registrar(
        "Cloud Storage respondeu",
        False,
        f"{type(e).__name__}: {str(e)[:180]}",
    )

# ---------------------------------------------------------------- 5/5
print("\n>> 5/5  Base de dados local")
try:
    faltando = [a.name for a in (ARQ_ATENDIMENTOS, ARQ_MENSAGENS) if not a.exists()]
    if faltando:
        registrar(
            "CSVs encontrados na pasta",
            False,
            f"Nao achei: {', '.join(faltando)}. Confira a pasta 2_dados/.",
        )
    else:
        amostra = pd.read_csv(
            ARQ_ATENDIMENTOS, sep=";", encoding="utf-8-sig", nrows=5
        )
        mb_a = ARQ_ATENDIMENTOS.stat().st_size / 1_048_576
        mb_m = ARQ_MENSAGENS.stat().st_size / 1_048_576
        registrar(
            "CSVs encontrados na pasta",
            len(amostra.columns) == 30,
            f"atendimentos: {mb_a:.0f} MB, {len(amostra.columns)} colunas | mensagens: {mb_m:.0f} MB",
        )
except Exception as e:
    registrar(
        "CSVs encontrados na pasta",
        False,
        f"{type(e).__name__}: {str(e)[:180]}",
    )

# ---------------------------------------------------------------- resumo
print()
print("=" * 62)
aprovados = sum(1 for _, ok, _ in resultados if ok)
total = len(resultados)
print(f"  RESULTADO: {aprovados} de {total} checagens OK")
print("=" * 62)

if aprovados == total:
    print("""
  Fundacao pronta. Pode avisar no chat que a Trilha 0 fechou.
  Proximo passo: Trilha B - subir a base e criar as camadas.
""")
else:
    print("\n  Pendencias:\n")
    for nome, ok, detalhe in resultados:
        if not ok:
            print(f"   - {nome}: {detalhe}")
    print("\n  Me mande esta tela no chat que eu te ajudo a destravar.\n")
