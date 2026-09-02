-- =====================================================================
-- Projeto Kenzie 360 - Sprint 2 - Trilha B
-- CAMADA GOLD (CURATED)
--
-- Cada view responde uma pergunta de negocio identificada na EDA.
-- Nenhuma view existe "por completude": todas tem achado que as justifica.
--
-- Sao VIEWS, nao tabelas: o dado nunca fica defasado e nao ocupa storage.
-- Como a silver e particionada por data_ref, um filtro de periodo no
-- Looker Studio varre so as particoes necessarias.
--
-- O marcador "-- BLOCO:" separa os comandos. @PROJETO e substituido
-- pelo script 06_cria_gold.py.
-- =====================================================================


-- BLOCO: vw_dim_assunto
-- Dimensao de apoio: classifica cada assunto pelo TIPO DE ACAO que exige.
-- Este corte foi o que revelou a causa do problema (EDA, Teste "a") e por
-- isso vira dimensao formal, nao um CASE repetido em cada consulta.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_dim_assunto`
OPTIONS(description="Dimensao de assunto: tipo de demanda e area responsavel")
AS
SELECT * FROM UNNEST([
  STRUCT('Saldo e Extrato'                   AS categoria_assunto, 'Informacional' AS tipo_demanda, 1 AS ordem_tipo, 'Backoffice'          AS area_padrao),
  ('Investimentos CDB',                             'Informacional', 1, 'Investimentos'),
  ('Termos e Documentacao BR',                      'Informacional', 1, 'Cadastro/Onboarding'),
  ('Cartao de Credito',                             'Misto',         2, 'Cartoes'),
  ('Primeiro Acesso',                               'Misto',         2, 'Suporte Tecnico'),
  ('Alteracao de Limites',                          'Transacional',  3, 'Mesa de Limites'),
  ('Cambio',                                        'Transacional',  3, 'Cambio/Backoffice'),
  ('Onboarding - Documentacao',                     'Transacional',  3, 'Cadastro/Onboarding'),
  ('Bloqueio TED/PIX',                              'Transacional',  3, 'Prevencao a Fraude'),
  ('Operacoes PJ - Folha e Pagamentos',             'Transacional',  3, 'Atendimento PJ'),
  ('Disparo Ativo',                                 'Nao atendimento', 4, NULL),
  ('Ruido / Nao-atendimento',                       'Nao atendimento', 4, NULL)
]);


-- BLOCO: vw_kpi_diario
-- Serie temporal para o topo do dashboard. Com a sazonalidade corrigida na
-- base v8, esta view voltou a produzir sinal (na v7 era ruido).
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_kpi_diario`
OPTIONS(description="KPIs por dia: volume, autonomia, funil, satisfacao e horas humanas")
AS
SELECT
  data_ref,
  FORMAT_DATE('%A', data_ref)                                      AS dia_semana,
  EXTRACT(DAYOFWEEK FROM data_ref)                                 AS dia_semana_num,
  DATE_TRUNC(data_ref, MONTH)                                      AS mes,
  COUNT(*)                                                         AS conversas,
  COUNTIF(resolvido_bot)                                           AS resolvidas_bot,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 2)                AS pct_autonomia,
  COUNTIF(status_conversa IN ('Resolvida pelo bot','Resolvida por humano')) AS resolvidas_total,
  ROUND(100 * COUNTIF(status_conversa IN ('Resolvida pelo bot','Resolvida por humano')) / COUNT(*), 2) AS pct_resolucao_total,
  COUNTIF(transferencia_iniciada)                                  AS transferencias,
  COUNTIF(transferencia_iniciada AND NOT humano_atendeu)           AS fila_abandonada,
  COUNTIF(status_conversa = 'Abandonada pelo cliente')             AS abandono_cliente,
  COUNTIF(status_conversa = 'Transferida - sem resolucao')         AS atendeu_e_nao_resolveu,
  ROUND(AVG(csat), 2)                                              AS csat_medio,
  COUNTIF(csat IS NOT NULL)                                        AS respostas_csat,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 2) AS pct_negativo,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 2)                   AS pct_reabertura,
  ROUND(SUM(IF(humano_atendeu, duracao_min, 0)) / 60, 1)           AS horas_humanas
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY data_ref;


-- BLOCO: vw_autonomia_por_tipo_demanda
-- Teste (a) da hipotese: a Kenzie resolve quando basta informar e falha
-- quando precisa executar acao em sistema.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_autonomia_por_tipo_demanda`
OPTIONS(description="Autonomia do bot por tipo de acao exigida - evidencia central da hipotese")
AS
SELECT
  d.ordem_tipo,
  d.tipo_demanda,
  a.categoria_assunto,
  a.segmento_cliente,
  COUNT(*)                                                         AS conversas,
  COUNTIF(a.resolvido_bot)                                         AS resolvidas_bot,
  ROUND(100 * COUNTIF(a.resolvido_bot) / COUNT(*), 2)              AS pct_bot_resolve,
  ROUND(100 * COUNTIF(a.transferencia_iniciada) / COUNT(*), 2)     AS pct_pede_humano,
  ROUND(AVG(a.duracao_min), 2)                                     AS duracao_media_min,
  ROUND(AVG(a.num_mensagens), 1)                                   AS turnos_medios,
  ROUND(AVG(a.csat), 2)                                            AS csat_medio,
  ROUND(100 * COUNTIF(a.sentimento_geral = 'Negativo') / COUNT(*), 2) AS pct_negativo
FROM `@PROJETO.kenzie360_silver.atendimentos` a
LEFT JOIN `@PROJETO.kenzie360_gold.vw_dim_assunto` d USING (categoria_assunto)
GROUP BY d.ordem_tipo, d.tipo_demanda, a.categoria_assunto, a.segmento_cliente;


-- BLOCO: vw_funil_atendimento
-- Teste (c), REVISADO em 28/08/2026.
--
-- A versao anterior (vw_funil_e_modos_de_falha) separava as conversas por
-- "com motivo classificado" x "sem motivo classificado". Essa separacao era
-- ARTEFATO do gerador: o motivo so e atribuido quando um humano assume o
-- caso, e o caso nao resolvido sempre recebe motivo enquanto o resolvido so
-- recebe em 40% das vezes. O recorte media a propria regra, nao a operacao.
--
-- Esta view descreve o funil real, etapa a etapa. Cada coluna e uma
-- CONTAGEM: no Looker Studio, calcule taxas com SUM(x)/SUM(y), nunca com a
-- media de percentuais ja calculados (a media de taxas diarias daria peso
-- igual a um sabado vazio e a uma terca cheia).
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_funil_atendimento`
OPTIONS(description="Funil do atendimento etapa a etapa. Use SUM/SUM para taxas.")
AS
SELECT
  data_ref,
  segmento_cliente,
  categoria_assunto,
  COUNT(*)                                                         AS conversas,
  -- etapa 1: o bot resolveu sozinho
  COUNTIF(resolvido_bot)                                           AS e1_bot_resolveu,
  -- etapa 2: escalou para humano
  COUNTIF(transferencia_iniciada)                                  AS e2_pediu_humano,
  -- etapa 3: desistiu antes de ser atendido (a fila abandonada)
  COUNTIF(transferencia_iniciada AND NOT humano_atendeu)           AS e3_desistiu_na_fila,
  -- etapa 4: um atendente humano assumiu o caso  <- DENOMINADOR CORRETO
  COUNTIF(humano_atendeu)                                          AS e4_humano_atendeu,
  -- etapa 5 e 6: desfecho do atendimento humano
  COUNTIF(status_conversa = 'Resolvida por humano')                AS e5_humano_resolveu,
  COUNTIF(status_conversa = 'Transferida - sem resolucao')         AS e6_humano_nao_resolveu,
  -- custo
  ROUND(SUM(IF(humano_atendeu, duracao_min, 0)) / 60, 1)           AS horas_humanas,
  ROUND(SUM(IF(status_conversa = 'Transferida - sem resolucao', duracao_min, 0)) / 60, 1) AS horas_sem_resultado,
  ROUND(AVG(csat), 2)                                              AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY data_ref, segmento_cliente, categoria_assunto;


-- BLOCO: vw_funil_e_modos_de_falha
-- OBSOLETA desde 28/08/2026. Mantida como repasse para vw_funil_atendimento,
-- de modo que qualquer relatorio ja conectado receba o dado CORRIGIDO em vez
-- de continuar lendo o recorte artefatual. Nao usar em novos relatorios.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_funil_e_modos_de_falha`
OPTIONS(description="OBSOLETA - use vw_funil_atendimento. Repassa a view corrigida.")
AS
SELECT * FROM `@PROJETO.kenzie360_gold.vw_funil_atendimento`;


-- BLOCO: vw_desempenho_areas_internas
-- Teste (c), REVISADO em 28/08/2026.
--
-- Duas correcoes em relacao a versao anterior:
--
-- 1. DENOMINADOR. Antes dividia por COUNT(*) sobre as linhas com
--    area_encaminhada preenchida. Como o caso resolvido so registra area em
--    40% das vezes e o nao resolvido registra sempre, aquele conjunto
--    excluia tres em cada cinco sucessos e nenhum fracasso - a taxa de falha
--    saia inflada em 2,01x (32,0% publicado contra 15,9% real).
--    Agora o denominador e "o humano atendeu o caso".
--
-- 2. ORIGEM DA AREA. Antes vinha do campo area_encaminhada, disponivel em
--    apenas 40% dos casos resolvidos. Agora vem de vw_dim_assunto.area_padrao,
--    que e deterministica a partir do assunto e existe para TODA conversa.
--
-- LEITURA: com o calculo correto as nove areas resolvem ~84% e nenhuma se
-- distingue das demais (oito dentro de 1,25 desvio-padrao da media). Isso NAO
-- e evidencia de que as areas sejam iguais na operacao real - e consequencia
-- de o gerador usar uma constante unica de resolucao para todas. Ver a Secao
-- 4.3 e 4.4 de EDA_Kenzie360_v2.md.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_desempenho_areas_internas`
OPTIONS(description="Por area responsavel: desfecho dos casos que chegaram ao humano")
AS
SELECT
  COALESCE(d.area_padrao, '(sem area definida)')                   AS area,
  a.segmento_cliente,
  -- volume que chega
  COUNTIF(a.transferencia_iniciada)                                AS escaladas,
  COUNTIF(a.transferencia_iniciada AND NOT a.humano_atendeu)       AS desistiu_na_fila,
  COUNTIF(a.humano_atendeu)                                        AS atendidas,
  -- desfecho
  COUNTIF(a.status_conversa = 'Resolvida por humano')              AS resolvidas,
  COUNTIF(a.status_conversa = 'Transferida - sem resolucao')        AS nao_resolvidas,
  -- taxa sobre o denominador correto (no Looker, prefira SUM/SUM)
  ROUND(100 * SAFE_DIVIDE(
      COUNTIF(a.status_conversa = 'Resolvida por humano'),
      COUNTIF(a.humano_atendeu)), 2)                               AS pct_resolvido,
  -- custo
  ROUND(SUM(IF(a.humano_atendeu, a.duracao_min, 0)) / 60, 1)       AS horas_consumidas,
  ROUND(SUM(IF(a.status_conversa = 'Transferida - sem resolucao', a.duracao_min, 0)) / 60, 1) AS horas_sem_resultado,
  ROUND(AVG(IF(a.humano_atendeu, a.duracao_min, NULL)), 2)         AS duracao_media_min,
  ROUND(AVG(IF(a.humano_atendeu, a.csat, NULL)), 2)                AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos` a
LEFT JOIN `@PROJETO.kenzie360_gold.vw_dim_assunto` d USING (categoria_assunto)
WHERE a.transferencia_iniciada
GROUP BY area, a.segmento_cliente;


-- BLOCO: vw_desfecho_e_custo
-- Achado 5.1: a satisfacao e bimodal. Esta view substitui o "CSAT medio"
-- por distribuicao entre cluster de resolucao e cluster de falha.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_desfecho_e_custo`
OPTIONS(description="Desfechos agrupados por cluster de satisfacao, com custo em horas")
AS
SELECT
  data_ref,
  status_conversa,
  CASE
    WHEN status_conversa IN ('Resolvida pelo bot','Resolvida por humano')  THEN '1. Resolvido'
    WHEN status_conversa IN ('Abandonada pelo cliente','Encerrada sem resolucao',
                             'Transferida - sem resolucao')                THEN '2. Falha'
    ELSE '3. Nao atendimento'
  END                                                              AS cluster,
  segmento_cliente,
  COUNT(*)                                                         AS conversas,
  ROUND(AVG(duracao_min), 2)                                       AS duracao_media_min,
  ROUND(SUM(duracao_min) / 60, 1)                                  AS horas_totais,
  ROUND(AVG(num_mensagens), 1)                                     AS turnos_medios,
  ROUND(AVG(csat), 2)                                              AS csat_medio,
  COUNTIF(csat IS NOT NULL)                                        AS respostas_csat
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY data_ref, status_conversa, cluster, segmento_cliente;


-- BLOCO: vw_espiral_recorrencia
-- Achado da Secao 6 - o de maior consequencia para o negocio, e que so a
-- base v8 permite calcular. Cada contato previo piora o proximo atendimento.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_espiral_recorrencia`
OPTIONS(description="Degradacao do atendimento conforme o cliente reincide")
AS
SELECT
  LEAST(contatos_previos, 5)                                       AS faixa_contatos,
  CASE WHEN contatos_previos = 0 THEN '1. Primeiro contato'
       WHEN reabertura          THEN '2. Reabertura (anterior falhou)'
       ELSE                          '3. Novo contato (anterior resolveu)'
  END                                                              AS situacao,
  segmento_cliente,
  COUNT(*)                                                         AS conversas,
  COUNT(DISTINCT id_cliente)                                       AS clientes,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 2)                AS pct_bot_resolve,
  ROUND(100 * COUNTIF(status_conversa IN ('Resolvida pelo bot','Resolvida por humano')) / COUNT(*), 2) AS pct_resolucao_total,
  ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 2)       AS pct_pede_humano,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 2) AS pct_negativo,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 2)                   AS pct_reabertura,
  ROUND(AVG(csat), 2)                                              AS csat_medio,
  ROUND(AVG(duracao_min), 2)                                       AS duracao_media_min,
  ROUND(SUM(duracao_min) / 60, 1)                                  AS horas_consumidas
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY faixa_contatos, situacao, segmento_cliente;


-- BLOCO: vw_jornada_sentimento
-- Achado 5.2: o humor do cliente so vira no fecho, e o pico de frustracao
-- esta no terco medio. Base para o gatilho de escalada da V2.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_jornada_sentimento`
OPTIONS(description="Sentimento do cliente por posicao relativa na conversa (quintos)")
AS
WITH falas AS (
  SELECT
    m.id_conversa,
    m.ordem,
    m.sentimento,
    m.segmento_cliente,
    m.idioma,
    m.categoria_assunto,
    m.data_ref,
    MAX(m.ordem) OVER (PARTITION BY m.id_conversa) AS ultimo_turno
  FROM `@PROJETO.kenzie360_silver.mensagens` m
  WHERE m.remetente = 'Cliente' AND m.sentimento IS NOT NULL
)
SELECT
  CASE WHEN ultimo_turno <= 1 THEN 1
       ELSE LEAST(5, GREATEST(1, CAST(CEIL(5 * SAFE_DIVIDE(ordem, ultimo_turno)) AS INT64)))
  END                                                              AS quinto_da_conversa,
  segmento_cliente,
  categoria_assunto,
  idioma,
  COUNT(*)                                                         AS falas,
  ROUND(100 * COUNTIF(sentimento = 'Positivo') / COUNT(*), 2)      AS pct_positivo,
  ROUND(100 * COUNTIF(sentimento = 'Neutro')   / COUNT(*), 2)      AS pct_neutro,
  ROUND(100 * COUNTIF(sentimento = 'Negativo') / COUNT(*), 2)      AS pct_negativo
FROM falas
GROUP BY quinto_da_conversa, segmento_cliente, categoria_assunto, idioma;


-- BLOCO: vw_dores_priorizadas
-- Ordena as dores por um score que combina volume, insatisfacao e custo -
-- em vez de so volume, que apontaria a prioridade errada.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_dores_priorizadas`
OPTIONS(description="Ranking de dores por score composto: volume x insatisfacao x custo")
AS
WITH base AS (
  SELECT
    a.categoria_assunto,
    d.tipo_demanda,
    COUNT(*)                                                       AS conversas,
    ROUND(100 * COUNTIF(a.sentimento_geral = 'Negativo') / COUNT(*), 2) AS pct_negativo,
    ROUND(100 * COUNTIF(a.resolvido_bot) / COUNT(*), 2)            AS pct_bot_resolve,
    ROUND(100 * COUNTIF(a.transferencia_iniciada) / COUNT(*), 2)   AS pct_transferencia,
    ROUND(100 * COUNTIF(a.reabertura) / COUNT(*), 2)               AS pct_reabertura,
    ROUND(AVG(a.csat), 2)                                          AS csat_medio,
    ROUND(AVG(a.duracao_min), 2)                                   AS duracao_media_min,
    ROUND(SUM(IF(a.humano_atendeu, a.duracao_min, 0)) / 60, 1)     AS horas_humanas
  FROM `@PROJETO.kenzie360_silver.atendimentos` a
  LEFT JOIN `@PROJETO.kenzie360_gold.vw_dim_assunto` d USING (categoria_assunto)
  WHERE d.tipo_demanda != 'Nao atendimento'
  GROUP BY a.categoria_assunto, d.tipo_demanda
),
normalizado AS (
  SELECT *,
    SAFE_DIVIDE(conversas     - MIN(conversas)     OVER (), NULLIF(MAX(conversas)     OVER () - MIN(conversas)     OVER (), 0)) AS n_volume,
    SAFE_DIVIDE(pct_negativo  - MIN(pct_negativo)  OVER (), NULLIF(MAX(pct_negativo)  OVER () - MIN(pct_negativo)  OVER (), 0)) AS n_insatisfacao,
    SAFE_DIVIDE(horas_humanas - MIN(horas_humanas) OVER (), NULLIF(MAX(horas_humanas) OVER () - MIN(horas_humanas) OVER (), 0)) AS n_custo
  FROM base
)
SELECT
  categoria_assunto,
  tipo_demanda,
  conversas,
  pct_negativo,
  pct_bot_resolve,
  pct_transferencia,
  pct_reabertura,
  csat_medio,
  duracao_media_min,
  horas_humanas,
  ROUND(100 * (0.35 * n_volume + 0.35 * n_insatisfacao + 0.30 * n_custo), 1) AS score_dor,
  RANK() OVER (ORDER BY (0.35 * n_volume + 0.35 * n_insatisfacao + 0.30 * n_custo) DESC) AS ranking
FROM normalizado;


-- BLOCO: vw_features_nlp
-- Insumo da Fase 4. SEM variavel alvo fixada (regra 5 do handoff): entrega
-- o texto e o contexto, e o alvo sera escolhido pelo grupo mais adiante.
--
-- NOTA TECNICA: o sentimento da primeira fala do cliente sai de uma CTE com
-- QUALIFY, e nao de subconsulta correlacionada. O BigQuery nao consegue
-- descorrelacionar subconsulta com ORDER BY + LIMIT que referencia outra
-- tabela, e devolve BadRequest.
CREATE OR REPLACE VIEW `@PROJETO.kenzie360_gold.vw_features_nlp`
OPTIONS(description="Texto + contexto para modelagem NLP. Sem variavel alvo definida.")
AS
WITH primeira_fala AS (
  SELECT
    id_conversa,
    sentimento AS sentimento_inicial,
    tipo_midia AS midia_inicial
  FROM `@PROJETO.kenzie360_silver.mensagens`
  WHERE remetente = 'Cliente' AND sentimento IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY id_conversa ORDER BY ordem) = 1
),
resumo_falas AS (
  SELECT
    id_conversa,
    COUNTIF(remetente = 'Cliente' AND sentimento = 'Negativo')     AS falas_negativas,
    COUNTIF(remetente = 'Cliente' AND tipo_midia != 'texto')       AS falas_com_midia,
    COUNTIF(contem_dado_mascarado)                                 AS falas_com_pii
  FROM `@PROJETO.kenzie360_silver.mensagens`
  GROUP BY id_conversa
)
SELECT
  a.id_conversa,
  a.id_cliente,
  a.data_ref,
  -- contexto do cliente
  a.segmento_cliente,
  a.arquetipo,
  a.perfil_tecnologico,
  a.faixa_etaria,
  a.idioma,
  a.contatos_previos,
  a.reabertura,
  -- contexto da demanda
  a.categoria_assunto,
  d.tipo_demanda,
  a.produto_relacionado,
  a.origem_contato,
  a.canal_entrada,
  -- texto
  a.primeira_mensagem_cliente,
  a.transcricao_completa,
  -- sinais derivados da conversa
  a.num_mensagens,
  a.num_mensagens_cliente,
  a.duracao_min,
  a.sentimento_geral,
  p.sentimento_inicial,
  p.midia_inicial,
  r.falas_negativas,
  r.falas_com_midia,
  r.falas_com_pii,
  a.qtd_dados_mascarados,
  -- desfechos disponiveis (o grupo escolhe qual vira alvo na Fase 4)
  a.resolvido_bot,
  a.transferencia_iniciada,
  a.humano_atendeu,
  a.status_conversa,
  a.resolucao_declarada,
  a.motivo_transferencia,
  a.area_encaminhada,
  a.csat
FROM `@PROJETO.kenzie360_silver.atendimentos` a
LEFT JOIN `@PROJETO.kenzie360_gold.vw_dim_assunto` d USING (categoria_assunto)
LEFT JOIN primeira_fala p USING (id_conversa)
LEFT JOIN resumo_falas r USING (id_conversa);
