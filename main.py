from flask import Flask, render_template, request, redirect, url_for
from conexion import create_connection

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
        # Insertar nueva carrera en la tabla programas
        codcarrera = request.form.get("codcarrera")
        descarrera = request.form.get("descarrera")
        cursor.execute(
            "INSERT INTO programas (codcarrera, descarrera) VALUES (?, ?)",
            (codcarrera, descarrera),
        )
        conn.commit()
        conn.close()

        # Redirigir a respuesta.html después de agregar
        return redirect(url_for("respuesta"))

    # Si es GET, simplemente muestro la página programas.html
    cursor.execute("SELECT * FROM programas;")
    rows = cursor.fetchall()
    conn.close()

    return render_template("programas.html", programas=rows)


@app.route("/respuesta")
def respuesta():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM programas;")
    rows = cursor.fetchall()
    conn.close()

    return render_template("respuesta.html", programas=rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
