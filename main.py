from flask import Flask, render_template, request, jsonify
from conexion import create_connection
import sqlite3
import re
import difflib
import unicodedata

app = Flask(__name__)
DB_FILE = "sisemasexp.db"

# =============== PÁGINAS BÁSICAS ===============
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
            """
            CREATE TABLE IF NOT EXISTS vision (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                mensaje TEXT,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            "INSERT INTO vision (nombre, mensaje) VALUES (?, ?)", (nombre, mensaje)
        )
        conn.commit()
        conn.close()

        return "✅ Datos guardados en la base de datos"
    return render_template("vision.html")


# =============== PROGRAMAS (CRUD SENCILLO) ===============
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
                cursor.execute(
                    "SELECT COUNT(*) FROM programas WHERE codcarrera = ?",
                    (codcarrera,),
                )
                if cursor.fetchone()[0] > 0:
                    conn.close()
                    return jsonify(
                        {"success": False, "message": "El código de carrera ya existe"}
                    )
                cursor.execute(
                    "INSERT INTO programas (codcarrera, descarrera) VALUES (?, ?)",
                    (codcarrera, descarrera),
                )
                message = "Programa agregado exitosamente"

            elif action == "actualizar":
                cursor.execute(
                    "UPDATE programas SET descarrera = ? WHERE codcarrera = ?",
                    (descarrera, codcarrera),
                )
                message = "Programa actualizado exitosamente"

            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": message})

        except Exception as e:
            conn.close()
            return jsonify({"success": False, "message": f"Error: {str(e)}"})

    # GET: listar
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
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM programas WHERE codcarrera = ?", (id,))
    programa = cursor.fetchone()
    conn.close()

    if programa:
        return (
            jsonify(
                {
                    "success": True,
                    "programa": {
                        "codcarrera": programa[0],
                        "descarrera": programa[1],
                    },
                }
            ),
            200,
        )
    return jsonify({"success": False, "message": "Programa no encontrado"}), 404


# =============== CHAT (UI + API) ===============
@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    reply = generate_reply(user_msg)
    return jsonify({"reply": reply})


# ----------- “IA” simple (reglas + BD) -----------
def normalize(text: str) -> str:
    """Quita acentos y pone en minúsculas para comparar mejor."""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return t.lower().strip()


def fetch_programs():
    conn = create_connection(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT codcarrera, descarrera FROM programas ORDER BY codcarrera")
    rows = cursor.fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _suggest_names(keyword_norm, nombres_norm_map, n=3):
    """Devuelve hasta n nombres similares al keyword_norm."""
    keys = list(nombres_norm_map.keys())
    matches = difflib.get_close_matches(keyword_norm, keys, n=n, cutoff=0.5)
    if not matches:
        # fallback: substring
        matches = [k for k in keys if keyword_norm in k][:n]
    if matches:
        return [nombres_norm_map[m] for m in matches]
    return []


def generate_reply(message: str) -> str:
    if not message:
        return (
            "Escríbeme algo y con gusto te ayudo 🙂. "
            "Puedo listar programas, buscar por nombre o por código."
        )

    msg = normalize(message)

    # Saludos / cortesía
    if any(
        p in msg
        for p in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey"]
    ):
        return (
            "¡Hola! Soy el asistente de la Universitaria. "
            "Puedo listar programas, buscar uno por nombre o por código."
        )

    if any(p in msg for p in ["gracias", "muchas gracias", "mil gracias"]):
        return "¡Con gusto! ¿Necesitas algo más?"

    if "ayuda" in msg or "que puedes hacer" in msg:
        return (
            "Puedo: 1) listar los programas, 2) buscar un programa por nombre, "
            "3) decirte qué programa corresponde a un código. "
            "Ejemplos: 'lista de programas', 'buscar programacion', 'codigo 3'."
        )

    # Lista de programas (sinónimos)
    if any(k in msg for k in ["lista", "listar", "ver", "mostrar", "catalogo"]) and any(
        k in msg for k in ["program", "carrera"]
    ):
        progs = fetch_programs()
        if not progs:
            return "No hay programas registrados."
        listado = " - " + " | ".join([f"{c}: {d}" for c, d in progs])
        return f"Aquí tienes la lista de programas (código: nombre):{listado}"

    # Consulta por código
    if "codigo" in msg or "id" in msg:
        match_id = re.search(r"\b(\d+)\b", msg)
        if match_id:
            cod = int(match_id.group(1))
            conn = create_connection(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT descarrera FROM programas WHERE codcarrera = ?", (cod,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return f"El código {cod} corresponde a: {row[0]}."
            return f"No encontré un programa con código {cod}."
        # pidió 'codigo' pero sin número
        return "Dime el número de código, por ejemplo: 'codigo 2'."

    # Búsqueda por nombre (varias palabras + sugerencias)
    if any(
        p in msg
        for p in ["buscar", "busca", "tienen", "ofrecen", "programa de", "programas de", "hay"]
    ):
        progs = fetch_programs()
        if not progs:
            return "No hay programas cargados todavía."

        nombres = [d for _, d in progs]
        nombres_norm_map = {normalize(n): n for n in nombres}

        # palabras relevantes
        palabras = [w for w in re.findall(r"[a-zA-Záéíóúñ]+", msg) if len(w) > 3]
        stop = {"buscar", "busca", "programa", "programas", "tienen", "ofrecen", "hay", "de", "en", "una"}
        keywords = [normalize(w) for w in palabras if normalize(w) not in stop]

        if not keywords:
            return "Dime la palabra clave. Ej: 'buscar programacion' o 'programa redes'."

        candidatos = []
        for kw in keywords:
            candidatos.extend(_suggest_names(kw, nombres_norm_map, n=3))
        # únicos manteniendo orden, top 3
        candidatos = list(dict.fromkeys(candidatos))[:3]

        if candidatos:
            progs_map = {d: c for c, d in progs}
            items = [f"- {progs_map[nom]}: {nom}" for nom in candidatos]
            return "Encontré esto que se parece a lo que buscas:\n" + "\n".join(items)

        return (
            "No encontré un programa que coincida. "
            "Prueba con otra palabra (ej.: 'programacion', 'redes', 'analisis')."
        )

    # Misión / Visión
    if "mision" in msg:
        return (
            "Nuestra misión es formar profesionales íntegros con competencias para "
            "transformar su entorno mediante el conocimiento."
        )
    if "vision" in msg:
        return (
            "Nuestra visión es ser referentes por la excelencia académica y el impacto social."
        )

    # Fallback
    return (
        "No estoy seguro de entenderte 🤔. "
        "Puedo listar programas, buscar por nombre o por código. "
        "Ejemplos: 'lista de programas', 'buscar programacion', 'codigo 2'."
    )


# =============== APP ===============
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
