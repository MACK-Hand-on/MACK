-- =============================================================================
-- PROJETO KENZIE 360 - Sprint 3
-- 08_diagnostico_alvos.sql
--
-- OBJETIVO: verificar, na propria base, se os alvos candidatos do modelo de NLP
-- sao de fato aprendiveis. Nao confie na leitura do codigo do gerador - rode
-- estas cinco consultas e olhe os numeros.
--
-- COMO RODAR:
--   1. Abra https://console.cloud.google.com/bigquery
--   2. Confirme que o projeto selecionado no topo e "kenzie-360-mba"
--   3. Cole UMA consulta por vez no editor e clique em "EXECUTAR"
--   4. Compare o resultado com o bloco "O QUE ESPERAR" de cada consulta
--
-- CUSTO: as cinco juntas varrem poucos MB. Irrelevante na franquia de 1 TiB.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- CONSULTA 1 - Como os motivos de transferencia se distribuem?
--
-- O QUE ESPERAR:
--   Se os 5 motivos aparecerem com percentuais parecidos (~20% cada), o motivo
--   foi sorteado ao acaso e NAO carrega informacao. Se houver concentracao
--   (ex.: um motivo com 45% e outro com 4%), ha estrutura para aprender.
-- -----------------------------------------------------------------------------
SELECT
  COALESCE(motivo_transferencia, '(sem motivo)') AS motivo,
  COUNT(*)                                      AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM `kenzie-360-mba.kenzie360_silver.atendimentos`
GROUP BY motivo
ORDER BY conversas DESC;


-- -----------------------------------------------------------------------------
-- CONSULTA 2 - O motivo prediz a area de destino?  (a pergunta do #1 -> #5)
--
-- O QUE ESPERAR:
--   Se cada motivo apontar para UMA area, o #5 sai de graca a partir do #1.
--   Se cada motivo se espalhar por todas as 9 areas em proporcao parecida,
--   os dois nao tem relacao nenhuma - e o #1 nao serve para roteamento.
-- -----------------------------------------------------------------------------
SELECT
  motivo_transferencia AS motivo,
  area_encaminhada     AS area,
  COUNT(*)             AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY motivo_transferencia), 1) AS pct_dentro_do_motivo
FROM `kenzie-360-mba.kenzie360_silver.atendimentos`
WHERE motivo_transferencia IS NOT NULL
  AND area_encaminhada     IS NOT NULL
GROUP BY motivo, area
ORDER BY motivo, conversas DESC;


-- -----------------------------------------------------------------------------
-- CONSULTA 3 - A categoria do assunto prediz a area?  (o teste do alvo #5)
--
-- O QUE ESPERAR:
--   Uma linha por categoria, cada uma com "areas_distintas = 1".
--   Isso significa que a area e deterministica a partir do assunto - e como o
--   assunto esta no texto da primeira mensagem, o alvo E aprendivel por NLP.
-- -----------------------------------------------------------------------------
SELECT
  categoria_assunto,
  COUNT(DISTINCT area_encaminhada) AS areas_distintas,
  STRING_AGG(DISTINCT area_encaminhada, ' | ' ORDER BY area_encaminhada) AS areas,
  COUNT(*) AS conversas
FROM `kenzie-360-mba.kenzie360_silver.atendimentos`
WHERE area_encaminhada IS NOT NULL
GROUP BY categoria_assunto
ORDER BY conversas DESC;


-- -----------------------------------------------------------------------------
-- CONSULTA 4 - O motivo depende do assunto?
--
-- O QUE ESPERAR:
--   Se dentro de CADA categoria os 5 motivos aparecerem em ~20% cada, esta
--   confirmado: o motivo e ruido. Nem o assunto, nem o texto, nem nada o explica.
-- -----------------------------------------------------------------------------
SELECT
  categoria_assunto,
  motivo_transferencia AS motivo,
  COUNT(*)             AS conversas,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY categoria_assunto), 1) AS pct_dentro_da_categoria
FROM `kenzie-360-mba.kenzie360_silver.atendimentos`
WHERE motivo_transferencia IS NOT NULL
GROUP BY categoria_assunto, motivo
ORDER BY categoria_assunto, conversas DESC;


-- -----------------------------------------------------------------------------
-- CONSULTA 5 - Por que 55% das transferencias nao tem motivo?
--
-- O QUE ESPERAR:
--   Olhe a coluna pct_sem_motivo por status_conversa. Se as conversas
--   abandonadas tiverem 100% sem motivo, a ausencia do motivo nao e uma falha
--   de processo: e consequencia mecanica de a conversa ter terminado ANTES de
--   um humano assumir o caso e registrar o motivo.
--   Isso muda a leitura da Secao 4.1 da EDA.
-- -----------------------------------------------------------------------------
SELECT
  status_conversa,
  transferencia_iniciada,
  humano_atendeu,
  COUNT(*) AS conversas,
  COUNTIF(motivo_transferencia IS NULL) AS sem_motivo,
  ROUND(100 * COUNTIF(motivo_transferencia IS NULL) / COUNT(*), 1) AS pct_sem_motivo
FROM `kenzie-360-mba.kenzie360_silver.atendimentos`
WHERE transferencia_iniciada = TRUE
GROUP BY status_conversa, transferencia_iniciada, humano_atendeu
ORDER BY conversas DESC;
