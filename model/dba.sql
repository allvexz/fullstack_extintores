#CRIAÇÃO DO BANCO DE DADOS
DROP DATABASE IF EXISTS pyrosync;
CREATE DATABASE pyrosync;
USE pyrosync;

-- 2. TABELA DE BRIGADISTAS
CREATE TABLE Brigadistas (
    id_brigadista INT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    setor VARCHAR(50) NOT NULL
);

-- 3. TABELA DE EXTINTORES
CREATE TABLE Extintores (
    id_extintor INT PRIMARY KEY,
    numero_serie VARCHAR(50) NOT NULL UNIQUE,
    fabricante VARCHAR(50) NOT NULL,
    tipo ENUM('Água', 'CO2', 'Pó Químico PQS', 'Espuma Mecânica', 'Compostos Halogenados') NOT NULL,
    classificacao VARCHAR(10) NOT NULL,
    capacidade_carga DECIMAL(5,2) NOT NULL,
    unidade_medida ENUM('KG','L') NOT NULL,
    data_fabricacao DATE NOT NULL,
    data_validade_carga DATE NOT NULL,
    localizacao_atual VARCHAR(100) NOT NULL,
    status_equipamento ENUM('Ativo', 'Em Manutenção', 'Descartado/Inativo') DEFAULT 'Ativo'
);

-- 4. TABELA DE INSPEÇÃO 
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
    observacoes TEXT NULL,
    FOREIGN KEY (id_brigadista) REFERENCES Brigadistas(id_brigadista) ON DELETE SET NULL,
    FOREIGN KEY (id_extintor) REFERENCES Extintores(id_extintor) ON DELETE CASCADE
);

-- ============================================================
--  INSERÇÃO DOS DADOS (1 BRIGADISTA + 4 EXTINTORES + VISTORIAS)
-- ============================================================

-- Cadastra o Brigadista (Tabela de ID)
INSERT INTO Brigadistas (id_brigadista, nome, setor) 
VALUES (1020, 'Victor Augusto', 'Segurança do Trabalho');

-- Cadastra os 4 Extintores de forma correta
INSERT INTO Extintores (id_extintor, numero_serie, fabricante, tipo, classificacao, capacidade_carga, unidade_medida, data_fabricacao, data_validade_carga, localizacao_atual, status_equipamento) VALUES 
(5001, 'AG-1111-2026', 'Resil', 'Água', 'A', 10.00, 'L', '2025-01-10', '2027-01-10', 'Galpão de Armazenamento', 'Ativo'),
(5002, 'CO-2222-2026', 'Kidde', 'CO2', 'BC', 6.00, 'KG', '2024-05-20', '2026-05-20', 'Sala do Servidor (TI)', 'Ativo'),
(5003, 'PQ-3333-2026', 'Bucka', 'Pó Químico PQS', 'ABC', 4.00, 'KG', '2025-03-15', '2027-03-15', 'Recepção Principal', 'Ativo'),
(5004, 'PQ-4444-2026', 'Mocelin', 'Pó Químico PQS', 'ABC', 8.00, 'KG', '2023-11-12', '2026-11-12', 'Oficina de Manutenção', 'Ativo');

-- Registra as Inspeções usando o nome "Inspecoes" com I maiúsculo
INSERT INTO Inspecoes (id_brigadista, id_extintor, data_inspecao, hora_inspecao, numero_lacre, confirmar_tipo, status_manometro, status_lacre, status_bocal, avaria_externa, observacoes) VALUES 
(1020, 5002, CURDATE(), CURTIME(), 'LAC-8888', 1, 'Normal', 'Intacto', 'Desobstruído', 'Nenhuma', 'Equipamento em perfeito estado.'),
(1020, 5003, CURDATE(), CURTIME(), 'LAC-9999', 1, 'Normal', 'Intacto', 'Desobstruído', 'Nenhuma', 'Pronto para uso operacional.');

-- ============================================================
--  CONSULTA PARA EXIBIR O RELATÓRIO NA TELA
-- ============================================================
SELECT i.id_inspecao, i.data_inspecao, b.nome AS nome_brigadista, e.tipo, e.localizacao_atual, i.status_manometro
FROM Inspecoes i
LEFT JOIN Brigadistas b ON i.id_brigadista = b.id_brigadista
INNER JOIN Extintores e ON i.id_extintor = e.id_extintor;