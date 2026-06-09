from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env automaticamente
load_dotenv()

app = Flask(__name__)

# Configuração puxando diretamente do arquivo .env configurado
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_DATABASE", "pyrosync")
}

# ============================================================
# ROTAS: BRIGADISTAS
# ============================================================

@app.route('/brigadistas', methods=['GET'])
def listar_brigadistas():
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Brigadistas")
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/brigadistas', methods=['POST'])
def criar_brigadista():
    dados = request.get_json()
    if not dados:
        return jsonify({'erro': 'JSON ausente'}), 400
        
    for campo in ['nome', 'setor']:
        if campo not in dados:
            return jsonify({'erro': f'Campo obrigatório: {campo}'}), 400

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Brigadistas (nome, setor) VALUES (%s, %s)", 
                       (dados['nome'], dados['setor']))
        conn.commit()
        return jsonify({'mensagem': 'Brigadista cadastrado'}), 201
    except Error as e:
        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ============================================================
# ROTAS: EXTINTORES
# ============================================================

@app.route('/extintores', methods=['GET'])
def listar_extintores():
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Extintores")
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/extintores/vencidos', methods=['GET'])
def listar_extintores_vencidos():
    hoje = datetime.now().strftime('%Y-%m-%d')
    q = "SELECT * FROM Extintores WHERE data_validade_carga < %s ORDER BY data_validade_carga ASC"
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q, (hoje,))
        res = cursor.fetchall()
        return jsonify({"data_verificacao": hoje, "total_vencidos": len(res), "extintores": res}), 200
    except Error as e:
        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ============================================================
# RECURSO AVANÇADO: REGISTRO DE INSPEÇÃO E RELATÓRIO AUTOMÁTICO
# ============================================================

@app.route('/inspecoes', methods=['POST'])
def criar_inspecao():
    dados = request.get_json()
    campos_obrigatorios = [
        'id_extintor', 'data_inspecao', 'hora_inspecao', 'numero_lacre', 
        'confirmar_tipo', 'status_manometro', 'status_lacre', 'status_bocal', 'avaria_externa'
    ]
    
    if not dados:
        return jsonify({'erro': 'JSON ausente'}), 400
        
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({'erro': f'Campo obrigatório: {campo}'}), 400

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 1. Inserir na tabela Inspecoes
        q_inspecao = """INSERT INTO Inspecoes (id_brigadista, id_extintor, data_inspecao, hora_inspecao, numero_lacre, 
                       confirmar_tipo, status_manometro, status_lacre, status_bocal, avaria_externa, observacoes) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        p_inspecao = (
            dados.get('id_brigadista'), dados['id_extintor'], dados['data_inspecao'], dados['hora_inspecao'], 
            dados['numero_lacre'], dados['confirmar_tipo'], dados['status_manometro'], dados['status_lacre'], 
            dados['status_bocal'], dados['avaria_externa'], dados.get('observacoes')
        )
        cursor.execute(q_inspecao, p_inspecao)
        id_nova_inspecao = cursor.lastrowid

        # 2. LÓGICA DE AVALIAÇÃO AUTOMÁTICA
        motivos_reprovacao = []
        if dados['status_manometro'] != 'Normal': 
            motivos_reprovacao.append(f"Manômetro {dados['status_manometro']}")
        if dados['status_lacre'] != 'Intacto': 
            motivos_reprovacao.append(f"Lacre {dados['status_lacre']}")
        if dados['status_bocal'] != 'Desobstruído': 
            motivos_reprovacao.append(f"Bocal {dados['status_bocal']}")
        if dados['avaria_externa'] != 'Nenhuma': 
            motivos_reprovacao.append(f"Avaria: {dados['avaria_externa']}")
        
        if motivos_reprovacao:
            situacao_final = f"REPROVADO: {', '.join(motivos_reprovacao)}"
            cursor.execute("UPDATE Extintores SET status_equipamento = 'Em Manutenção' WHERE id_extintor = %s", (dados['id_extintor'],))
        else:
            situacao_final = "Equipamento aprovado para uso"

        # 3. Gerar na tabela Relatorios_Inspecao INCLUINDO o id_extintor exigido pelo banco
        q_relatorio = "INSERT INTO Relatorios_Inspecao (id_inspecao, id_extintor, data_relatorio, situacao) VALUES (%s, %s, %s, %s)"
        cursor.execute(q_relatorio, (id_nova_inspecao, dados['id_extintor'], dados['data_inspecao'], situacao_final))
        
        conn.commit()
        return jsonify({
            'mensagem': 'Inspeção realizada com sucesso!',
            'resultado_analise': situacao_final
        }), 201
        
    except Error as e:
        if conn:
            conn.rollback()
        return jsonify({'erro': 'Erro ao processar inspeção', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ============================================================
# ROTA DE CONSULTA DO RELATÓRIO FINAL (QUERY DO PROFESSOR)
# ============================================================

@app.route('/relatorios', methods=['GET'])
def listar_relatorios_finais():
    q = """SELECT e.qr_code AS QR_Code, e.numero_serie AS Extintor, e.localizacao_atual AS Localizacao, 
                  i.status_lacre AS Lacre, i.status_manometro AS Manometro, i.status_bocal AS Bocal, 
                  b.nome AS Responsavel, r.data_relatorio AS Data, r.situacao AS Situacao 
           FROM Relatorios_Inspecao r 
           INNER JOIN Inspecoes i ON r.id_inspecao = i.id_inspecao 
           INNER JOIN Extintores e ON i.id_extintor = e.id_extintor 
           LEFT JOIN Brigadistas b ON i.id_brigadista = b.id_brigadista"""
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q)
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({'erro': 'Erro ao buscar relatórios', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)