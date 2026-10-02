-- Fila de Cobrança Priorizada por Score (sem IPTU Social)
SELECT 
    c.nome AS contribuinte,
    c.cpf_cnpj,
    i.inscricao_imobiliaria,
    i.setor,
    d.tipo_tributo,
    d.valor_consolidado,
    d.score_recuperabilidade
FROM divida_ativa d
JOIN imovel i ON d.inscricao_imobiliaria = i.inscricao_imobiliaria
JOIN contribuinte c ON i.id_contribuinte = c.id_contribuinte
WHERE c.isencao_iptu_social = FALSE 
  AND d.status_cobranca = 'Em Aberto'
ORDER BY d.score_recuperabilidade DESC;

-- Montante acumulado da Dívida por Tributo
SELECT 
    tipo_tributo,
    COUNT(id_divida) AS qtd_processos,
    SUM(valor_consolidado) AS total_devido,
    ROUND(AVG(score_recuperabilidade), 2) AS media_score
FROM divida_ativa
GROUP BY tipo_tributo
ORDER BY total_devido DESC;