from flask import Flask, request, jsonify
import mysql.connector
#Importa a biblioteca para conectar ao MySQL. mysql.connector é um conector oficial do MySQL para Python, que permite que você se conecte a um banco de dados MySQL e execute consultas SQL.

# No terminal, instale o Flask e o mysql-connector-python usando pip:
# pip install Flask mysql-connector-python. esse comando instala as bibliotecas necessárias para criar a API com Flask e para conectar ao banco de dados MySQL usando mysql.connector. O Flask é um microframework leve para criar APIs web, enquanto o mysql-connector-python é a biblioteca oficial do MySQL para Python, que facilita a conexão e a execução de consultas SQL em um banco de dados MySQL.

# Importando as bibliotecas necessárias para criar a API e lidar com o banco de dados
#flask é o microframework para criar a API, request para pegar os dados enviados pelo cliente, jsonify para retornar respostas em formato JSON
#request e jsonify são funções do Flask para lidar com requisições e respostas HTTP, respectivamente.

app = Flask(__name__) 

# Criando a aplicação Flask, que é o núcleo da nossa API. O nome __name__ é uma convenção do Python que indica o nome do módulo atual, e é usado para configurar a aplicação corretamente.

# Configuração do Banco de Dados - Centralizada para evitar erros, facilitar manutenção e garantir segurança (evitando SQL Injection)

db_config = {
    'host': 'localhost',
    # O endereço do servidor MySQL (pode ser 'localhost' se estiver rodando localmente) ou o IP do servidor onde o MySQL está hospedado.
    'database': 'INF07SST',
    # O nome do banco de dados que você criou para armazenar as tabelas DimFuncionarios, DimTreinamentos e FactRegistros. o Schema do banco de dados é o nome do banco onde as tabelas estão criadas.
    'user': 'root', 
    # O nome de usuário do MySQL (geralmente 'root' para instalações locais, mas pode ser diferente dependendo da configuração do seu MySQL).
    'password': '115088' 
    # Coloque sua senha aqui, se você tiver configurado uma senha para o usuário do MySQL. Se estiver usando uma instalação local sem senha, deixe em branco.
}

def get_db_connection(): 
    # Função para obter uma conexão com o banco de dados usando as configurações definidas acima. 
    #Função auxiliar para abrir conexão sempre que necessário.
    return mysql.connector.connect(**db_config)
    #A função get_db_connection() é uma função auxiliar que cria e retorna uma nova conexão com o banco de dados MySQL usando as configurações definidas em db_config. O uso de **db_config permite passar os parâmetros do dicionário como argumentos nomeados para a função mysql.connector.connect(), facilitando a manutenção e evitando erros de digitação ao criar conexões em diferentes partes do código.

# =========================================================
# CLASSES (MODELOS) - A definição dos nossos objetos
# =========================================================

# Definindo a planta baixa (Classe) para Funcionários
class Funcionario:
    # __init__ é o construtor: ele "constrói" o objeto quando o chamamos
    # self refere-se ao objeto que estamos criando naquele momento
    # id=None é um valor padrão: se não passarmos um ID, ele assume None (útil para novos registros que ainda não têm ID)
    def __init__(self, nome, cpf, cargo, setor, id=None):
        self.id = id # Armazena o ID (None para novos, um número para existentes)
        self.nome = nome # Atribui o nome passado na criação ao atributo do objeto
        self.cpf = cpf # Atribui o CPF
        self.cargo = cargo # Atribui o cargo
        self.setor = setor # Atribui o setor

# Definindo a planta baixa para Treinamentos
class Treinamento:
    def __init__(self, nome_treinamento, validade_meses, id=None):
        self.id = id
        self.nome_treinamento = nome_treinamento
        self.validade_meses = validade_meses

# Definindo a planta baixa para os Registros (a tabela Fato)
class Registro:
    # status='Ativo' é um valor padrão: se não dissermos nada, ele assume 'Ativo'
    def __init__(self, id_funcionario, id_treinamento, data_realizacao, status='Ativo', id=None):
        self.id = id
        self.id_funcionario = id_funcionario # Guarda quem fez (chave estrangeira)
        self.id_treinamento = id_treinamento # Guarda o que fez (chave estrangeira)
        self.data_realizacao = data_realizacao # Guarda quando fez
        self.status = status # Guarda o estado atual (ex: ativo ou vencido)