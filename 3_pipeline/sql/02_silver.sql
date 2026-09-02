-- =====================================================================
-- Projeto Kenzie 360 - Sprint 2 - Trilha B
-- CAMADA SILVER (TRUSTED)
--
-- Regras desta camada:
--   1. Tipos corretos (a bronze e toda STRING)
--   2. Deduplicacao por chave de negocio
--   3. Strings vazias viram NULL de verdade
--   4. Particionamento por data + clustering pelos filtros mais usados
--   5. Mascaramento defensivo de PII no texto livre
--
-- O marcador "-- BLOCO:" separa os comandos. Nao remova.
-- O placeholder @PROJETO e substituido pelo script 02_cria_silver.py.
-- =====================================================================


-- BLOCO: atendimentos
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_silver.atendimentos`
PARTITION BY data_ref
CLUSTER BY segmento_cliente, categoria_assunto, idioma
OPTIONS(
  description = "TRUSTED - 1 linha por atendimento. Tipado, deduplicado por id_conversa, particionado por data."
)
AS
WITH bronze_dedup AS (
  SELECT
    *,
    -- Se o mesmo id_conversa aparecer duas vezes, fica a ingestao mais recente
    ROW_NUMBER() OVER (PARTITION BY id_conversa ORDER BY _ingestion_ts DESC) AS _rn
  FROM `@PROJETO.kenzie360_bronze.atendimentos`
)
SELECT
  -- ---------- identificacao
  id_conversa,
  id_cliente,

  -- ---------- perfil do cliente
  segmento_cliente,
  arquetipo,
  perfil_tecnologico,
  faixa_etaria,
  idioma,

  -- ---------- tempo
  -- SAFE.PARSE_DATETIME devolve NULL em vez de quebrar se o formato variar.
  -- Preferimos DATETIME a TIMESTAMP: a origem nao declara fuso horario, e
  -- converter para UTC seria inventar informacao que o dado nao tem.
  SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', data_hora)              AS data_hora,
  DATE(SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', data_hora))        AS data_ref,

  -- ---------- canal e assunto
  origem                                                            AS origem_contato,
  canal_entrada,
  NULLIF(TRIM(canal_humano), '')                                    AS canal_humano,
  categoria_assunto,
  produto_relacionado,
  NULLIF(TRIM(primeira_mensagem_cliente), '')                       AS primeira_mensagem_cliente,

  -- ---------- desfecho
  sentimento_geral,
  resolvido_bot = 'True'                                            AS resolvido_bot,
  transferencia_iniciada = 'True'                                   AS transferencia_iniciada,
  humano_atendeu = 'True'                                           AS humano_atendeu,
  status_conversa,
  -- ATENCAO: "resolvida" NAO e booleano. Tem 4 valores:
  -- Sim / Nao / Desconhecido / Nao aplicavel. Fica STRING de proposito.
  resolvida                                                         AS resolucao_declarada,
  NULLIF(TRIM(area_encaminhada), '')                                AS area_encaminhada,
  NULLIF(TRIM(motivo_transferencia), '')                            AS motivo_transferencia,

  -- ---------- metricas
  SAFE_CAST(num_mensagens AS INT64)                                 AS num_mensagens,
  SAFE_CAST(num_mensagens_cliente AS INT64)                         AS num_mensagens_cliente,
  SAFE_CAST(duracao_seg AS INT64)                                   AS duracao_seg,
  ROUND(SAFE_CAST(duracao_seg AS INT64) / 60, 2)                    AS duracao_min,
  -- csat vem gravado como "5.0", entao passa por FLOAT64 antes de virar INT64.
  -- 62% das conversas nao tem csat (a pesquisa so e respondida por ~30%): fica NULL.
  SAFE_CAST(SAFE_CAST(NULLIF(csat, '') AS FLOAT64) AS INT64)        AS csat,
  SAFE_CAST(qtd_dados_mascarados AS INT64)                          AS qtd_dados_mascarados,
  SAFE_CAST(contatos_previos AS INT64)                              AS contatos_previos,
  reabertura = 'True'                                               AS reabertura,

  -- ---------- texto
  NULLIF(TRIM(transcricao_completa), '')                            AS transcricao_completa,

  -- ---------- rastreabilidade herdada da bronze
  _ingestion_ts,
  _source_file
FROM bronze_dedup
WHERE _rn = 1;


-- BLOCO: mensagens
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_silver.mensagens`
PARTITION BY data_ref
CLUSTER BY id_conversa, remetente
OPTIONS(
  description = "TRUSTED - 1 linha por turno de conversa. Deduplicado por (id_conversa, ordem). PII mascarada."
)
AS
WITH bronze_dedup AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY id_conversa, ordem ORDER BY _ingestion_ts DESC
    ) AS _rn
  FROM `@PROJETO.kenzie360_bronze.mensagens`
),
mascarado AS (
  SELECT
    *,
    -- Mascaramento defensivo. A base ja nasce mascarada por construcao, mas a
    -- regra fica implementada aqui porque em producao a origem nao e confiavel.
    -- Aplicamos so e-mail e CPF: sao padroes de baixo falso-positivo. Telefone
    -- ficou de fora de proposito - o padrao colide com valores e protocolos.
    REGEXP_REPLACE(
      REGEXP_REPLACE(
        texto,
        r'[\w\.\-\+]+@[\w\-]+\.[\w\.\-]+', '[EMAIL]'
      ),
      r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', '[CPF]'
    ) AS texto_tratado
  FROM bronze_dedup
  WHERE _rn = 1
)
SELECT
  id_conversa,
  id_cliente,
  segmento_cliente,
  idioma,
  categoria_assunto,
  SAFE_CAST(ordem AS INT64)                                         AS ordem,
  SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', timestamp)               AS momento,
  DATE(SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', timestamp))         AS data_ref,
  remetente,
  texto_tratado                                                     AS texto,
  -- Auditoria: marca as linhas em que a regra de mascaramento agiu de fato.
  texto_tratado != texto                                            AS pii_remascarada,
  -- Sentimento so existe nas falas do Cliente. Nas do bot e do humano vem vazio,
  -- e vazio aqui significa "nao se aplica", nao "faltou dado".
  NULLIF(TRIM(sentimento), '')                                      AS sentimento,
  tipo_midia,
  contem_dado_mascarado = 'True'                                    AS contem_dado_mascarado,
  _ingestion_ts,
  _source_file
FROM mascarado;
