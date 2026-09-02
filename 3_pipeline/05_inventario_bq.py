# -*- coding: utf-8 -*-
"""
Projeto Kenzie 360 - Sprint 2
Inventario do BigQuery: o que existe, quantas linhas, quanto ocupa e quanto custa.

    kenzie
    python3 05_inventario_bq.py

So le metadados - nao consulta dados, entao nao consome franquia de query.
"""

from google.cloud import bigquery
import config_kenzie as cfg

FREE_STORAGE_GIB = 10.0

cliente = bigquery.Client(project=cfg.PROJETO)

print()
print("=" * 74)
print(f"  INVENTARIO DO BIGQUERY - {cfg.PROJETO}")
print("=" * 74)

total_bytes = 0
total_linhas = 0
achados = []

for ds in (cfg.DS_BRONZE, cfg.DS_SILVER, cfg.DS_GOLD):
    try:
        tabelas = list(cliente.list_tables(f"{cfg.PROJETO}.{ds}"))
    except Exception as e:
        print(f"\n  [{ds}] nao acessivel: {type(e).__name__}")
        continue

    print(f"\n  [{ds}]")
    if not tabelas:
        print("     (vazio)")
        continue

    print(f"     {'tabela':<26}{'linhas':>12}{'tamanho':>12}  {'tipo':<8}")
    print("     " + "-" * 60)
    for t in sorted(tabelas, key=lambda x: x.table_id):
        info = cliente.get_table(t.reference)
        mb = (info.num_bytes or 0) / 1_048_576
        total_bytes += info.num_bytes or 0
        total_linhas += info.num_rows or 0
        tipo = "VIEW" if info.table_type == "VIEW" else "tabela"
        versao = "v7" if t.table_id.endswith("_v7") else "v8"
        print(f"     {t.table_id:<26}{info.num_rows or 0:>12,}{mb:>10.1f} MB  {tipo:<8} {versao}"
              .replace(",", "."))
        achados.append((ds, t.table_id, info.num_rows or 0))

# ------------------------------------------------------------------ resumo
gib = total_bytes / 1_073_741_824
print()
print("=" * 74)
print(f"  TOTAL: {total_linhas:,} linhas | {total_bytes/1_048_576:.0f} MB "
      f"({gib:.3f} GiB)".replace(",", "."))
print(f"  Franquia gratuita de armazenamento: {FREE_STORAGE_GIB:.0f} GiB/mes "
      f"-> usando {100*gib/FREE_STORAGE_GIB:.2f}%")
print("=" * 74)

# ------------------------------------------------------------------ checagem
print("\n  CHECAGEM DE DUPLICACAO")
esperado = {
    ("kenzie360_bronze", "atendimentos"): cfg.TOTAL_ATENDIMENTOS,
    ("kenzie360_bronze", "mensagens"): cfg.TOTAL_MENSAGENS,
    ("kenzie360_silver", "atendimentos"): cfg.TOTAL_ATENDIMENTOS,
    ("kenzie360_silver", "mensagens"): cfg.TOTAL_MENSAGENS,
}
problemas = []
for (ds, tab), n_esp in esperado.items():
    real = next((n for d, t, n in achados if d == ds and t == tab), None)
    if real is None:
        print(f"     [--] {ds}.{tab} nao encontrada")
        continue
    if real == n_esp:
        print(f"     [OK] {ds}.{tab:<14} {real:>9,} linhas  (esperado)".replace(",", "."))
    else:
        print(f"     [!!] {ds}.{tab:<14} {real:>9,} linhas  (esperado {n_esp:,})".replace(",", "."))
        problemas.append(f"{ds}.{tab}")

if problemas:
    print(f"\n  [ATENCAO] Divergencia em: {', '.join(problemas)}")
    print("  Cole esta tela no chat.\n")
else:
    print(f"""
  Nenhuma duplicacao. As tabelas da v8 tem exatamente o numero de linhas
  do arquivo de origem. As tabelas _v7 sao o snapshot da base anterior.

  Para consultar a versao antiga:
    SELECT COUNT(*) FROM `{cfg.PROJETO}.{cfg.DS_SILVER}.atendimentos_v7`

  Para remover o snapshot quando nao precisar mais (opcional):
    bq rm -f -t {cfg.PROJETO}:{cfg.DS_BRONZE}.atendimentos_v7
    bq rm -f -t {cfg.PROJETO}:{cfg.DS_BRONZE}.mensagens_v7
    bq rm -f -t {cfg.PROJETO}:{cfg.DS_SILVER}.atendimentos_v7
    bq rm -f -t {cfg.PROJETO}:{cfg.DS_SILVER}.mensagens_v7
""")
