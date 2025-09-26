from flask import Flask, render_template, request, redirect, url_for, jsonify
from conexion import create_connection
import sqlite3

app = Flask(__name__)
DB_FILE = "sisemasexp.db"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/mision")
def mision():
    return render_template("mision.html")


@app.route("/vision", methods=["GET", "POST"])
def vision():
    if request.method == "POST":
        datos = request.form
        nombre = datos.get("nombre")
        mensaje = datos.get("mensaje")

        conn = create_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO vision (nombre, mensaje) VALUES (?, ?)", (nombre, mensaje)
        )
        conn.commit()
        conn.close()

        return "✅ Datos guardados en la base de datos"
    else:
        return render_template("vision.html")


@app.route("/programas", methods=["GET", "POST"])
def programas():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()

    if request.method == "POST":
        codcarrera = request.form.get("codcarrera")
        descarrera = request.form.get("descarrera")
        action = request.form.get("action")

        try:
            if action == "agregar":
                # Verificar si ya existe el código
                cursor.execute("SELECT COUNT(*) FROM programas WHERE codcarrera = ?", (codcarrera,))
                if cursor.fetchone()[0] > 0:
                    conn.close()
                    return jsonify({"success": False, "message": "El código de carrera ya existe"})
                
                cursor.execute(
                    "INSERT INTO programas (codcarrera, descarrera) VALUES (?, ?)",
                    (codcarrera, descarrera),
                )
                message = "Programa agregado exitosamente"
                
            elif action == "actualizar":
                cursor.execute(
                    "UPDATE programas SET descarrera = ? WHERE codcarrera = ?", 
                    (descarrera, codcarrera)
                )
                message = "Programa actualizado exitosamente"
            
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": message})
            
        except Exception as e:
            conn.close()
            return jsonify({"success": False, "message": f"Error: {str(e)}"})

    # GET request - cargar datos
    cursor.execute("SELECT * FROM programas ORDER BY codcarrera")
    rows = cursor.fetchall()
    conn.close()

    return render_template("programas.html", programas=rows)


@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_programa(id):
    try:
        conn = create_connection(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM programas WHERE codcarrera = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Programa eliminado exitosamente"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al eliminar: {str(e)}"})


@app.route("/obtener_programa/<int:id>")
def obtener_programa(id):
    """Endpoint para obtener los datos de un programa específico"""
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM programas WHERE codcarrera = ?", (id,))
    programa = cursor.fetchone()
    conn.close()
    
    if programa:
        return jsonify({
            "success": True,
            "programa": {
                "codcarrera": programa[0],
                "descarrera": programa[1]
            }
        })
    else:
        return jsonify({"success": False, "message": "Programa no encontrado"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)