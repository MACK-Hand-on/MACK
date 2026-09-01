# 2_dados — a base sintética

## O que está versionado aqui

| Caminho | Conteúdo |
|---|---|
| `atual_v8/dataset_kenzie360_atendimentos_v8.csv.gz` | 36.000 conversas × 30 colunas |
| `atual_v8/dataset_kenzie360_mensagens_v8.csv.gz` | 405.073 mensagens × 12 colunas |
| `amostras/AMOSTRA_conversas.csv` | 30 conversas, para inspeção rápida sem descompactar |
| `amostras/AMOSTRA_mensagens.csv` | 225 mensagens |

Os CSVs descompactados somam 101 MB e são **derivados** — estão no `.gitignore`.

## Para usar a base

```bash
cd 2_dados/atual_v8
gzip -dk dataset_kenzie360_atendimentos_v8.csv.gz
gzip -dk dataset_kenzie360_mensagens_v8.csv.gz
```

No Windows sem `gzip`: clique com o botão direito no arquivo e extraia com 7-Zip ou WinRAR, deixando o `.csv` na mesma pasta.

Os scripts de `3_pipeline/` esperam os arquivos exatamente nesse caminho — é o que `config_kenzie.py` resolve.

## Formato

Separador `;` · encoding UTF-8 com BOM.

```python
pd.read_csv(arquivo, sep=";", encoding="utf-8-sig")
```

**Atenção:** 4.361 linhas de atendimentos e 4.842 de mensagens contêm ponto e vírgula **dentro** de campos de texto, protegidos por aspas duplas. Qualquer leitor de CSV que respeite aspas lê corretamente — não usar `split(";")`.

## Para regerar do zero

```bash
cd 4_gerador_da_base
python3 gerar_dataset_cde_v8.py
```

O gerador é determinístico (`SEED = 42`): reproduz exatamente os mesmos arquivos, byte a byte.

SHA-256 dos CSVs descompactados:

```
183587592d771a8996e6de6ac0658a3c4c14f92bd1ac966af1ebd4ece3545342  dataset_kenzie360_atendimentos_v8.csv
70ae0b4a13f385e92c493d1212f1888b47f947a601f7fd0155e0a859145daf41  dataset_kenzie360_mensagens_v8.csv
```

## Sobre a origem

Base **100% sintética**, construída como gêmeo estatístico da operação real e calibrada por indicadores agregados. Nenhum dado pessoal de cliente foi utilizado em nenhuma etapa.

A `historico_v7/` — a base da Sprint 1, antes da recalibração — não é versionada. Quem precisar dela roda `gerar_dataset_cde.py` (o gerador v7, também determinístico), preservado em `4_gerador_da_base/`.
