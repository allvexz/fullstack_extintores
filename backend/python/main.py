import os
from typing import Any, List, Tuple

import mysql.connector
import numpy as np


def fetch_pyrosync_data() -> Tuple[np.ndarray, List[str]]:
    """Conecta no MySQL e retorna os dados como array numpy.

    Retorna:
        (meu_array, colunas)
    """

    # Usar variáveis de ambiente facilita trocar credenciais sem editar o código.
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "leonardo.jessica")
    password = os.getenv("MYSQL_PASSWORD", "0000")
    database = os.getenv("MYSQL_DATABASE", "pyrosync")

    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
    )

    try:
        cursor = conn.cursor()
        # Consulta completa do arquivo backend/sql/my.sql (com JOIN + status_inspecao)
        query = """
        SELECT
            i.id_inspecao,
            b.nome          AS brigadista,
            e.tipo_extintor,
            i.manometro,
            i.bocal_obstruido,
            i.lacre_violado,
            i.avaria_externa,
            i.data_inspecao,
            CASE
                WHEN UPPER(i.manometro)  <> 'OK'  THEN 'REPROVADO - Manometro com problema'
                WHEN i.bocal_obstruido   = 'Sim'  THEN 'REPROVADO - Bocal obstruido'
                WHEN i.lacre_violado     = 'Sim'  THEN 'REPROVADO - Lacre violado'
                WHEN i.avaria_externa    = 'Sim'  THEN 'REPROVADO - Avaria externa'
                ELSE 'APROVADO'
            END AS status_inspecao
        FROM pyrosync.inspecoes i
        INNER JOIN pyrosync.brigadistas b
            ON i.id_brigadista = b.id_brigadista
        INNER JOIN pyrosync.extintores e
            ON i.id_extintor = e.id_extintor;
        """
        cursor.execute(query)

        rows = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]

        meu_array = np.array(rows, dtype=object)
        return meu_array, colunas
    finally:
        conn.close()


def main() -> None:
    meu_array, colunas = fetch_pyrosync_data()

    print("Colunas:")
    print(colunas)
    print("\nArray NumPy:")
    print(meu_array)


if __name__ == "__main__":
    main()

