-- =====================================================================
-- Projeto Kenzie 360 - Sprint 2
-- MODELAGEM DIMENSIONAL: STAR SCHEMA + WIDE TABLE
--
-- Atende ao entregavel "Modelagem de Dados" da disciplina:
--   . Star Schema  -> analise OLAP (fato + dimensoes conformes)
--   . Wide Table   -> machine learning e consultas rapidas
--
-- Grao da tabela fato: UM ATENDIMENTO (uma conversa completa).
-- Fonte: camada silver. Destino: camada gold.
--
-- Chaves substitutas (surrogate keys) via FARM_FINGERPRINT da chave
-- natural: deterministicas, estaveis entre recargas e sem necessidade
-- de sequence. dim_tempo usa a convencao AAAAMMDD como inteiro.
--
-- Toda dimensao tem um membro "(nao aplicavel)" com SK = 0, para que
-- nenhuma linha da fato fique orfa - regra basica de modelagem estrela.
-- =====================================================================


-- BLOCO: dim_tempo
-- Dimensao de calendario. Cobre todo o periodo da base, inclusive dias
-- sem atendimento (importante para series temporais nao terem buracos).
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.dim_tempo`
OPTIONS(description="Dimensao de calendario - um registro por dia do periodo")
AS
WITH limites AS (
  SELECT MIN(data_ref) AS ini, MAX(data_ref) AS fim
  FROM `@PROJETO.kenzie360_silver.atendimentos`
),
dias AS (
  SELECT d AS data_ref
  FROM limites, UNNEST(GENERATE_DATE_ARRAY(ini, fim)) AS d
)
SELECT
  CAST(FORMAT_DATE('%Y%m%d', data_ref) AS INT64)            AS sk_tempo,
  data_ref,
  EXTRACT(YEAR    FROM data_ref)                            AS ano,
  EXTRACT(QUARTER FROM data_ref)                            AS trimestre,
  EXTRACT(MONTH   FROM data_ref)                            AS mes,
  FORMAT_DATE('%B', data_ref)                               AS nome_mes,
  FORMAT_DATE('%Y-%m', data_ref)                            AS ano_mes,
  EXTRACT(DAY     FROM data_ref)                            AS dia,
  EXTRACT(DAYOFWEEK FROM data_ref)                          AS dia_semana_num,
  FORMAT_DATE('%A', data_ref)                               AS dia_semana,
  EXTRACT(ISOWEEK FROM data_ref)                            AS semana_ano,
  EXTRACT(DAYOFWEEK FROM data_ref) IN (1, 7)                AS is_fim_de_semana,
  -- janela de vencimento de fatura: concentra demanda de cartao
  EXTRACT(DAY FROM data_ref) BETWEEN 4 AND 10               AS is_janela_fatura
FROM dias;


-- BLOCO: dim_cliente
-- Um registro por cliente, com atributos de perfil e metricas de
-- relacionamento derivadas do historico.
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.dim_cliente`
OPTIONS(description="Dimensao de cliente - perfil e metricas de relacionamento")
AS
SELECT
  FARM_FINGERPRINT(id_cliente)                              AS sk_cliente,
  id_cliente,
  ANY_VALUE(segmento_cliente)                               AS segmento_cliente,
  ANY_VALUE(arquetipo)                                      AS arquetipo,
  ANY_VALUE(perfil_tecnologico)                             AS perfil_tecnologico,
  ANY_VALUE(faixa_etaria)                                   AS faixa_etaria,
  ANY_VALUE(idioma)                                         AS idioma,
  -- metricas de relacionamento
  COUNT(*)                                                  AS total_atendimentos,
  COUNT(*) > 1                                              AS is_recorrente,
  COUNTIF(reabertura)                                       AS total_reaberturas,
  MIN(data_ref)                                             AS data_primeiro_contato,
  MAX(data_ref)                                             AS data_ultimo_contato,
  DATE_DIFF(MAX(data_ref), MIN(data_ref), DAY)              AS dias_de_relacionamento,
  ROUND(AVG(csat), 2)                                       AS csat_medio,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 2)         AS pct_resolvido_bot,
  -- faixa de recorrencia, util para segmentar no dashboard
  CASE
    WHEN COUNT(*) = 1        THEN '1. Contato unico'
    WHEN COUNT(*) <= 3       THEN '2. Ate 3 contatos'
    WHEN COUNT(*) <= 6       THEN '3. De 4 a 6 contatos'
    ELSE                          '4. Mais de 6 contatos'
  END                                                       AS faixa_recorrencia
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY id_cliente

UNION ALL
-- membro "nao aplicavel" (SK = 0): garante que nenhuma linha da fato fique orfa.
-- Os NULL precisam de CAST explicito - em UNION ALL o BigQuery nao infere o tipo.
SELECT 0, '(nao aplicavel)', '(nao aplicavel)', '(nao aplicavel)', '(nao aplicavel)',
       '(nao aplicavel)', '(nao aplicavel)', 0, FALSE, 0,
       CAST(NULL AS DATE), CAST(NULL AS DATE), CAST(NULL AS INT64),
       CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64), '(nao aplicavel)';


-- BLOCO: dim_assunto
-- Dimensao de assunto com a classificacao por TIPO DE ACAO exigida, que
-- foi o corte que revelou a causa do problema na analise exploratoria.
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.dim_assunto`
OPTIONS(description="Dimensao de assunto - categoria, produto e tipo de demanda")
AS
WITH combinacoes AS (
  SELECT DISTINCT
    categoria_assunto,
    COALESCE(produto_relacionado, '(sem produto)')          AS produto_relacionado
  FROM `@PROJETO.kenzie360_silver.atendimentos`
)
SELECT
  FARM_FINGERPRINT(CONCAT(categoria_assunto, '|', produto_relacionado)) AS sk_assunto,
  categoria_assunto,
  produto_relacionado,
  CASE categoria_assunto
    WHEN 'Saldo e Extrato'                    THEN 'Informacional'
    WHEN 'Investimentos CDB'                  THEN 'Informacional'
    WHEN 'Termos e Documentacao BR'           THEN 'Informacional'
    WHEN 'Cartao de Credito'                  THEN 'Misto'
    WHEN 'Primeiro Acesso'                    THEN 'Misto'
    WHEN 'Alteracao de Limites'               THEN 'Transacional'
    WHEN 'Cambio'                             THEN 'Transacional'
    WHEN 'Onboarding - Documentacao'          THEN 'Transacional'
    WHEN 'Bloqueio TED/PIX'                   THEN 'Transacional'
    WHEN 'Operacoes PJ - Folha e Pagamentos'  THEN 'Transacional'
    ELSE 'Nao atendimento'
  END                                                       AS tipo_demanda,
  CASE categoria_assunto
    WHEN 'Saldo e Extrato'                    THEN 1
    WHEN 'Investimentos CDB'                  THEN 1
    WHEN 'Termos e Documentacao BR'           THEN 1
    WHEN 'Cartao de Credito'                  THEN 2
    WHEN 'Primeiro Acesso'                    THEN 2
    ELSE CASE WHEN categoria_assunto IN ('Disparo Ativo','Ruido / Nao-atendimento')
              THEN 4 ELSE 3 END
  END                                                       AS ordem_tipo_demanda,
  -- area que costuma receber o caso quando escala
  CASE categoria_assunto
    WHEN 'Onboarding - Documentacao'          THEN 'Cadastro/Onboarding'
    WHEN 'Termos e Documentacao BR'           THEN 'Cadastro/Onboarding'
    WHEN 'Bloqueio TED/PIX'                   THEN 'Prevencao a Fraude'
    WHEN 'Cambio'                             THEN 'Cambio/Backoffice'
    WHEN 'Primeiro Acesso'                    THEN 'Suporte Tecnico'
    WHEN 'Alteracao de Limites'               THEN 'Mesa de Limites'
    WHEN 'Cartao de Credito'                  THEN 'Cartoes'
    WHEN 'Investimentos CDB'                  THEN 'Investimentos'
    WHEN 'Saldo e Extrato'                    THEN 'Backoffice'
    WHEN 'Operacoes PJ - Folha e Pagamentos'  THEN 'Atendimento PJ'
    ELSE '(nao se aplica)'
  END                                                       AS area_padrao
FROM combinacoes

UNION ALL
SELECT 0, '(nao aplicavel)', '(nao aplicavel)', '(nao aplicavel)', 9, '(nao aplicavel)';


-- BLOCO: dim_canal
-- Canal de entrada, canal do atendimento humano e origem do contato.
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.dim_canal`
OPTIONS(description="Dimensao de canal - entrada, canal humano e origem")
AS
WITH combinacoes AS (
  SELECT DISTINCT
    canal_entrada,
    COALESCE(canal_humano, '(sem atendimento humano)')      AS canal_humano,
    origem_contato
  FROM `@PROJETO.kenzie360_silver.atendimentos`
)
SELECT
  FARM_FINGERPRINT(CONCAT(canal_entrada, '|', canal_humano, '|', origem_contato)) AS sk_canal,
  canal_entrada,
  canal_humano,
  origem_contato,
  origem_contato = 'Ativo'                                  AS is_disparo_ativo,
  canal_humano != '(sem atendimento humano)'                AS teve_canal_humano
FROM combinacoes

UNION ALL
SELECT 0, '(nao aplicavel)', '(nao aplicavel)', '(nao aplicavel)', FALSE, FALSE;


-- BLOCO: dim_desfecho
-- Desfecho do atendimento, agrupado no cluster de satisfacao. A analise
-- mostrou que o CSAT e bimodal, entao o cluster e atributo de primeira
-- classe, nao um calculo feito na hora da consulta.
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.dim_desfecho`
OPTIONS(description="Dimensao de desfecho - status, cluster de satisfacao e resolucao")
AS
WITH combinacoes AS (
  SELECT DISTINCT status_conversa, resolucao_declarada
  FROM `@PROJETO.kenzie360_silver.atendimentos`
)
SELECT
  FARM_FINGERPRINT(CONCAT(status_conversa, '|', resolucao_declarada)) AS sk_desfecho,
  status_conversa,
  resolucao_declarada,
  CASE
    WHEN status_conversa IN ('Resolvida pelo bot', 'Resolvida por humano')
         THEN '1. Resolvido'
    WHEN status_conversa IN ('Abandonada pelo cliente', 'Encerrada sem resolucao',
                             'Transferida - sem resolucao')
         THEN '2. Falha'
    ELSE '3. Nao atendimento'
  END                                                       AS cluster_satisfacao,
  status_conversa IN ('Resolvida pelo bot', 'Resolvida por humano') AS is_resolvido,
  status_conversa = 'Resolvida pelo bot'                    AS is_resolvido_por_bot,
  -- modo de falha, quando houver
  CASE
    WHEN status_conversa = 'Transferida - sem resolucao'
         THEN 'Roteado e nao resolvido'
    WHEN status_conversa IN ('Abandonada pelo cliente', 'Encerrada sem resolucao')
         THEN 'Nao resolvido no atendimento'
    ELSE '(sem falha)'
  END                                                       AS modo_de_falha
FROM combinacoes

UNION ALL
SELECT 0, '(nao aplicavel)', '(nao aplicavel)', '(nao aplicavel)', FALSE, FALSE, '(sem falha)';


-- BLOCO: dim_motivo_transferencia
-- Motivo e area de encaminhamento. O membro "(nao classificado)" e
-- relevante por si: 55,2% das transferencias saem sem motivo, e e delas
-- que vem a fila abandonada.
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.dim_motivo_transferencia`
OPTIONS(description="Dimensao de motivo de transferencia e area de encaminhamento")
AS
WITH combinacoes AS (
  SELECT DISTINCT
    COALESCE(motivo_transferencia, '(nao classificado)')     AS motivo_transferencia,
    COALESCE(area_encaminhada,     '(sem area)')             AS area_encaminhada
  FROM `@PROJETO.kenzie360_silver.atendimentos`
  WHERE transferencia_iniciada
)
SELECT
  FARM_FINGERPRINT(CONCAT(motivo_transferencia, '|', area_encaminhada)) AS sk_motivo,
  motivo_transferencia,
  area_encaminhada,
  motivo_transferencia = '(nao classificado)'               AS is_nao_classificado,
  -- natureza da limitacao que gerou a transferencia
  CASE motivo_transferencia
    WHEN 'Necessita acao em sistema interno' THEN 'Falta de permissao transacional'
    WHEN 'Fora do escopo do bot'             THEN 'Falta de cobertura do script'
    WHEN 'Analise manual/documental'         THEN 'Exige julgamento humano'
    WHEN 'Validacao de seguranca'            THEN 'Exige julgamento humano'
    WHEN 'Excecao de regra de negocio'       THEN 'Exige julgamento humano'
    ELSE '(nao classificado)'
  END                                                       AS natureza_limitacao
FROM combinacoes

UNION ALL
SELECT 0, '(nao aplicavel)', '(nao aplicavel)', FALSE, '(nao aplicavel)';


-- BLOCO: fato_atendimento
-- Tabela fato. Grao: um atendimento. Particionada por data e clusterizada
-- pelas chaves mais usadas em filtro.
CREATE OR REPLACE TABLE `@PROJETO.kenzie360_gold.fato_atendimento`
PARTITION BY data_ref
CLUSTER BY sk_assunto, sk_cliente, sk_desfecho
OPTIONS(description="Tabela fato - grao de um atendimento. Star Schema para analise OLAP")
AS
SELECT
  -- ---------- dimensao degenerada
  a.id_conversa,

  -- ---------- chaves estrangeiras
  CAST(FORMAT_DATE('%Y%m%d', a.data_ref) AS INT64)          AS sk_tempo,
  FARM_FINGERPRINT(a.id_cliente)                            AS sk_cliente,
  FARM_FINGERPRINT(CONCAT(a.categoria_assunto, '|',
       COALESCE(a.produto_relacionado, '(sem produto)')))   AS sk_assunto,
  FARM_FINGERPRINT(CONCAT(a.canal_entrada, '|',
       COALESCE(a.canal_humano, '(sem atendimento humano)'), '|',
       a.origem_contato))                                   AS sk_canal,
  FARM_FINGERPRINT(CONCAT(a.status_conversa, '|',
       a.resolucao_declarada))                              AS sk_desfecho,
  CASE WHEN a.transferencia_iniciada
       THEN FARM_FINGERPRINT(CONCAT(
              COALESCE(a.motivo_transferencia, '(nao classificado)'), '|',
              COALESCE(a.area_encaminhada, '(sem area)')))
       ELSE 0 END                                           AS sk_motivo,

  -- ---------- coluna de particao (redundante com sk_tempo, por desempenho)
  a.data_ref,
  a.data_hora,

  -- ---------- metricas aditivas
  1                                                         AS qtd_atendimentos,
  a.num_mensagens,
  a.num_mensagens_cliente,
  a.duracao_seg,
  a.duracao_min,
  a.qtd_dados_mascarados,
  a.contatos_previos,

  -- ---------- metricas semi-aditivas
  a.csat,

  -- ---------- flags (somaveis com COUNTIF / SUM de CAST)
  a.resolvido_bot,
  a.transferencia_iniciada,
  a.humano_atendeu,
  a.reabertura,
  a.transferencia_iniciada AND NOT a.humano_atendeu         AS fila_abandonada,
  a.status_conversa = 'Transferida - sem resolucao'         AS atendeu_e_nao_resolveu,

  -- ---------- atributos de contexto mantidos na fato por conveniencia
  a.sentimento_geral,

  -- ---------- horas de atendimento humano, para o calculo de custo
  IF(a.humano_atendeu, a.duracao_min, 0)                    AS min_humano
FROM `@PROJETO.kenzie360_silver.atendimentos` a;


-- BLOCO: vw_wide_atendimento
-- WIDE TABLE: o star schema ja desnormalizado numa unica linha por
-- atendimento. Atende ao entregavel "Wide Table para machine learning e
-- consultas rapidas" - dispensa join para quem for treinar modelo ou
-- fazer exploracao rapida.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_wide_atendimento`
OPTIONS(description="Wide Table - uma linha por atendimento com todas as dimensoes resolvidas")
AS
SELECT
  f.id_conversa,
  -- tempo
  t.data_ref, t.ano, t.trimestre, t.mes, t.ano_mes, t.dia_semana,
  t.semana_ano, t.is_fim_de_semana, t.is_janela_fatura,
  EXTRACT(HOUR FROM f.data_hora)                            AS hora_do_dia,
  -- cliente
  c.id_cliente, c.segmento_cliente, c.arquetipo, c.perfil_tecnologico,
  c.faixa_etaria, c.idioma, c.total_atendimentos, c.is_recorrente,
  c.faixa_recorrencia, c.dias_de_relacionamento,
  -- assunto
  s.categoria_assunto, s.produto_relacionado, s.tipo_demanda,
  s.ordem_tipo_demanda, s.area_padrao,
  -- canal
  ca.canal_entrada, ca.canal_humano, ca.origem_contato, ca.is_disparo_ativo,
  -- desfecho
  d.status_conversa, d.resolucao_declarada, d.cluster_satisfacao,
  d.is_resolvido, d.is_resolvido_por_bot, d.modo_de_falha,
  -- motivo de transferencia
  m.motivo_transferencia, m.area_encaminhada, m.is_nao_classificado,
  m.natureza_limitacao,
  -- metricas
  f.num_mensagens, f.num_mensagens_cliente, f.duracao_seg, f.duracao_min,
  f.csat, f.qtd_dados_mascarados, f.contatos_previos, f.min_humano,
  -- flags
  f.resolvido_bot, f.transferencia_iniciada, f.humano_atendeu, f.reabertura,
  f.fila_abandonada, f.atendeu_e_nao_resolveu, f.sentimento_geral
FROM `@PROJETO.kenzie360_gold.fato_atendimento` f
LEFT JOIN `@PROJETO.kenzie360_gold.dim_tempo`    t  ON f.sk_tempo    = t.sk_tempo
LEFT JOIN `@PROJETO.kenzie360_gold.dim_cliente`  c  ON f.sk_cliente  = c.sk_cliente
LEFT JOIN `@PROJETO.kenzie360_gold.dim_assunto`  s  ON f.sk_assunto  = s.sk_assunto
LEFT JOIN `@PROJETO.kenzie360_gold.dim_canal`    ca ON f.sk_canal    = ca.sk_canal
LEFT JOIN `@PROJETO.kenzie360_gold.dim_desfecho` d  ON f.sk_desfecho = d.sk_desfecho
LEFT JOIN `@PROJETO.kenzie360_gold.dim_motivo_transferencia` m ON f.sk_motivo = m.sk_motivo;
