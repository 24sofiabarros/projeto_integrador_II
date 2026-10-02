INSERT INTO contribuinte (cpf_cnpj, nome, isencao_iptu_social) VALUES
('111.222.333-00', 'João Silva', FALSE),
('222.333.444-11', 'Maria Oliveira (Beneficiária Social)', TRUE),
('33.444.555/0001-66', 'Comércio de Alimentos Palmas LTDA', FALSE),
('444.555.666-33', 'Carlos Eduardo Santos', FALSE);

INSERT INTO imovel (inscricao_imobiliaria, id_contribuinte, logradouro, bairro, setor, area_edificada_m2) VALUES
('IMP-104S-01', 1, 'Rua NE 01, Lote 12', 'Plano Diretor Sul', '104 Sul', 150.00),
('IMP-TAQ-05', 2, 'Av. Tocantins, Quadra 10', 'Taquaralto', 'Setor Taquaralto', 70.50),
('IMP-501N-09', 3, 'Av. LO 11, Lote 04', 'Plano Diretor Norte', '501 Norte', 450.00),
('IMP-104S-02', 1, 'Rua NE 03, Lote 15', 'Plano Diretor Sul', '104 Sul', 210.00);

INSERT INTO divida_ativa (inscricao_imobiliaria, tipo_tributo, exercicio, valor_consolidado, score_recuperabilidade, status_cobranca) VALUES
('IMP-104S-01', 'IPTU', 2024, 2500.50, 88.50, 'Em Aberto'),
('IMP-TAQ-05', 'IPTU', 2023, 850.00, 20.00, 'Em Aberto'),
('IMP-501N-09', 'ISS', 2024, 15400.00, 94.20, 'Em Aberto'),
('IMP-104S-02', 'IPTU', 2023, 3100.00, 75.00, 'Em Aberto'),
('IMP-501N-09', 'ITBI', 2022, 8900.00, 60.00, 'Ajuizado');