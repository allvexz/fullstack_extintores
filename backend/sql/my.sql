
-- Cria o banco de dados do sistema PyroSync
CREATE DATABASE pyrosync;

-- Define o charset para suportar caracteres especiais (ã, ç, é, etc.)
ALTER DATABASE pyrosync CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Seleciona o banco para uso
USE pyrosync;

-- =========================
-- TABELA DE BRIGADISTAS
-- =========================

-- Armazena os responsáveis pelas inspeções de extintores
CREATE TABLE pyrosync.brigadistas (
    id_brigadista INT PRIMARY KEY AUTO_INCREMENT, -- Identificador único do brigadista
    nome          VARCHAR(100) NOT NULL,          -- Nome completo do brigadista
    data_cadastro DATE NOT NULL                   -- Data em que o brigadista foi registrado no sistema
);

-- =========================
-- TABELA DE EXTINTORES
-- =========================

-- Armazena os extintores cadastrados para inspeção
CREATE TABLE pyrosync.extintores (
    id_extintor   INT PRIMARY KEY AUTO_INCREMENT, -- Identificador único do extintor
    tipo_extintor VARCHAR(50) NOT NULL,           -- Tipo do extintor (ex: Po Quimico ABC, CO2)
    data_validade DATE NOT NULL                   -- Data de validade do extintor
);

-- =========================
-- TABELA DE INSPEÇÕES
-- =========================

-- Registra cada inspeção realizada em um extintor por um brigadista
CREATE TABLE pyrosync.inspecoes (
    id_inspecao    INT PRIMARY KEY AUTO_INCREMENT,  -- Identificador único da inspeção

    id_extintor    INT NOT NULL,                    -- Referência ao extintor inspecionado
    id_brigadista  INT NOT NULL,                    -- Referência ao brigadista responsável

    -- Itens verificados durante a inspeção
    -- CHECK garante que só aceita 'Sim' ou 'Nao', sem depender de charset
    manometro       VARCHAR(20) NOT NULL,                                          -- Leitura do manômetro (ex: OK, BAIXO, ALTO)
    bocal_obstruido VARCHAR(3)  NOT NULL CHECK (bocal_obstruido IN ('Sim','Nao')), -- Indica se o bocal está obstruído
    lacre_violado   VARCHAR(3)  NOT NULL CHECK (lacre_violado   IN ('Sim','Nao')), -- Indica se o lacre de segurança foi violado
    avaria_externa  VARCHAR(3)  NOT NULL CHECK (avaria_externa  IN ('Sim','Nao')), -- Indica se há danos visíveis na estrutura externa

    data_inspecao  DATE NOT NULL,                   -- Data em que a inspeção foi realizada

    -- Chave estrangeira: garante que o extintor informado existe na tabela extintores
    CONSTRAINT fk_extintor
        FOREIGN KEY (id_extintor)
        REFERENCES pyrosync.extintores(id_extintor),

    -- Chave estrangeira: garante que o brigadista informado existe na tabela brigadistas
    CONSTRAINT fk_brigadista
        FOREIGN KEY (id_brigadista)
        REFERENCES pyrosync.brigadistas(id_brigadista)
);

-- =========================
-- DADOS DE TESTE
-- =========================

-- Insere dois brigadistas para simular o uso do sistema
INSERT INTO pyrosync.brigadistas (nome, data_cadastro)
VALUES
('Victor Augusto', '2026-05-11'),
('Leonardo Alves', '2026-05-12');

-- Insere dois extintores de tipos diferentes para teste
INSERT INTO pyrosync.extintores (tipo_extintor, data_validade)
VALUES
('Po Quimico ABC', '2027-10-20'),
('CO2', '2028-01-15');

-- Insere duas inspeções:
-- Inspeção 1: Extintor 1 inspecionado por Victor — todos os itens OK
-- Inspeção 2: Extintor 2 inspecionado por Leonardo — lacre violado detectado
INSERT INTO pyrosync.inspecoes (
    id_extintor,
    id_brigadista,
    manometro,
    bocal_obstruido,
    lacre_violado,
    avaria_externa,
    data_inspecao
)
VALUES
(1, 1, 'OK', 'Nao', 'Nao', 'Nao', '2026-05-11'),
(2, 2, 'OK', 'Nao', 'Sim', 'Nao', '2026-05-12');

-- =========================
-- CONSULTA COMPLETA COM STATUS
-- =========================

-- Retorna todas as inspeções com os dados do brigadista, do extintor
-- e um status automático calculado com base nos itens verificados
SELECT
    i.id_inspecao,
    b.nome          AS brigadista,    -- Nome do brigadista responsável
    e.tipo_extintor,                  -- Tipo do extintor inspecionado
    i.manometro,
    i.bocal_obstruido,
    i.lacre_violado,
    i.avaria_externa,
    i.data_inspecao,

    -- Status calculado automaticamente: verifica cada item em ordem de criticidade
    -- O primeiro problema encontrado define o motivo da reprovação
    CASE
        WHEN UPPER(i.manometro)  <> 'OK'  THEN 'REPROVADO - Manometro com problema'
        WHEN i.bocal_obstruido   = 'Sim'  THEN 'REPROVADO - Bocal obstruido'
        WHEN i.lacre_violado     = 'Sim'  THEN 'REPROVADO - Lacre violado'
        WHEN i.avaria_externa    = 'Sim'  THEN 'REPROVADO - Avaria externa'
        ELSE 'APROVADO'                       -- Aprovado somente se todos os itens estiverem OK
    END AS status_inspecao

FROM pyrosync.inspecoes i

-- JOIN para trazer o nome do brigadista
INNER JOIN pyrosync.brigadistas b
    ON i.id_brigadista = b.id_brigadista

-- JOIN para trazer o tipo do extintor
INNER JOIN pyrosync.extintores e
    ON i.id_extintor = e.id_extintor;
