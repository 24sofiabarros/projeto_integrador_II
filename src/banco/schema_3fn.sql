CREATE TABLE IF NOT EXISTS contribuinte (
    id_contribuinte SERIAL PRIMARY KEY,
    cpf_cnpj VARCHAR(18) UNIQUE NOT NULL,
    nome VARCHAR(150) NOT NULL,
    isencao_iptu_social BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS imovel (
    inscricao_imobiliaria VARCHAR(30) PRIMARY KEY,
    id_contribuinte INT NOT NULL,
    logradouro VARCHAR(200) NOT NULL,
    bairro VARCHAR(100) NOT NULL,
    setor VARCHAR(100) NOT NULL,
    area_edificada_m2 NUMERIC(10,2),
    FOREIGN KEY (id_contribuinte) REFERENCES contribuinte(id_contribuinte)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS divida_ativa (
    id_divida SERIAL PRIMARY KEY,
    inscricao_imobiliaria VARCHAR(30) NOT NULL,
    tipo_tributo VARCHAR(20) NOT NULL CHECK (tipo_tributo IN ('IPTU', 'ISS', 'ITBI', 'TAXAS')),
    exercicio INT NOT NULL,
    valor_consolidado NUMERIC(12,2) NOT NULL CHECK (valor_consolidado >= 0),
    score_recuperabilidade NUMERIC(5,2) CHECK (score_recuperabilidade BETWEEN 0 AND 100),
    status_cobranca VARCHAR(30) DEFAULT 'Em Aberto' CHECK (status_cobranca IN ('Em Aberto', 'Ajuizado', 'Parcelado', 'Quitado')),
    FOREIGN KEY (inscricao_imobiliaria) REFERENCES imovel(inscricao_imobiliaria)
        ON DELETE RESTRICT ON UPDATE CASCADE
);