import sqlite3
import os

def create_connection(db_file):
    """Crear una conexión a la base de datos SQLite"""
    try:
        connection = sqlite3.connect(db_file)
        connection.row_factory = sqlite3.Row  # Acceso a columnas por nombre
        print(f"✅ Conexión exitosa a SQLite: {db_file}")
        return connection
    except sqlite3.Error as e:
        print(f"❌ Error al conectar a SQLite: {e}")
        return None

def execute_sql_script(connection, script_file):
    """Ejecutar todas las sentencias SQL desde un archivo .sql"""
    if not os.path.exists(script_file):
        print(f"❌ El archivo {script_file} no existe.")
        return
    
    try:
        with open(script_file, 'r', encoding="utf-8") as f:
            sql_script = f.read()
        
        cursor = connection.cursor()
        cursor.executescript(sql_script)
        connection.commit()
        print(f"✅ Script {script_file} ejecutado correctamente.")
    except sqlite3.Error as e:
        print(f"❌ Error ejecutando el script SQL: {e}")

if __name__ == "__main__":
    db_file = "sisemasexp.db"      # Archivo de base de datos
    sql_file = "sentencias.sql"    # Script con sentencias SQL

    conn = create_connection(db_file)
    if conn:
        execute_sql_script(conn, sql_file)
        conn.close()
