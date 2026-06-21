from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import os
import io
import base64
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import qrcode
from datetime import timedelta  # Adicione este import caso precise tratar o tempo puro

def converter_datas_e_horas(dados):
    """Transforma objetos de data, hora e timedelta do MySQL em texto legível para o JSON."""
    if isinstance(dados, list):
        for item in dados:
            converter_datas_e_horas(item)
    elif isinstance(dados, dict):
        for chave, valor in dados.items():
            if isinstance(valor, (date, datetime, timedelta)):
                dados[chave] = str(valor)
    return dados
# Carrega as variáveis do arquivo .env automaticamente
load_dotenv()

app = Flask(__name__)

# Configuração do Banco de Dados
# Suporta tanto DB_PASSWORD quanto DB_PASS no .env (compatibilidade com o guia do professor)
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD") or os.getenv("DB_PASS", ""),  # CORRIGIDO: suporta os dois nomes
    "database": os.getenv("DB_DATABASE") or os.getenv("DB_NAME", "pyrosync"),  # CORRIGIDO: suporta os dois nomes
}


def gerar_qr_code_base64(data: str) -> str:
    """Gera QR Code e retorna em base64 para exibir no frontend/app."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"


def enviar_notificacao_manutencao(extintor_id, motivo):
    """Envia alerta quando um extintor é reprovado (WhatsApp via Twilio)."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    sms_from = os.getenv("TWILIO_PHONE_FROM") or os.getenv("TWILIO_FROM")
    admin_phone = os.getenv("ADMIN_PHONE") or os.getenv("TWILIO_TO")

    if not (account_sid and auth_token and sms_from and admin_phone):
        print(
            "DEBUG: Twilio não configurado. "
            f"account_sid={bool(account_sid)} token={bool(auth_token)} "
            f"sms_from={bool(sms_from)} admin_phone={bool(admin_phone)}"
        )
        print(f"DEBUG: (stub) Enviando alerta para extintor {extintor_id}: {motivo}")
        return

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        print(f"DEBUG: Enviando de {sms_from} para {admin_phone}")

        # Função interna para garantir o formato whatsapp:+55...
        def formatar(num):
            num = str(num).strip()
            if not num.startswith("whatsapp:"):
                if not num.startswith("+"):
                    num = f"+{num}"
                num = f"whatsapp:{num}"
            return num

        remetente = formatar(sms_from)
        destinatario = formatar(admin_phone)

        message = client.messages.create(
            body=f"🚨 Extintor {extintor_id} reprovado. Motivo: {motivo}",
            from_=remetente,
            to=destinatario,
        )
        print(f"Twilio WhatsApp enviado! sid={message.sid}")
    except Exception as e:
        print(f"DEBUG: Falha ao enviar Twilio: {e}")


# ============================================================
# ROTAS: BRIGADISTAS
# ============================================================


@app.route("/brigadistas", methods=["GET"])
def listar_brigadistas():
    conn = None
    cursor = None  # CORRIGIDO: inicializa cursor como None para evitar erro no finally
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id_brigadista, nome, setor, telefone, email, whatsapp FROM Brigadistas"
        )
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({"erro": "Erro no banco de dados", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/brigadistas", methods=["POST"])
def criar_brigadista():
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "JSON ausente"}), 400

    campos_obrigatorios = ["nome", "setor", "senha", "telefone", "email", "whatsapp"]
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"Campo obrigatório: {campo}"}), 400

    senha_hash = generate_password_hash(dados["senha"])

    conn = None
    cursor = None  # CORRIGIDO
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        q = """
            INSERT INTO Brigadistas (nome, setor, senha, telefone, email, whatsapp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            q,
            (
                dados["nome"],
                dados["setor"],
                senha_hash,
                dados["telefone"],
                dados["email"],
                dados["whatsapp"],
            ),
        )
        conn.commit()
        return jsonify({"mensagem": "Brigadista cadastrado com sucesso"}), 201
    except Error as e:
        return jsonify({"erro": "Erro no banco de dados", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ============================================================
# ROTAS: TREINAMENTOS
# ============================================================


@app.route("/treinamentos", methods=["GET"])
def listar_treinamentos():
    """Lista todos os treinamentos registrados (útil para pegar id_treinamento)."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        q = """
            SELECT
                t.id_treinamento,
                t.id_brigadista,
                b.nome AS nome_brigadista,
                t.nome_treinamento,
                t.data_treinamento,
                t.data_vencimento,
                t.carga_horaria,
                t.instrutor
            FROM Registros_Treinamento t
            INNER JOIN Brigadistas b ON t.id_brigadista = b.id_brigadista
            ORDER BY t.data_treinamento DESC
        """
        cursor.execute(q)
        res = cursor.fetchall()
        res_tratado = converter_datas_e_horas(res)
        return jsonify(res_tratado), 200
    except Error as e:
        return jsonify({"erro": "Erro ao buscar treinamentos", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/treinamentos", methods=["POST"])
def criar_treinamento():
    """Recebe treinamento e calcula vencimento automaticamente (1 ano)."""
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "JSON ausente"}), 400

    campos_obrigatorios = ["id_brigadista", "nome_treinamento", "data_treinamento"]
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"Campo obrigatório: {campo}"}), 400

    try:
        data_treinamento_obj = datetime.strptime(dados["data_treinamento"], "%Y-%m-%d").date()
        data_vencimento_obj = data_treinamento_obj + relativedelta(years=1)
        data_vencimento_str = data_vencimento_obj.strftime("%Y-%m-%d")
    except ValueError:
        return jsonify({"erro": "Formato de data inválido. Use AAAA-MM-DD"}), 400

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        q = """
            INSERT INTO Registros_Treinamento
                (id_brigadista, nome_treinamento, data_treinamento, data_vencimento, carga_horaria, instrutor)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            q,
            (
                dados["id_brigadista"],
                dados["nome_treinamento"],
                dados["data_treinamento"],
                data_vencimento_str,
                dados.get("carga_horaria"),
                dados.get("instrutor"),
            ),
        )
        conn.commit()

        return (
            jsonify(
                {
                    "mensagem": "Treinamento registrado com sucesso!",
                    "data_treinamento": dados["data_treinamento"],
                    "data_vencimento_calculada": data_vencimento_str,
                }
            ),
            201,
        )
    except Error as e:
        return jsonify({"erro": "Erro no banco de dados", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ============================================================
# ROTAS: EXTINTORES (COM QR CODE)
# ============================================================


@app.route("/extintores", methods=["GET"])
def listar_extintores():
    conn = None
    cursor = None  # CORRIGIDO
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Extintores")
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({"erro": "Erro no banco de dados", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/extintores/gerar-qr/<int:id_extintor>", methods=["GET"])
def gerar_qr_extintor(id_extintor):
    """Gera QR Code para um extintor específico."""
    conn = None
    cursor = None  # CORRIGIDO
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Extintores WHERE id_extintor = %s", (id_extintor,))
        extintor = cursor.fetchone()

        if not extintor:
            return jsonify({"erro": "Extintor não encontrado"}), 404

        # CORRIGIDO: fallback explícito para "N/A" se nenhuma coluna de tipo existir
        tipo = extintor.get("tipo_extintor") or extintor.get("tipo") or "N/A"

        dados_qr = f"""
ID: {extintor['id_extintor']}
Série: {extintor['numero_serie']}
Tipo: {tipo}
Local: {extintor['localizacao_atual']}
Validade: {extintor['data_validade_carga']}
        """.strip()

        qr_base64 = gerar_qr_code_base64(dados_qr)

        return (
            jsonify(
                {
                    "id_extintor": id_extintor,
                    "numero_serie": extintor["numero_serie"],
                    "qr_code": qr_base64,
                }
            ),
            200,
        )

    except Error as e:
        return jsonify({"erro": "Erro ao gerar QR Code", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/extintores/vencidos", methods=["GET"])
def listar_extintores_vencidos():
    hoje = datetime.now().strftime("%Y-%m-%d")
    q = "SELECT * FROM Extintores WHERE data_validade_carga < %s ORDER BY data_validade_carga ASC"
    conn = None
    cursor = None  # CORRIGIDO
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q, (hoje,))
        res = cursor.fetchall()
        return (
            jsonify(
                {"data_verificacao": hoje, "total_vencidos": len(res), "extintores": res}
            ),
            200,
        )
    except Error as e:
        return jsonify({"erro": "Erro no banco de dados", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/extintores/analise-vencimentos", methods=["GET"])
def analise_vencimentos():
    q = "SELECT id_extintor, numero_serie, data_validade_carga, localizacao_atual FROM Extintores"
    conn = None
    cursor = None  # CORRIGIDO
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q)
        extintores = cursor.fetchall()

        hoje = datetime.now().date()
        resultado = []
        for ex in extintores:
            validade = ex["data_validade_carga"]
            dias_restantes = (validade - hoje).days
            status = (
                "OK"
                if dias_restantes > 30
                else "CRÍTICO"
                if dias_restantes >= 0
                else "VENCIDO"
            )

            ex["dias_para_vencer"] = dias_restantes
            ex["situacao_validade"] = status
            resultado.append(ex)

        return jsonify(resultado), 200
    except Error as e:
        return jsonify({"erro": "Erro no cálculo", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ============================================================
# RECURSO: INSPEÇÕES
# ============================================================


@app.route("/inspecoes", methods=["POST"])
def criar_inspecao():
    dados = request.get_json()
    campos_obrigatorios = [
        "id_extintor",
        "data_inspecao",
        "hora_inspecao",
        "numero_lacre",
        "confirmar_tipo",
        "status_manometro",
        "status_lacre",
        "status_bocal",
        "avaria_externa",
    ]

    if not dados:
        return jsonify({"erro": "JSON ausente"}), 400

    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"Campo obrigatório: {campo}"}), 400

    conn = None
    cursor = None  # CORRIGIDO
    # CORRIGIDO: Twilio é chamado fora da transação do banco
    notificar_extintor_id = None
    notificar_motivo = None

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        q_inspecao = """
            INSERT INTO Inspecoes
                (id_brigadista, id_extintor, data_inspecao, hora_inspecao, numero_lacre,
                 confirmar_tipo, status_manometro, status_lacre, status_bocal, avaria_externa, observacoes)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        p_inspecao = (
            dados.get("id_brigadista"),
            dados["id_extintor"],
            dados["data_inspecao"],
            dados["hora_inspecao"],
            dados["numero_lacre"],
            dados["confirmar_tipo"],
            dados["status_manometro"],
            dados["status_lacre"],
            dados["status_bocal"],
            dados["avaria_externa"],
            dados.get("observacoes"),
        )
        cursor.execute(q_inspecao, p_inspecao)
        id_nova_inspecao = cursor.lastrowid

        motivos_reprovacao = []
        if dados["status_manometro"] != "Normal":
            motivos_reprovacao.append(f"Manômetro {dados['status_manometro']}")
        if dados["status_lacre"] != "Intacto":
            motivos_reprovacao.append(f"Lacre {dados['status_lacre']}")
        if dados["status_bocal"] != "Desobstruído":
            motivos_reprovacao.append(f"Bocal {dados['status_bocal']}")
        if dados["avaria_externa"] != "Nenhuma":
            motivos_reprovacao.append(f"Avaria: {dados['avaria_externa']}")

        if motivos_reprovacao:
            situacao_final = f"REPROVADO: {', '.join(motivos_reprovacao)}"
            cursor.execute(
                "UPDATE Extintores SET status_equipamento = 'Em Manutenção' WHERE id_extintor = %s",
                (dados["id_extintor"],),
            )
            # CORRIGIDO: guarda os dados para notificar DEPOIS do commit
            notificar_extintor_id = dados["id_extintor"]
            notificar_motivo = situacao_final
        else:
            situacao_final = "Equipamento aprovado para uso"

        conn.commit()

        # CORRIGIDO: Twilio chamado APÓS o commit, fora da transação do banco
        if notificar_extintor_id is not None:
            enviar_notificacao_manutencao(notificar_extintor_id, notificar_motivo)

        return (
            jsonify({"mensagem": "Inspeção realizada com sucesso!", "resultado_analise": situacao_final}),
            201,
        )

    except Error as e:
        if conn:
            conn.rollback()
        return jsonify({"erro": "Erro ao processar inspeção", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ============================================================
# ROTA: RELATÓRIOS
# ============================================================


@app.route("/relatorios", methods=["GET"])
def listar_relatorios_finais():
    q = """
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
        LEFT JOIN Brigadistas b ON i.id_brigadista = b.id_brigadista
    """
    conn = None
    cursor = None  # CORRIGIDO
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q)
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({"erro": "Erro ao buscar relatórios", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ============================================================
# ROTAS: RELATÓRIOS DE TREINAMENTOS
# ============================================================


@app.route("/relatorios-treinamentos", methods=["GET"]) 
def listar_relatorios_treinamentos():
    """Lista todos os relatórios de treinamentos com informações do treinamento e brigadista."""
    q = """
        SELECT
            rt.id_relatorio_treinamento,
            rt.id_treinamento,
            rt.situacao,
            rt.data_relatorio,
            rt.observacoes,
            t.nome_treinamento,
            t.data_treinamento,
            t.carga_horaria,
            t.instrutor,
            b.id_brigadista,
            b.nome AS nome_brigadista,
            b.setor
        FROM Relatorios_Treinamentos rt
        INNER JOIN Registros_Treinamento t ON rt.id_treinamento = t.id_treinamento
        INNER JOIN Brigadistas b ON t.id_brigadista = b.id_brigadista
        ORDER BY rt.data_relatorio DESC
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q)
        res = cursor.fetchall()
        return jsonify(res), 200
    except Error as e:
        return jsonify({"erro": "Erro ao buscar relatórios de treinamentos", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/relatorios-treinamentos", methods=["POST"])
def criar_relatorio_treinamento():
    """Cria um novo relatório de treinamento."""
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "JSON ausente"}), 400

    campos_obrigatorios = ["id_treinamento", "situacao", "data_relatorio"]
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"Campo obrigatório: {campo}"}), 400

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        q = """
            INSERT INTO Relatorios_Treinamentos
                (id_treinamento, situacao, data_relatorio, observacoes)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(
            q,
            (
                dados["id_treinamento"],
                dados["situacao"],
                dados["data_relatorio"],
                dados.get("observacoes"),
            ),
        )
        conn.commit()

        return (
            jsonify(
                {
                    "mensagem": "Relatório de treinamento criado com sucesso!",
                    "id_relatorio_treinamento": cursor.lastrowid,
                }
            ),
            201,
        )
    except Error as e:
        return jsonify({"erro": "Erro ao criar relatório de treinamento", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/relatorios-treinamentos/<int:id_relatorio>", methods=["GET"])
def obter_relatorio_treinamento(id_relatorio):
    """Obtém um relatório de treinamento específico."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        q = """
            SELECT
                rt.id_relatorio_treinamento,
                rt.id_treinamento,
                rt.situacao,
                rt.data_relatorio,
                rt.observacoes,
                t.nome_treinamento,
                t.data_treinamento,
                t.carga_horaria,
                t.instrutor,
                b.id_brigadista,
                b.nome AS nome_brigadista,
                b.setor
            FROM Relatorios_Treinamentos rt
            INNER JOIN Registros_Treinamento t ON rt.id_treinamento = t.id_treinamento
            INNER JOIN Brigadistas b ON t.id_brigadista = b.id_brigadista
            WHERE rt.id_relatorio_treinamento = %s
        """
        cursor.execute(q, (id_relatorio,))
        res = cursor.fetchone()

        if not res:
            return jsonify({"erro": "Relatório não encontrado"}), 404

        return jsonify(res), 200
    except Error as e:
        return jsonify({"erro": "Erro ao buscar relatório", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# ============================================================
# ROTAS: RELATÓRIOS DE INSPEÇÃO
# ============================================================

@app.route("/relatorios-inspecoes", methods=["GET"])
def listar_relatorios_inspecoes():
    """Lista todos os relatórios de inspeção com informações da inspeção e equipamento."""
    q = """
        SELECT
            r.id_relatorio AS id_relatorio_inspecao,
            r.id_inspecao,
            r.situacao,
            i.data_inspecao,
            i.hora_inspecao,
            i.numero_lacre,
            i.status_manometro,
            i.status_lacre,
            i.status_bocal,
            i.avaria_externa,
            e.id_extintor,
            e.numero_serie,
            e.localizacao_atual,
            e.data_validade_carga,
            b.id_brigadista,
            b.nome AS nome_brigadista,
            b.setor
        FROM Relatorios_Inspecao r
        INNER JOIN Inspecoes i ON r.id_inspecao = i.id_inspecao
        INNER JOIN Extintores e ON i.id_extintor = e.id_extintor
        LEFT JOIN Brigadistas b ON i.id_brigadista = b.id_brigadista
    """
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(q)
        res = cursor.fetchall()
        
        # Aplica a conversão para evitar o erro de timedelta/date do JSON
        res_tratado = converter_datas_e_horas(res)
        
        return jsonify(res_tratado), 200
    except Error as e:
        return jsonify({"erro": "Erro ao buscar relatórios de inspeção", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/relatorios-inspecoes", methods=["POST"])
def criar_relatorio_inspecao():
    """Cria um novo relatório de inspeção."""
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "JSON ausente"}), 400

    campos_obrigatorios = ["id_inspecao", "situacao"]
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"Campo obrigatório: {campo}"}), 400

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        q = """
            INSERT INTO Relatorios_Inspecao (id_inspecao, situacao)
            VALUES (%s, %s)
        """
        cursor.execute(
            q,
            (
                dados["id_inspecao"],
                dados["situacao"]
            ),
        )
        conn.commit()

        return (
            jsonify(
                {
                    "mensagem": "Relatório de inspeção criado com sucesso!",
                    "id_relatorio": cursor.lastrowid,
                }
            ),
            201,
        )
    except Error as e:
        return jsonify({"erro": "Erro ao criar relatório de inspeção", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.route("/relatorios-inspecoes/<int:id_relatorio>", methods=["GET"])
def obter_relatorio_inspecao(id_relatorio):
    """Obtém um relatório de inspeção específico."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        q = """
            SELECT
                r.id_relatorio AS id_relatorio_inspecao,
                r.id_inspecao,
                r.situacao,
                i.data_inspecao,
                i.hora_inspecao,
                i.numero_lacre,
                i.status_manometro,
                i.status_lacre,
                i.status_bocal,
                i.avaria_externa,
                e.id_extintor,
                e.numero_serie,
                e.localizacao_atual,
                e.data_validade_carga,
                b.id_brigadista,
                b.nome AS nome_brigadista,
                b.setor
            FROM Relatorios_Inspecao r
            INNER JOIN Inspecoes i ON r.id_inspecao = i.id_inspecao
            INNER JOIN Extintores e ON i.id_extintor = e.id_extintor
            LEFT JOIN Brigadistas b ON i.id_brigadista = b.id_brigadista
            WHERE r.id_relatorio = %s
        """
        cursor.execute(q, (id_relatorio,))
        res = cursor.fetchone()

        if not res:
            return jsonify({"erro": "Relatório de inspeção não encontrado"}), 404

        # Aplica a conversão aqui também
        res_tratado = converter_datas_e_horas(res)

        return jsonify(res_tratado), 200
    except Error as e:
        return jsonify({"erro": "Erro ao buscar relatório de inspeção", "detalhes": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ============================================================
# ROTA: TWILIO (teste/disparo manual)
# ============================================================


@app.route("/twilio/notificar", methods=["POST"])
def twilio_notificar():
    """Dispara uma notificação WhatsApp via Twilio.

    Body (JSON):
      {
        "extintor_id": 123,
        "motivo": "mensagem livre"
      }
    """
    dados = request.get_json(silent=True)
    if dados is None:
        return jsonify({"erro": "Requisição inválida. Certifique-se de enviar JSON e usar o Header Content-Type: application/json"}), 400

    extintor_id = dados.get("extintor_id")
    motivo = dados.get("motivo")

    if extintor_id is None or motivo is None:
        return jsonify({"erro": "Payload inválido. Use extintor_id e motivo."}), 400

    enviar_notificacao_manutencao(extintor_id, motivo)

    return jsonify({"mensagem": "Notificação processada."}), 200


if __name__ == "__main__":
    # CORRIGIDO: porta 80 exige privilégios de root. Usando 5000 (padrão Flask).
    app.run(host="127.0.0.1", port=5000, debug=True)