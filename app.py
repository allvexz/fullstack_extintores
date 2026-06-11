from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
# Importamos o relativedelta para calcular +1 ano de forma precisa (controlando anos bissextos)
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
# from twilio.rest import Client # Descomente após instalar: pip install twilio

# Carrega as variáveis do arquivo .env automaticamente
load_dotenv()

app = Flask(_name_)

# Configuração puxando diretamente do arquivo .env configurado
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_DATABASE", "pyrosync")
}
# Configuração Twilio (Placeholder)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_FROM = os.getenv("TWILIO_PHONE_FROM")

def enviar_notificacao_manutencao(extintor_id, motivo):
    """Função para enviar alerta via Twilio quando um extintor é reprovado."""
    # if not TWILIO_ACCOUNT_SID: return
    # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # message = client.messages.create(
    #     body=f"Alerta Pyrosync: Extintor {extintor_id} reprovado! Motivo: {motivo}",
    #     from_=TWILIO_PHONE_FROM,
    #     to=os.getenv("ADMIN_PHONE")
    # )
    print(f"DEBUG: Enviando alerta para extintor {extintor_id}: {motivo}")
    pass

# ============================================================
# ROTAS: BRIGADISTAS [Dev / Sec]
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
        
    # ATUALIZAÇÃO [Dev]: Adicionados os novos atributos exigidos pelo quadro
    campos_obrigatorios = ['nome', 'setor', 'senha', 'telefone', 'email', 'whatsapp']
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({'erro': f'Campo obrigatório: {campo}'}), 400

    senha_hash = generate_password_hash(dados['senha'])

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # ATUALIZAÇÃO [Dev]: Query alterada para persistir as novas colunas
        q = """INSERT INTO Brigadistas (nome, setor, senha, telefone, email, whatsapp) 
               VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(q, (dados['nome'], dados['setor'], senha_hash, 
                       dados['telefone'], dados['email'], dados['whatsapp']))
        conn.commit()
        return jsonify({'mensagem': 'Brigadista cadastrado com sucesso'}), 201
    except Error as e:
        return jsonify({'erro': 'Erro no banco de dados', 'detalhes': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ============================================================
# NOVA ROTA [DBA / Dev]: REGISTRO DE TREINAMENTOS (Tabela Fato)
# ============================================================

@app.route('/treinamentos', methods=['POST'])
def criar_treinamento():
    dados = request.get_json()
    if not dados:
        return jsonify({'erro': 'JSON ausente'}), 400
        
    campos_obrigatorios = ['id_brigadista', 'nome_treinamento', 'data_treinamento']
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({'erro': f'Campo obrigatório: {campo}'}), 400

    try:
        # Converte a string recebida (ex: "2026-06-11") para um objeto date do Python
        data_treinamento_obj = datetime.strptime(dados['data_treinamento'], '%Y-%m-%d').date()
        
        # LÓGICA DE NEGÓCIO EXIGIDA: Calcula o vencimento adicionando exatamente 1 ano (12 meses)
        data_vencimento_obj = data_treinamento_obj + relativedelta(years=1)
        
        # Converte de volta para string no formato do MySQL (YYYY-MM-DD)
        data_vencimento_str = data_vencimento_obj.strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({'erro': 'Formato de data inválido. Use AAAA-MM-DD'}), 400

    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Insere na tabela fato de registros/treinamentos salvando a data calculada
        q = """INSERT INTO Registros_Treinamento (id_brigadista, nome_treinamento, data_treinamento, data_vencimento) 
               VALUES (%s, %s, %s, %s)"""
        cursor.execute(q, (dados['id_brigadista'], dados['nome_treinamento'], 
                       dados['data_treinamento'], data_vencimento_str))
        conn.commit()
        
        return jsonify({
            'mensagem': 'Treinamento registrado com sucesso!',
            'data_treinamento': dados['data_treinamento'],
            'data_vencimento_calculada': data_vencimento_str
        }), 201
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

@app.route('/extintores/analise-vencimentos', methods=['GET'])
def analise_vencimentos():
    """Calcula prazos e status de validade de todos os extintores."""
    q = "SELECT id_extintor, numero_serie, data_validade_carga, localizacao_atual FROM Extintores"
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q)
        extintores = cursor.fetchall()
        
        hoje = datetime.now().date()
        resultado = []
        for ex in extintores:
            validade = ex['data_validade_carga']
            dias_restantes = (validade - hoje).days
            status = "OK" if dias_restantes > 30 else "CRÍTICO" if dias_restantes >= 0 else "VENCIDO"
            
            ex['dias_para_vencer'] = dias_restantes
            ex['situacao_validade'] = status
            resultado.append(ex)
            
        return jsonify(resultado), 200
    except Error as e:
        return jsonify({'erro': 'Erro no cálculo', 'detalhes': str(e)}), 500
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
            enviar_notificacao_manutencao(dados['id_extintor'], situacao_final)
        else:
            situacao_final = "Equipamento aprovado para uso"
        # 3. Verificar se a trigger do banco gerou o relatório; se não, inserir (fallback).
        cursor.execute("SELECT COUNT(*) FROM Relatorios_Inspecao WHERE id_inspecao = %s", (id_nova_inspecao,))
        existe = cursor.fetchone()[0]
        if not existe:
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='Relatorios_Inspecao'", (db_config.get('database'),))
            cols = [row[0].lower() for row in cursor.fetchall()]

            fields = ['id_inspecao', 'situacao']
            params = [id_nova_inspecao, situacao_final]

            if 'data_relatorio' in cols:
                from datetime import date
                data_rel = dados.get('data_inspecao') or date.today().isoformat()
                fields.append('data_relatorio')
                params.append(data_rel)

            if 'id_extintor' in cols and 'id_extintor' not in [f.lower() for f in fields]:
                fields.append('id_extintor')
                params.append(dados['id_extintor'])

            sql = f"INSERT INTO Relatorios_Inspecao ({', '.join(fields)}) VALUES ({', '.join(['%s']*len(fields))})"
            cursor.execute(sql, tuple(params))
        
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
# ROTA DE CONSULTA DO RELATÓRIO FINAL
# ============================================================

@app.route('/relatorios', methods=['GET'])
def listar_relatorios_finais():
    q = """SELECT e.qr_code AS QR_Code, e.numero_serie AS Extintor, e.localizacao_atual AS Localizacao, 
                  i.status_lacre AS Lacre, i.status_manometro AS Manometro, i.status_bocal AS Bocal, 
                  b.nome AS Responsavel, i.data_inspecao AS Data, r.situacao AS Situacao 
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