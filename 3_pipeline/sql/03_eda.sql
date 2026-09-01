-- =====================================================================
-- Projeto Kenzie 360 - Sprint 2 - Trilha A
-- ANALISE EXPLORATORIA sobre a camada SILVER
--
-- Cada consulta responde uma pergunta de negocio e e candidata a virar
-- uma view da camada GOLD. O marcador "-- CONSULTA:" separa os comandos.
-- O placeholder @PROJETO e trocado pelo script 03_eda.py.
-- =====================================================================


-- CONSULTA: a1_perfil_base
-- Bloco A1 - retrato geral da base. Serve de capa do relatorio.
SELECT
  COUNT(*)                                                  AS conversas,
  COUNT(DISTINCT id_cliente)                                AS clientes,
  MIN(data_ref)                                             AS primeira_data,
  MAX(data_ref)                                             AS ultima_data,
  DATE_DIFF(MAX(data_ref), MIN(data_ref), DAY) + 1          AS dias_periodo,
  ROUND(COUNT(*) / (DATE_DIFF(MAX(data_ref), MIN(data_ref), DAY) + 1), 1) AS conversas_por_dia,
  ROUND(AVG(num_mensagens), 1)                              AS media_mensagens,
  ROUND(AVG(duracao_min), 1)                                AS media_duracao_min,
  ROUND(AVG(csat), 2)                                       AS csat_medio,
  COUNTIF(csat IS NOT NULL)                                 AS respostas_csat,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)         AS pct_resolvido_bot,
  ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 1) AS pct_transferencia,
  ROUND(100 * COUNTIF(humano_atendeu) / COUNT(*), 1)        AS pct_humano_atendeu,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 1)            AS pct_reabertura
FROM `@PROJETO.kenzie360_silver.atendimentos`;


-- CONSULTA: a2_volumetria_diaria
-- Bloco A2 - serie temporal. Detecta tendencia e picos.
SELECT
  data_ref,
  FORMAT_DATE('%A', data_ref)                               AS dia_semana,
  COUNT(*)                                                  AS conversas,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)         AS pct_resolvido_bot,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo,
  ROUND(AVG(csat), 2)                                       AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY data_ref
ORDER BY data_ref;


-- CONSULTA: a2_volumetria_hora_semana
-- Bloco A2 - onde estao os picos dentro da semana e do dia.
SELECT
  EXTRACT(DAYOFWEEK FROM data_hora)                         AS dia_semana_num,
  FORMAT_DATE('%A', data_ref)                               AS dia_semana,
  EXTRACT(HOUR FROM data_hora)                              AS hora,
  COUNT(*)                                                  AS conversas,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)         AS pct_resolvido_bot,
  ROUND(100 * COUNTIF(transferencia_iniciada AND NOT humano_atendeu) / COUNT(*), 1) AS pct_fila_abandonada
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY dia_semana_num, dia_semana, hora
ORDER BY dia_semana_num, hora;


-- CONSULTA: a3_dores_categoria
-- Bloco A3 - o mapa de dores. Volume e insatisfacao nao andam juntos:
-- e essa diferenca que aponta onde investir.
SELECT
  categoria_assunto,
  COUNT(*)                                                  AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)          AS pct_do_total,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)         AS pct_resolvido_bot,
  ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 1) AS pct_transferencia,
  ROUND(AVG(csat), 2)                                       AS csat_medio,
  ROUND(AVG(duracao_min), 1)                                AS duracao_media_min,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 1)            AS pct_reabertura
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY categoria_assunto
ORDER BY conversas DESC;


-- CONSULTA: a3_dores_produto_segmento
-- Bloco A3 - o cruzamento que mostra qual produto dói para qual publico.
SELECT
  segmento_cliente,
  produto_relacionado,
  COUNT(*)                                                  AS conversas,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)         AS pct_resolvido_bot,
  ROUND(AVG(csat), 2)                                       AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY segmento_cliente, produto_relacionado
HAVING conversas >= 50
ORDER BY segmento_cliente, conversas DESC;


-- CONSULTA: a4_performance_bot
-- Bloco A4 - onde a Kenzie ganha e onde ela apanha, por assunto e canal.
SELECT
  categoria_assunto,
  canal_entrada,
  COUNT(*)                                                  AS conversas,
  COUNTIF(resolvido_bot)                                    AS resolvidas_bot,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)         AS pct_resolvido_bot,
  ROUND(AVG(IF(resolvido_bot, csat, NULL)), 2)              AS csat_quando_bot_resolve,
  ROUND(AVG(IF(NOT resolvido_bot, csat, NULL)), 2)          AS csat_quando_nao_resolve,
  ROUND(AVG(num_mensagens), 1)                              AS media_turnos
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY categoria_assunto, canal_entrada
HAVING conversas >= 50
ORDER BY conversas DESC;


-- CONSULTA: a5_funil_transferencia
-- Bloco A5 - o funil e a fila abandonada, o vazamento mais caro da operacao.
SELECT
  ' 1. Total de conversas'                                  AS etapa,
  COUNT(*)                                                  AS conversas,
  ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM `@PROJETO.kenzie360_silver.atendimentos`), 1) AS pct
FROM `@PROJETO.kenzie360_silver.atendimentos`
UNION ALL
SELECT ' 2. Resolvidas pelo bot', COUNTIF(resolvido_bot),
       ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)
FROM `@PROJETO.kenzie360_silver.atendimentos`
UNION ALL
SELECT ' 3. Transferencia iniciada', COUNTIF(transferencia_iniciada),
       ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 1)
FROM `@PROJETO.kenzie360_silver.atendimentos`
UNION ALL
SELECT ' 4. Humano atendeu', COUNTIF(humano_atendeu),
       ROUND(100 * COUNTIF(humano_atendeu) / COUNT(*), 1)
FROM `@PROJETO.kenzie360_silver.atendimentos`
UNION ALL
SELECT ' 5. FILA ABANDONADA (pediu humano e nao foi atendido)',
       COUNTIF(transferencia_iniciada AND NOT humano_atendeu),
       ROUND(100 * COUNTIF(transferencia_iniciada AND NOT humano_atendeu) / COUNT(*), 1)
FROM `@PROJETO.kenzie360_silver.atendimentos`
ORDER BY etapa;


-- CONSULTA: a5_motivos_transferencia
-- Bloco A5 - por que a Kenzie desiste, e o que acontece depois.
SELECT
  COALESCE(motivo_transferencia, '(sem motivo registrado)')  AS motivo,
  COALESCE(area_encaminhada, '(sem area)')                   AS area,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNTIF(humano_atendeu) / COUNT(*), 1)         AS pct_atendido,
  ROUND(AVG(csat), 2)                                        AS csat_medio,
  ROUND(AVG(duracao_min), 1)                                 AS duracao_media_min
FROM `@PROJETO.kenzie360_silver.atendimentos`
WHERE transferencia_iniciada
GROUP BY motivo, area
ORDER BY conversas DESC;


-- CONSULTA: a6_jornada_sentimento
-- Bloco A6 - o diferencial da nossa base: como o humor do cliente evolui
-- DENTRO da conversa. Divide cada conversa em 5 partes iguais.
WITH falas_cliente AS (
  SELECT
    id_conversa,
    ordem,
    sentimento,
    MAX(ordem) OVER (PARTITION BY id_conversa) AS ultimo_turno
  FROM `@PROJETO.kenzie360_silver.mensagens`
  WHERE remetente = 'Cliente' AND sentimento IS NOT NULL
),
com_quinto AS (
  SELECT
    sentimento,
    CASE
      WHEN ultimo_turno <= 1 THEN 1
      ELSE LEAST(5, GREATEST(1,
        CAST(CEIL(5 * SAFE_DIVIDE(ordem, ultimo_turno)) AS INT64)))
    END AS quinto_da_conversa
  FROM falas_cliente
)
SELECT
  quinto_da_conversa,
  COUNT(*)                                                   AS falas,
  ROUND(100 * COUNTIF(sentimento = 'Positivo') / COUNT(*), 1) AS pct_positivo,
  ROUND(100 * COUNTIF(sentimento = 'Neutro')   / COUNT(*), 1) AS pct_neutro,
  ROUND(100 * COUNTIF(sentimento = 'Negativo') / COUNT(*), 1) AS pct_negativo
FROM com_quinto
GROUP BY quinto_da_conversa
ORDER BY quinto_da_conversa;


-- CONSULTA: a6_sentimento_por_desfecho
-- Bloco A6 - o sentimento da PRIMEIRA fala prediz o desfecho?
-- Esta consulta e candidata direta a feature do modelo da Fase 4.
WITH primeira_fala AS (
  SELECT id_conversa, sentimento AS sentimento_inicial
  FROM `@PROJETO.kenzie360_silver.mensagens`
  WHERE remetente = 'Cliente' AND sentimento IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY id_conversa ORDER BY ordem) = 1
)
SELECT
  p.sentimento_inicial,
  a.status_conversa,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY p.sentimento_inicial), 1) AS pct_dentro_do_sentimento,
  ROUND(AVG(a.csat), 2)                                      AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos` a
JOIN primeira_fala p USING (id_conversa)
GROUP BY p.sentimento_inicial, a.status_conversa
ORDER BY p.sentimento_inicial, conversas DESC;


-- CONSULTA: a7_recorrencia
-- Bloco A7 - quem volta, quantas vezes, e com que humor.
SELECT
  LEAST(contatos_previos, 5)                                 AS contatos_previos_faixa,
  COUNT(*)                                                   AS conversas,
  COUNT(DISTINCT id_cliente)                                 AS clientes,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 1)             AS pct_reabertura,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)          AS pct_resolvido_bot,
  ROUND(AVG(csat), 2)                                        AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY contatos_previos_faixa
ORDER BY contatos_previos_faixa;


-- CONSULTA: a8_barreira_idioma
-- Bloco A8 - a hipotese central do publico CDE: a Kenzie atende pior
-- em ingles e espanhol?
SELECT
  idioma,
  segmento_cliente,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)          AS pct_resolvido_bot,
  ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 1) AS pct_transferencia,
  ROUND(100 * COUNTIF(transferencia_iniciada AND NOT humano_atendeu) / COUNT(*), 1) AS pct_fila_abandonada,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo,
  ROUND(AVG(csat), 2)                                        AS csat_medio,
  ROUND(AVG(num_mensagens), 1)                               AS media_turnos,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 1)             AS pct_reabertura
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY idioma, segmento_cliente
HAVING conversas >= 50
ORDER BY idioma, conversas DESC;


-- CONSULTA: a9_custo_por_desfecho
-- Bloco A9 - quanto custa cada tipo de desfecho, em tempo e em turnos.
-- Base do calculo de ROI da V2.
SELECT
  status_conversa,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS pct_do_total,
  ROUND(AVG(duracao_min), 1)                                 AS duracao_media_min,
  ROUND(AVG(num_mensagens), 1)                               AS media_turnos,
  ROUND(AVG(num_mensagens_cliente), 1)                       AS media_turnos_cliente,
  ROUND(AVG(csat), 2)                                        AS csat_medio,
  ROUND(SUM(duracao_min) / 60, 0)                            AS horas_totais
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY status_conversa
ORDER BY conversas DESC;


-- CONSULTA: a9_arquetipo_perfil
-- Bloco A9 - o perfil do cliente muda o resultado do atendimento?
SELECT
  arquetipo,
  perfil_tecnologico,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)          AS pct_resolvido_bot,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo,
  ROUND(AVG(csat), 2)                                        AS csat_medio,
  ROUND(AVG(num_mensagens), 1)                               AS media_turnos
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY arquetipo, perfil_tecnologico
HAVING conversas >= 50
ORDER BY conversas DESC;


-- CONSULTA: a1_qualidade_campos
-- Bloco A1 - preenchimento dos campos. Confirma o que e nulo por regra
-- de negocio e o que seria nulo por falha.
SELECT
  'atendimentos'                                             AS tabela,
  COUNT(*)                                                   AS linhas,
  COUNTIF(csat IS NULL)                                      AS sem_csat,
  COUNTIF(canal_humano IS NULL)                              AS sem_canal_humano,
  COUNTIF(motivo_transferencia IS NULL)                      AS sem_motivo_transf,
  COUNTIF(area_encaminhada IS NULL)                          AS sem_area,
  COUNTIF(primeira_mensagem_cliente IS NULL)                 AS sem_primeira_msg,
  COUNTIF(transcricao_completa IS NULL)                      AS sem_transcricao
FROM `@PROJETO.kenzie360_silver.atendimentos`;


-- CONSULTA: a1_midia_e_pii
-- Bloco A1 - uso de audio e imagem, e quanto a regra de mascaramento agiu.
SELECT
  remetente,
  tipo_midia,
  COUNT(*)                                                   AS mensagens,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY remetente), 1) AS pct_do_remetente,
  COUNTIF(contem_dado_mascarado)                             AS com_dado_mascarado,
  COUNTIF(pii_remascarada)                                   AS remascaradas_pela_regra
FROM `@PROJETO.kenzie360_silver.mensagens`
GROUP BY remetente, tipo_midia
ORDER BY remetente, mensagens DESC;
