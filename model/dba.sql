-- ============================================================
-- SISTEMA PYROSYNC - INSPEÇÃO DE EXTINTORES COM QR CODE
-- ============================================================

DROP DATABASE IF EXISTS pyrosync;
CREATE DATABASE pyrosync;
USE pyrosync;

-- ============================================================
-- TABELA DE BRIGADISTAS
-- ============================================================

CREATE TABLE Brigadistas (
    id_brigadista INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    setor VARCHAR(50) NOT NULL,
    senha VARCHAR(255) NOT NULL
);

-- ============================================================
-- TABELA DE EXTINTORES
-- ============================================================

CREATE TABLE Extintores (
    id_extintor INT AUTO_INCREMENT PRIMARY KEY,
    qr_code VARCHAR(100) UNIQUE NOT NULL,
    numero_serie VARCHAR(50) NOT NULL UNIQUE,
    fabricante VARCHAR(50) NOT NULL,
    tipo ENUM(
        'Água',
        'CO2',
        'Pó Químico PQS',
        'Espuma Mecânica',
        'Compostos Halogenados'
    ) NOT NULL,
    classificacao VARCHAR(10) NOT NULL,
    capacidade_carga DECIMAL(5,2) NOT NULL,
    unidade_medida ENUM('KG','L') NOT NULL,
    data_fabricacao DATE NOT NULL,
    data_validade_carga DATE NOT NULL,
    localizacao_atual VARCHAR(100) NOT NULL,
    status_equipamento ENUM(
        'Ativo',
        'Em Manutenção',
        'Descartado/Inativo'
    ) DEFAULT 'Ativo'
);

-- ============================================================
-- TABELA DE INSPEÇÕES
-- ============================================================

CREATE TABLE Inspecoes (
    id_inspecao INT AUTO_INCREMENT PRIMARY KEY,
    id_brigadista INT NULL,
    id_extintor INT NOT NULL,
    data_inspecao DATE NOT NULL,
    hora_inspecao TIME NOT NULL,
    numero_lacre VARCHAR(30) NOT NULL,
    confirmar_tipo BOOLEAN NOT NULL,
    status_manometro ENUM('Normal', 'Baixa Pressão', 'Sobrepressão') NOT NULL,
    status_lacre ENUM('Intacto', 'Violado', 'Ausente') NOT NULL,
    status_bocal ENUM('Desobstruído', 'Obstruído', 'Ressecado', 'Ausente') NOT NULL,
    avaria_externa ENUM('Nenhuma', 'Corrosão', 'Amassado', 'Rótulo Ilegível') NOT NULL,
    observacoes TEXT,
    FOREIGN KEY (id_brigadista) REFERENCES Brigadistas(id_brigadista) ON DELETE SET NULL,
    FOREIGN KEY (id_extintor) REFERENCES Extintores(id_extintor) ON DELETE CASCADE
);

-- ============================================================
-- TABELA DE RELATÓRIOS (Otimizada - sem dados redundantes)
-- ============================================================

CREATE TABLE Relatorios_Inspecao (
    id_relatorio INT AUTO_INCREMENT PRIMARY KEY,
    id_inspecao INT NOT NULL,
    situacao VARCHAR(100) NOT NULL,
    FOREIGN KEY (id_inspecao) REFERENCES Inspecoes(id_inspecao) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- AUTOMATIZAÇÃO: TRIGGER PARA GERAR RELATÓRIO AUTOMATICAMENTE
-- ============================================================

DELIMITER $$
CREATE TRIGGER tg_gerar_relatorio
AFTER INSERT ON Inspecoes
FOR EACH ROW
BEGIN
    DECLARE v_situacao VARCHAR(100);
    
    -- Lógica simples de aprovação
    IF NEW.status_manometro = 'Normal' AND NEW.status_lacre = 'Intacto' AND NEW.status_bocal = 'Desobstruído' AND NEW.avaria_externa = 'Nenhuma' THEN
        SET v_situacao = 'Equipamento aprovado para uso';
    ELSE
        SET v_situacao = 'Equipamento reprovado - Necessita manutenção';
    END IF;

    INSERT INTO Relatorios_Inspecao (id_inspecao, situacao)
    VALUES (NEW.id_inspecao, v_situacao);
END$$
DELIMITER ;

-- ============================================================
-- DADOS DE EXEMPLO
-- ============================================================

INSERT INTO Brigadistas (id_brigadista, nome, setor, senha)
VALUES (1020, 'Victor Augusto', 'Segurança do Trabalho', 'pbkdf2:sha256:600000$examplehash');

INSERT INTO Extintores 
(id_extintor, qr_code, numero_serie, fabricante, tipo, classificacao, capacidade_carga, unidade_medida, data_fabricacao, data_validade_carga, localizacao_atual, status_equipamento)
VALUES
(5001, 'QR-5001', 'AG-1111-2026', 'Resil', 'Água', 'A', 10.00, 'L', '2025-01-10', '2027-01-10', 'Galpão de Armazenamento', 'Ativo'),
(5002, 'QR-5002', 'CO-2222-2026', 'Kidde', 'CO2', 'BC', 6.00, 'KG', '2024-05-20', '2026-05-20', 'Sala do Servidor (TI)', 'Ativo'),
(5003, 'QR-5003', 'PQ-3333-2026', 'Bucka', 'Pó Químico PQS', 'ABC', 4.00, 'KG', '2025-03-15', '2027-03-15', 'Recepção Principal', 'Ativo'),
(5004, 'QR-5004', 'PQ-4444-2026', 'Mocelin', 'Pó Químico PQS', 'ABC', 8.00, 'KG', '2023-11-12', '2026-11-12', 'Oficina de Manutenção', 'Ativo');

-- ============================================================
-- INSPEÇÃO REALIZADA APÓS LEITURA DO QR CODE
-- ============================================================

-- Nota: O ID gerado aqui automaticamente para id_inspecao será 1.
INSERT INTO Inspecoes 
(id_brigadista, id_extintor, data_inspecao, hora_inspecao, numero_lacre, confirmar_tipo, status_manometro, status_lacre, status_bocal, avaria_externa, observacoes)
VALUES
(1020, 5003, '2026-05-30', '14:30:00', 'LAC-9999', 1, 'Normal', 'Intacto', 'Desobstruído', 'Nenhuma', 'Equipamento em perfeito estado.');

-- O INSERT na tabela Relatorios_Inspecao NÃO é mais necessário! A Trigger faz isso sozinha.

-- ============================================================
-- CONSULTA DO RELATÓRIO FINAL (Ajustada para o novo modelo)
-- ============================================================

SELECT
    e.qr_code AS QR_Code,
    e.numero_serie AS Extintor,
    e.localizacao_atual AS Localizacao,
    i.status_lacre AS Lacre,
    i.status_manometro AS Manometro,
    i.status_bocal AS Bocal,
    b.nome AS Responsavel,
    i.data_inspecao AS Data,
    r.situacao AS Situacao
FROM Relatorios_Inspecao r
INNER JOIN Inspecoes i ON r.id_inspecao = i.id_inspecao
INNER JOIN Extintores e ON i.id_extintor = e.id_extintor
LEFT JOIN Brigadistas b ON i.id_brigadista = b.id_brigadista;

-- ============================================================
-- BLOCO ADICIONAL: INF07SST
-- Observação: o trecho de CREATE TABLE Extintores do INF07SST
-- estava incompleto no enunciado (aparecia truncado em “d...”).
-- Como você respondeu “não precisa criar”, este bloco adiciona apenas
-- a base e a tabela Brigadistas com telefone/email/whatsapp.
-- ============================================================

CREATE DATABASE IF NOT EXISTS INF07SST;
USE INF07SST;

CREATE TABLE IF NOT EXISTS Brigadistas (
    id_brigadista INT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20),
    email VARCHAR(100),
    whatsapp VARCHAR(20)
);
