-- =====================================================================
-- Projeto Kenzie 360 - Sprint 2 - Trilha A (complemento)
-- TESTE DIRETO DA HIPOTESE DO PROJETO
--
-- Hipotese (formulada pelo grupo):
--   (a) o script da Kenzie V1 nao resolve sozinho - so sabe informar,
--       nao sabe executar acao em sistema;
--   (b) por isso depende cronicamente do atendimento humano;
--   (c) e o proprio atendimento humano falha, porque a demanda circula
--       entre areas internas do banco.
--
-- Cada consulta abaixo testa um pedaco disso.
-- =====================================================================


-- CONSULTA: h1_informar_vs_executar
-- Testa (a): a Kenzie resolve quando basta informar e falha quando
-- precisa agir? Classifica a demanda pelo TIPO DE ACAO exigida.
SELECT
  CASE categoria_assunto
    WHEN 'Saldo e Extrato'            THEN '1. Informacional (so consultar)'
    WHEN 'Investimentos CDB'          THEN '1. Informacional (so consultar)'
    WHEN 'Termos e Documentacao BR'   THEN '1. Informacional (so consultar)'
    WHEN 'Cartao de Credito'          THEN '2. Misto (consulta + acao leve)'
    WHEN 'Primeiro Acesso'            THEN '2. Misto (consulta + acao leve)'
    WHEN 'Alteracao de Limites'       THEN '3. Transacional (exige sistema)'
    WHEN 'Cambio'                     THEN '3. Transacional (exige sistema)'
    WHEN 'Onboarding - Documentacao'  THEN '3. Transacional (exige sistema)'
    WHEN 'Bloqueio TED/PIX'           THEN '3. Transacional (exige sistema)'
    WHEN 'Operacoes PJ - Folha e Pagamentos' THEN '3. Transacional (exige sistema)'
    ELSE '4. Nao atendimento (disparo/ruido)'
  END                                                        AS tipo_demanda,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS pct_do_total,
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)          AS pct_bot_resolve,
  ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 1) AS pct_pede_humano,
  ROUND(AVG(duracao_min), 1)                                 AS duracao_media_min,
  ROUND(AVG(csat), 2)                                        AS csat_medio,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 1)             AS pct_reabertura
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY tipo_demanda
ORDER BY tipo_demanda;


-- CONSULTA: h2_motivos_por_natureza
-- Testa (a) e (b): todo motivo de transferencia e uma limitacao de
-- permissao/capacidade do bot, e nao uma preferencia do cliente?
--
-- !! ATENCAO (28/08/2026) - ESTA CONSULTA NAO RESPONDE A PERGUNTA ACIMA.
-- A auditoria do gerador mostrou que motivo_transferencia e sorteado com
-- probabilidade uniforme (random.choice), sem vinculo com texto, assunto ou
-- cliente: os cinco motivos aparecem entre 19,4% e 20,5%, e cada um se
-- espalha pelas nove areas na mesma proporcao. Agrupar por motivo e agrupar
-- por ruido.
--
-- Alem disso, o grupo '(NAO CLASSIFICADO)' e enviesado por construcao: ele
-- reune os casos resolvidos que nao registraram motivo (60% deles) e os
-- abandonados na fila, que nunca chegam a receber um. Por isso o seu
-- pct_atendido e o seu pct_resolvido_no_fim sao artefatos, nao achados.
--
-- MANTIDA apenas para rastreabilidade do que foi executado na Sprint 2.
-- NAO usar o resultado desta consulta em relatorio, dashboard ou modelo.
-- Ver EDA_Kenzie360_v2.md, Secao 4 (nota de revisao).
SELECT
  COALESCE(motivo_transferencia, '(NAO CLASSIFICADO)')       AS motivo,
  COUNT(*)                                                   AS transferencias,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS pct_das_transferencias,
  COUNTIF(humano_atendeu)                                    AS humano_atendeu,
  ROUND(100 * COUNTIF(humano_atendeu) / COUNT(*), 1)         AS pct_atendido,
  COUNTIF(status_conversa = 'Resolvida por humano')          AS resolvidas,
  ROUND(100 * COUNTIF(status_conversa = 'Resolvida por humano') / COUNT(*), 1) AS pct_resolvido_no_fim,
  ROUND(AVG(csat), 2)                                        AS csat_medio
FROM `@PROJETO.kenzie360_silver.atendimentos`
WHERE transferencia_iniciada
GROUP BY motivo
ORDER BY transferencias DESC;


-- CONSULTA: h3_falha_por_area
-- Testa (c): o atendimento humano falha depois de receber o caso?
--
-- REVISADA em 28/08/2026. A versao anterior media a taxa sobre as conversas
-- com area_encaminhada preenchida. No gerador, o caso resolvido so registra
-- area em 40% das vezes e o nao resolvido registra sempre - o denominador
-- excluia tres em cada cinco sucessos e nenhum fracasso, inflando a taxa de
-- falha em 2,01x (32,0% contra os 15,9% reais).
--
-- Duas correcoes:
--   1. O denominador passa a ser "o humano atendeu o caso" (COUNTIF(humano_atendeu)).
--   2. A area passa a vir do ASSUNTO, que e deterministico e existe para toda
--      conversa, em vez do campo area_encaminhada, disponivel em so 40% dos
--      casos resolvidos. O mapeamento e o mesmo de vw_dim_assunto.area_padrao.
--
-- Backup da versao anterior: /tmp/04_hipotese_backup_28ago.sql
SELECT
  CASE categoria_assunto
    WHEN 'Saldo e Extrato'                   THEN 'Backoffice'
    WHEN 'Investimentos CDB'                 THEN 'Investimentos'
    WHEN 'Termos e Documentacao BR'          THEN 'Cadastro/Onboarding'
    WHEN 'Cartao de Credito'                 THEN 'Cartoes'
    WHEN 'Primeiro Acesso'                   THEN 'Suporte Tecnico'
    WHEN 'Alteracao de Limites'              THEN 'Mesa de Limites'
    WHEN 'Cambio'                            THEN 'Cambio/Backoffice'
    WHEN 'Onboarding - Documentacao'         THEN 'Cadastro/Onboarding'
    WHEN 'Bloqueio TED/PIX'                  THEN 'Prevencao a Fraude'
    WHEN 'Operacoes PJ - Folha e Pagamentos' THEN 'Atendimento PJ'
    ELSE '(sem area definida)'
  END                                                        AS area,
  COUNT(*)                                                   AS escaladas,
  COUNTIF(transferencia_iniciada AND NOT humano_atendeu)     AS desistiu_na_fila,
  COUNTIF(humano_atendeu)                                    AS atendidas,
  COUNTIF(status_conversa = 'Resolvida por humano')          AS resolvidas,
  COUNTIF(status_conversa = 'Transferida - sem resolucao')   AS nao_resolvidas,
  -- taxa sobre o denominador CORRETO: dos casos que chegaram ao humano
  ROUND(100 * SAFE_DIVIDE(
      COUNTIF(status_conversa = 'Resolvida por humano'),
      COUNTIF(humano_atendeu)), 1)                           AS pct_resolvido,
  ROUND(AVG(IF(humano_atendeu, csat, NULL)), 2)              AS csat_medio,
  ROUND(SUM(IF(humano_atendeu, duracao_min, 0)) / 60, 0)     AS horas_consumidas
FROM `@PROJETO.kenzie360_silver.atendimentos`
WHERE transferencia_iniciada
GROUP BY area
ORDER BY atendidas DESC;


-- CONSULTA: h4_custo_da_dependencia
-- Quantifica (b): quanto custa a operacao depender do humano.
-- Compara o mundo atual com dois cenarios de autonomia do bot.
WITH base AS (
  SELECT
    COUNT(*)                                                        AS total,
    COUNTIF(resolvido_bot)                                          AS resolvidas_bot,
    COUNTIF(transferencia_iniciada)                                 AS pediram_humano,
    SUM(IF(status_conversa = 'Resolvida por humano', duracao_min, 0))     AS min_humano_ok,
    SUM(IF(status_conversa = 'Transferida - sem resolucao', duracao_min, 0)) AS min_humano_falhou,
    AVG(IF(resolvido_bot, duracao_min, NULL))                       AS min_medio_bot,
    AVG(IF(status_conversa = 'Resolvida por humano', duracao_min, NULL)) AS min_medio_humano
  FROM `@PROJETO.kenzie360_silver.atendimentos`
)
SELECT
  total                                                             AS conversas_no_periodo,
  resolvidas_bot,
  ROUND(100 * resolvidas_bot / total, 1)                            AS pct_autonomia_atual,
  ROUND(min_medio_bot, 1)                                           AS min_por_conversa_bot,
  ROUND(min_medio_humano, 1)                                        AS min_por_conversa_humano,
  ROUND((min_humano_ok + min_humano_falhou) / 60, 0)                AS horas_humanas_no_periodo,
  ROUND(min_humano_falhou / 60, 0)                                  AS horas_humanas_desperdicadas,
  -- Cenario: cada 10 p.p. de autonomia extra libera quantas horas por ano?
  ROUND(2 * (total * 0.10) * (min_medio_humano - min_medio_bot) / 60, 0) AS horas_ano_por_10pp_autonomia
FROM base;


-- CONSULTA: h5_reabertura_e_resolucao_primeiro_contato
-- Liga (c) ao efeito no cliente: quando a demanda passa por area interna,
-- o cliente volta mais? Compara resolvido pelo bot x por humano.
SELECT
  CASE
    WHEN resolvido_bot                                    THEN '1. Bot resolveu sozinho'
    WHEN status_conversa = 'Resolvida por humano'         THEN '2. Humano resolveu'
    WHEN status_conversa = 'Transferida - sem resolucao'  THEN '3. Humano atendeu e nao resolveu'
    WHEN transferencia_iniciada AND NOT humano_atendeu    THEN '4. Pediu humano e nao foi atendido'
    ELSE '5. Outros desfechos'
  END                                                        AS trajetoria,
  COUNT(*)                                                   AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)           AS pct_do_total,
  ROUND(100 * COUNTIF(reabertura) / COUNT(*), 1)             AS pct_reabertura,
  ROUND(AVG(contatos_previos), 2)                            AS media_contatos_previos,
  ROUND(AVG(csat), 2)                                        AS csat_medio,
  ROUND(AVG(duracao_min), 1)                                 AS duracao_media_min
FROM `@PROJETO.kenzie360_silver.atendimentos`
GROUP BY trajetoria
ORDER BY trajetoria;


-- CONSULTA: h6_reabertura_causa_ou_consequencia
-- Correcao metodologica: a coluna "reabertura" descreve o desfecho da conversa
-- ANTERIOR do mesmo cliente, nao o da propria conversa. O teste correto tem
-- duas partes:
--   (1) o desfecho anterior explica a marca de reabertura? (deve explicar,
--       e por construcao do gerador);
--   (2) ser uma reabertura torna a conversa ATUAL mais dificil? (na operacao
--       real, sim; e isso que estamos testando).
WITH ordenado AS (
  SELECT
    id_conversa,
    id_cliente,
    data_hora,
    contatos_previos,
    reabertura,
    resolvido_bot,
    resolucao_declarada,
    status_conversa,
    transferencia_iniciada,
    num_mensagens,
    duracao_min,
    csat,
    sentimento_geral,
    LAG(resolucao_declarada) OVER (PARTITION BY id_cliente ORDER BY data_hora) AS desfecho_anterior
  FROM `@PROJETO.kenzie360_silver.atendimentos`
)
SELECT
  CASE
    WHEN contatos_previos = 0 THEN '1. Primeiro contato do cliente'
    WHEN reabertura         THEN '2. Reabertura (anterior nao resolveu)'
    ELSE                         '3. Novo contato (anterior resolveu)'
  END                                                        AS situacao,
  COUNT(*)                                                   AS conversas,
  -- (1) coerencia da marca: o desfecho anterior bate com a marca de reabertura?
  ROUND(100 * COUNTIF(desfecho_anterior IN ('Nao', 'Desconhecido')) / COUNT(*), 1) AS pct_anterior_sem_resolucao,
  -- (2) o desfecho ATUAL muda conforme a situacao?
  ROUND(100 * COUNTIF(resolvido_bot) / COUNT(*), 1)          AS pct_bot_resolve_agora,
  ROUND(100 * COUNTIF(transferencia_iniciada) / COUNT(*), 1) AS pct_pede_humano_agora,
  ROUND(100 * COUNTIF(sentimento_geral = 'Negativo') / COUNT(*), 1) AS pct_negativo_agora,
  ROUND(AVG(num_mensagens), 1)                               AS turnos_agora,
  ROUND(AVG(duracao_min), 1)                                 AS duracao_agora,
  ROUND(AVG(csat), 2)                                        AS csat_agora
FROM ordenado
GROUP BY situacao
ORDER BY situacao;
