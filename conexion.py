import sqlite3

def create_connection(db_file):
    """ Crear una conexión a la base de datos SQLite """
    connection = None
    try:
        connection = sqlite3.connect(db_file)
        print("Conexión exitosa a SQLite")
    except sqlite3.Error as e:
        print(f"El error '{e}' ocurrió")
    return connection

def execute_sql_script(connection, script_file):
    with open(script_file, 'r') as f:
        sql_script = f.read()

    cursor = connection.cursor()
    try:
        cursor.executescript(sql_script)  # Ejecutar todas las sentencias SQL del archivo
        connection.commit()
        print("Sentencias SQL ejecutadas correctamente.")
    except sqlite3.Error as e:
        print(f"El error '{e}' ocurrió al ejecutar las sentencias.")

# Crear la conexión
db_file = "sisemasexp.db"  # Archivo de base de datos SQLite
connection = create_connection(db_file)

if connection:
    # Ejecutar las sentencias SQL
    execute_sql_script(connection, 'sentencias.sql')  # El archivo donde están las sentencias SQL

    # Cerrar la conexión
    connection.close()