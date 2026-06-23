-- ============================================================
-- SISTEMA PYROSYNC - INSPEÇÃO DE EXTINTORES COM QR CODE
-- ============================================================

CREATE DATABASE IF NOT EXISTS pyrosync;
USE pyrosync;

-- Apaga as tabelas/views antigas se existirem (ordem correta por causa das FKs)
DROP VIEW IF EXISTS vw_extintores_analise_vencimentos;
DROP VIEW IF EXISTS vw_extintores_vencidos;
DROP TABLE IF EXISTS Relatorios_Treinamentos;
DROP TABLE IF EXISTS Relatorios_Inspecao;
DROP TABLE IF EXISTS Registros_Treinamento;
DROP TABLE IF EXISTS Inspecoes;
DROP TABLE IF EXISTS Extintores;
DROP TABLE IF EXISTS Brigadistas;

-- ============================================================
-- 1. TABELA DE BRIGADISTAS (Rota: /brigadistas)
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
-- 2. TABELA DE EXTINTORES (Rota: /extintores)
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
    data_validade_carga DATE NOT NULL, -- Data crucial para controle de vencimento
    localizacao_atual VARCHAR(100) NOT NULL,
    status_equipamento ENUM(
        'Ativo',
        'Em Manutenção',
        'Descartado/Inativo'
    ) DEFAULT 'Ativo'
);

-- ============================================================
-- 3. TABELA DE INSPEÇÕES (Rota: /inspecoes)
-- ============================================================

CREATE TABLE Inspecoes (
    id_inspecao INT AUTO_INCREMENT PRIMARY KEY,
    id_brigadista INT NULL,
    id_extintor INT NOT NULL,
    data_inspecao DATE NOT NULL,
    data_vencimento DATE NULL, -- Preenchido automaticamente pelo Gatilho 1
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
-- 4. TABELA DE RELATÓRIOS DE INSPEÇÃO (Rota: /relatorios, /relatorios-inspecoes)
-- ============================================================

CREATE TABLE Relatorios_Inspecao (
    id_relatorio INT AUTO_INCREMENT PRIMARY KEY,
    id_inspecao INT NOT NULL,
    situacao VARCHAR(100) NOT NULL,
    data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_inspecao) REFERENCES Inspecoes(id_inspecao) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- 5. TABELA DE TREINAMENTOS (Rota: /treinamentos)
-- Esta tabela faltava no script original -- a FK de Relatorios_Treinamentos
-- e o INSERT de teste já apontavam para ela, mas ela nunca era criada.
-- Colunas carga_horaria/instrutor incluídas porque o app.py já as consulta
-- em /relatorios-treinamentos e /relatorios-treinamentos/<id>.
-- ============================================================

CREATE TABLE Registros_Treinamento (
    id_treinamento INT AUTO_INCREMENT PRIMARY KEY,
    id_brigadista INT NOT NULL,
    nome_treinamento VARCHAR(150) NOT NULL,
    data_treinamento DATE NOT NULL,
    data_vencimento DATE NULL, -- Calculado em Python (data_treinamento + 1 ano)
    carga_horaria INT NULL,
    instrutor VARCHAR(100) NULL,
    FOREIGN KEY (id_brigadista) REFERENCES Brigadistas(id_brigadista) ON DELETE CASCADE
);

-- ============================================================
-- 6. TABELA DE RELATÓRIOS DE TREINAMENTOS
-- ============================================================

CREATE TABLE Relatorios_Treinamentos (
    id_relatorio_treinamento INT AUTO_INCREMENT PRIMARY KEY,
    id_treinamento INT NOT NULL,
    situacao VARCHAR(100) NOT NULL,
    data_relatorio DATE NOT NULL,
    observacoes TEXT,
    FOREIGN KEY (id_treinamento)
        REFERENCES Registros_Treinamento(id_treinamento)
        ON DELETE CASCADE
);

-- ============================================================
-- 7. AUTOMATIZAÇÃO (TRIGGERS)
-- ============================================================

DELIMITER $$

-- GATILHO 1: Calcula o vencimento de 1 ano ANTES de salvar a inspeção
CREATE TRIGGER tg_calcular_vencimento
BEFORE INSERT ON Inspecoes
FOR EACH ROW
BEGIN
    SET NEW.data_vencimento = DATE_ADD(NEW.data_inspecao, INTERVAL 1 YEAR);
END$$

-- GATILHO 2: Gera automaticamente a situação na tabela Relatorios_Inspecao
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
-- 8. VIEWS PARA SUPORTE ÀS ROTAS DA FOTO (GET)
-- ============================================================

-- Rota: GET /extintores/vencidos
CREATE VIEW vw_extintores_vencidos AS
SELECT id_extintor, qr_code, numero_serie, tipo, data_validade_carga, localizacao_atual
FROM Extintores
WHERE data_validade_carga < CURDATE() AND status_equipamento = 'Ativo';

-- Rota: GET /extintores/analise-vencimentos
CREATE VIEW vw_extintores_analise_vencimentos AS
SELECT
    id_extintor,
    qr_code,
    numero_serie,
    tipo,
    data_validade_carga,
    DATEDIFF(data_validade_carga, CURDATE()) AS dias_para_vencer,
    CASE
        WHEN data_validade_carga < CURDATE() THEN 'Vencido'
        WHEN DATEDIFF(data_validade_carga, CURDATE()) <= 30 THEN 'Alerta: Vence em menos de 30 dias'
        ELSE 'Regular'
    END AS status_vencimento
FROM Extintores;

-- ============================================================
-- 9. INSERÇÃO DE DADOS PARA TESTE
-- ============================================================

-- Inserindo Brigadista
INSERT INTO Brigadistas (id_brigadista, nome, setor, senha, telefone, email, whatsapp)
VALUES (1020, 'Victor Augusto', 'Segurança do Trabalho', 'pbkdf2:sha256:600000$examplehash', '3199297-5647', 'victor@pyrosync.com', '3199297-5647');

-- Inserindo Treinamento para o Brigadista
INSERT INTO Registros_Treinamento (id_brigadista, nome_treinamento, data_treinamento, data_vencimento, carga_horaria, instrutor)
VALUES (1020, 'Treinamento de Brigada de Incêndio - NR 23', '2026-01-15', '2027-01-15', 8, 'Carlos Mendes');

-- Inserindo Extintores (Incluindo um propositalmente vencido para testar as rotas)
INSERT INTO Extintores
(id_extintor, qr_code, numero_serie, fabricante, tipo, classificacao, capacidade_carga, unidade_medida, data_fabricacao, data_validade_carga, localizacao_atual, status_equipamento)
VALUES
(5001, 'QR-5001', 'AG-1111-2026', 'Resil', 'Água', 'A', 10.00, 'L', '2025-01-10', '2027-01-10', 'Galpão de Armazenamento', 'Ativo'),
(5002, 'QR-5002', 'CO-2222-2026', 'Kidde', 'CO2', 'BC', 6.00, 'KG', '2024-05-20', '2026-05-20', 'Sala do Servidor (TI)', 'Ativo'), -- Vencido em relação a Junho/2026
(5003, 'QR-5003', 'PQ-3333-2026', 'Bucka', 'Pó Químico PQS', 'ABC', 4.00, 'KG', '2025-03-15', '2027-03-15', 'Recepção Principal', 'Ativo'),
(5004, 'QR-5004', 'PQ-4444-2026', 'Mocelin', 'Pó Químico PQS', 'ABC', 8.00, 'KG', '2023-11-12', '2026-07-15', 'Oficina de Manutenção', 'Ativo'); -- Vence em breve

-- Simulação de uma Inspeção realizada via API (POST /inspecoes)
INSERT INTO Inspecoes
(id_brigadista, id_extintor, data_inspecao, hora_inspecao, numero_lacre, confirmar_tipo, status_manometro, status_lacre, status_bocal, avaria_externa, observacoes)
VALUES
(1020, 5003, '2026-06-16', '19:15:00', 'LAC-9999', 1, 'Normal', 'Intacto', 'Desobstruído', 'Nenhuma', 'Equipamento testado e aprovado no workshop.');

-- ============================================================
-- 10. QUERIES DE VERIFICAÇÃO (Simulando as chamadas das Rotas)
-- ============================================================

-- Simula: GET /extintores/vencidos
SELECT * FROM vw_extintores_vencidos;

-- Simula: GET /extintores/analise-vencimentos
SELECT * FROM vw_extintores_analise_vencimentos;

-- Simula: GET /relatorios
SELECT

    r.id_relatorio,
    e.qr_code,
    i.data_inspecao,
    r.situacao
FROM Relatorios_Inspecao r
JOIN Inspecoes i ON r.id_inspecao = i.id_inspecao
JOIN Extintores e ON i.id_extintor = e.id_extintor;

-- Simula consulta de Treinamentos vinculados ao brigadista
SELECT b.nome, t.nome_treinamento, t.data_vencimento
FROM Registros_Treinamento t
JOIN Brigadistas b ON t.id_brigadista = b.id_brigadista;