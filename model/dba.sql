-- ============================================================
-- SISTEMA PYROSYNC - INSPEÇÃO DE EXTINTORES COM QR CODE
-- ============================================================

CREATE DATABASE IF NOT EXISTS pyrosync;
USE pyrosync;

-- Desativa as travas de chave estrangeira para limpar o banco sem erros
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Relatorios_Inspecao;
DROP TABLE IF EXISTS Inspecoes;
DROP TABLE IF EXISTS Extintores;
DROP TABLE IF EXISTS Brigadistas;
DROP TABLE IF EXISTS Treinamentos;
SET FOREIGN_KEY_CHECKS = 1; -- Reativa as travas de segurança

-- ============================================================
-- 1. TABELA DE BRIGADISTAS (Para: GET e POST /brigadistas)
-- ============================================================
CREATE TABLE Brigadistas (
    id_brigadista INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    setor VARCHAR(50) NOT NULL,
    senha VARCHAR(255) NOT NULL,
    telefone VARCHAR(20) NULL,
    email VARCHAR(100) NULL,
    whatsapp VARCHAR(20) NULL
);

-- ============================================================
-- 2. TABELA DE EXTINTORES (Para: GET /extintores, /vencidos e /analise-vencimentos)
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
-- 3. TABELA DE TREINAMENTOS (Para: POST /treinamentos)
-- ============================================================
CREATE TABLE Treinamentos (
    id_treinamento INT AUTO_INCREMENT PRIMARY KEY,
    id_brigadista INT NOT NULL, -- Chave adicionada para vincular ao brigadista
    nome_treinamento VARCHAR(100) NOT NULL,
    data_treinamento DATE NOT NULL,
    carga_horaria INT NOT NULL,
    instrutor VARCHAR(100) NOT NULL,
    FOREIGN KEY (id_brigadista) REFERENCES Brigadistas(id_brigadista) ON DELETE CASCADE
);

-- ============================================================
-- 4. TABELA DE INSPEÇÕES (Para: POST /inspecoes)
-- ============================================================
CREATE TABLE Inspecoes (
    id_inspecao INT AUTO_INCREMENT PRIMARY KEY,
    id_brigadista INT NULL,
    id_extintor INT NOT NULL,
    data_inspecao DATE NOT NULL,
    data_vencimento DATE NULL,
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
-- 5. TABELA DE RELATÓRIOS (Para: GET /relatorios)
-- ============================================================
CREATE TABLE Relatorios_Inspecao (
    id_relatorio INT AUTO_INCREMENT PRIMARY KEY,
    id_inspecao INT NOT NULL,
    situacao VARCHAR(100) NOT NULL,
    FOREIGN KEY (id_inspecao) REFERENCES Inspecoes(id_inspecao) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- 6. AUTOMATIZAÇÃO (TRIGGERS)
-- ============================================================
DELIMITER $$

-- GATILHO 1: Calcula o vencimento de 1 ano antes de salvar a inspeção
CREATE TRIGGER tg_calcular_vencimento
BEFORE INSERT ON Inspecoes
FOR EACH ROW
BEGIN
    SET NEW.data_vencimento = DATE_ADD(NEW.data_inspecao, INTERVAL 1 YEAR);
END$$

-- GATILHO 2: Gera o relatório de SST automaticamente após a inspeção
CREATE TRIGGER tg_gerar_relatorio
AFTER INSERT ON Inspecoes
FOR EACH ROW
BEGIN
    DECLARE v_situacao VARCHAR(100);
    
    IF NEW.status_manometro = 'Normal' 
       AND NEW.status_lacre = 'Intacto' 
       AND NEW.status_bocal = 'Desobstruído' 
       AND NEW.avaria_externa = 'Nenhuma' THEN
        SET v_situacao = 'Equipamento aprovado para uso';
    ELSE
        SET v_situacao = 'Equipamento reprovado - Necessita manutenção';
    END IF;

    INSERT INTO Relatorios_Inspecao (id_inspecao, situacao)
    VALUES (NEW.id_inspecao, v_situacao);
END$$

DELIMITER ;

-- ============================================================
-- 7. CARGA DE DADOS DE TESTE (Para alimentar os métodos GET de início)
-- ============================================================

-- Inserindo Brigadista Base (ID 1020)
INSERT INTO Brigadistas (id_brigadista, nome, setor, senha, telefone, email, whatsapp)
VALUES (1020, 'Victor Augusto', 'Segurança do Trabalho', 'pbkdf2:sha256:600000$examplehash', '3199297-5647', 'victor@pyrosync.com', '3199297-5647');

-- Inserindo Extintores (Normais e um Vencido para simular a rota /extintores/vencidos)
INSERT INTO Extintores 
(id_extintor, qr_code, numero_serie, fabricante, tipo, classificacao, capacidade_carga, unidade_medida, data_fabricacao, data_validade_carga, localizacao_atual, status_equipamento)
VALUES
(5001, 'QR-5001', 'AG-1111-2026', 'Resil', 'Água', 'A', 10.00, 'L', '2025-01-10', '2027-01-10', 'Galpão de Armazenamento', 'Ativo'),
(5002, 'QR-5002', 'CO-2222-2026', 'Kidde', 'CO2', 'BC', 6.00, 'KG', '2024-05-20', '2026-05-20', 'Sala do Servidor (TI)', 'Ativo'),
(5003, 'QR-5003', 'PQ-3333-2026', 'Bucka', 'Pó Químico PQS', 'ABC', 4.00, 'KG', '2025-03-15', '2027-03-15', 'Recepção Principal', 'Ativo'),
(5004, 'QR-5004', 'PQ-4444-2026', 'Mocelin', 'Pó Químico PQS', 'ABC', 8.00, 'KG', '2023-11-12', '2024-11-12', 'Oficina de Manutenção', 'Ativo'); -- VENCIDO (2024)

-- REGISTRO DE TREINAMENTO VINCULADO AO BRIGADISTA 1020
INSERT INTO Treinamentos (id_brigadista, nome_treinamento, data_treinamento, carga_horaria, instrutor)
VALUES (1020, 'Primeiros Socorros e Resgate', '2026-04-10', 8, 'Tenente Oliveira');

-- Simulando Inspeção Inicial (Ativará os Triggers e criará o primeiro Relatório)
INSERT INTO Inspecoes 
(id_brigadista, id_extintor, data_inspecao, hora_inspecao, numero_lacre, confirmar_tipo, status_manometro, status_lacre, status_bocal, avaria_externa, observacoes)
VALUES
(1020, 5003, '2026-06-16', '19:15:00', 'LAC-9999', 1, 'Normal', 'Intacto', 'Desobstruído', 'Nenhuma', 'Equipamento testado e aprovado no workshop.');
