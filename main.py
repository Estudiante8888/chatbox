from flask import Flask, render_template, request, jsonify
from conexion import create_connection
import sqlite3
import re
import difflib
import unicodedata
import os
from datetime import datetime
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None  # por si no está disponible

# ---- .env opcional ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- Gemini ----
try:
    import google.generativeai as genai
except Exception:
    genai = None  # por si no está instalado

app = Flask(__name__)
DB_FILE = "sisemasexp.db"

# Modelo por defecto (sugiero flash por disponibilidad/latencia)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# === Mapeo simple ciudad -> zona horaria (puedes ampliarlo) ===
CITY_TZ = {
    "nueva york": "America/New_York",
    "new york": "America/New_York",
    "bogota": "America/Bogota",
    "colombia": "America/Bogota",
    "mexico": "America/Mexico_City",
    "ciudad de mexico": "America/Mexico_City",
    "lima": "America/Lima",
    "santiago": "America/Santiago",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "madrid": "Europe/Madrid",
    "londres": "Europe/London",
    "paris": "Europe/Paris",
}

# =================== PÁGINAS BÁSICAS ===================
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


# =================== PROGRAMAS (CRUD) ===================
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


# =================== CHAT (UI + API) ===================
@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.post("/api/chat")
def api_chat():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()

    # 1) Hechos/respuestas rápidas locales (para enriquecer Gemini)
    quick_bits = []

    t = _maybe_time_answer(user_msg)
    if t:
        quick_bits.append(f"[HORA] {t}")

    m = _maybe_math_answer(user_msg)
    if m:
        quick_bits.append(f"[MATE] {m}")

    if _should_use_rules(user_msg):
        quick_bits.append(f"[REGLAS] {generate_reply(user_msg)}")

    # 2) Si hay Gemini, SIEMPRE lo consultamos con el contexto local como ayuda
    if _gemini_available():
        reply = ask_gemini(user_msg, extra_context="\n".join(quick_bits))
        # Si por alguna razón viniera vacío, caemos a lo local
        if reply:
            return jsonify({"reply": reply})

    # 3) Sin Gemini o error: devolver lo mejor que tengamos localmente
    if quick_bits:
        # Prioriza lo más específico (mate/hora) o la última regla
        return jsonify({"reply": quick_bits[-1].split("] ", 1)[-1]})

    # 4) Fallback amable (siempre hay respuesta)
    return jsonify({
        "reply": (
            "Puedo ayudarte con preguntas generales, hora por ciudad y operaciones básicas. "
            "También conozco la lista de programas. ¿Qué necesitas?"
        )
    })


# ----------------- Utilidades locales -----------------
def normalize(text: str) -> str:
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
    keys = list(nombres_norm_map.keys())
    matches = difflib.get_close_matches(keyword_norm, keys, n=n, cutoff=0.5)
    if not matches:
        matches = [k for k in keys if keyword_norm in k][:n]
    if matches:
        return [nombres_norm_map[m] for m in matches]
    return []


def _should_use_rules(message: str) -> bool:
    if not message:
        return True
    msg = normalize(message)
    triggers = [
        "hola", "buenas", "gracias", "ayuda",
        "lista", "listar", "ver", "mostrar", "catalogo",
        "codigo", "id",
        "buscar", "busca", "tienen", "ofrecen", "programa de", "programas de", "hay",
        "mision", "vision"
    ]
    return any(t in msg for t in triggers)


def generate_reply(message: str) -> str:
    if not message:
        return ("Puedo listar programas, buscar por nombre o por código. "
                "Ejemplos: 'lista de programas', 'buscar programacion', 'codigo 2'.")

    msg = normalize(message)

    # Saludos / cortesía
    if any(p in msg for p in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey"]):
        return ("¡Hola! Soy el asistente de la Universitaria. "
                "Puedo listar programas, buscar uno por nombre o por código.")

    if any(p in msg for p in ["gracias", "muchas gracias", "mil gracias"]):
        return "¡Con gusto! ¿Necesitas algo más?"

    if "ayuda" in msg or "que puedes hacer" in msg:
        return ("Puedo: 1) listar los programas, 2) buscar por nombre, "
                "3) decir qué programa corresponde a un código. "
                "Ejemplos: 'lista', 'buscar programacion', 'codigo 3'.")

    # Lista de programas
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
            cursor.execute("SELECT descarrera FROM programas WHERE codcarrera = ?", (cod,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return f"El código {cod} corresponde a: {row[0]}."
            return f"No encontré un programa con código {cod}."
        return "Dime el número de código, por ejemplo: 'codigo 2'."

    # Búsqueda por nombre
    if any(p in msg for p in ["buscar", "busca", "tienen", "ofrecen", "programa de", "programas de", "hay"]):
        progs = fetch_programs()
        if not progs:
            return "No hay programas cargados todavía."

        nombres = [d for _, d in progs]
        nombres_norm_map = {normalize(n): n for n in nombres}

        palabras = [w for w in re.findall(r"[a-zA-Záéíóúñ]+", msg) if len(w) > 3]
        stop = {"buscar", "busca", "programa", "programas", "tienen", "ofrecen", "hay", "de", "en", "una"}
        keywords = [normalize(w) for w in palabras if normalize(w) not in stop]

        if not keywords:
            return "Dime la palabra clave. Ej: 'buscar programacion' o 'programa redes'."

        candidatos = []
        for kw in keywords:
            candidatos.extend(_suggest_names(kw, nombres_norm_map, n=3))
        candidatos = list(dict.fromkeys(candidatos))[:3]

        if candidatos:
            progs_map = {d: c for c, d in progs}
            items = [f"- {progs_map[nom]}: {nom}" for nom in candidatos]
            return "Encontré esto que se parece a lo que buscas:\n" + "\n".join(items)

        return ("No encontré un programa que coincida. "
                "Prueba con otra palabra (ej.: 'programacion', 'redes', 'analisis').")

    # Misión / Visión
    if "mision" in msg:
        return ("Nuestra misión es formar profesionales íntegros con competencias para "
                "transformar su entorno mediante el conocimiento.")
    if "vision" in msg:
        return "Nuestra visión es ser referentes por la excelencia académica y el impacto social."

    # Fallback de reglas (igual consultaremos a Gemini)
    return ("")  # vacío a propósito para no bloquear respuestas


# ----------------- Hora actual (local) -----------------
def _maybe_time_answer(message: str) -> str | None:
    msg = normalize(message)
    if "hora" not in msg:
        return None

    # Detectar ciudad
    tz = None
    city_found = None
    for key, zone in CITY_TZ.items():
        if key in msg:
            tz = zone
            city_found = key
            break

    try:
        if tz and ZoneInfo:
            now = datetime.now(ZoneInfo(tz))
            txt_city = city_found.title()
            return f"La hora en {txt_city} es {now.strftime('%H:%M')} del {now.strftime('%Y-%m-%d')}."
        else:
            # hora local del sistema
            now_local = datetime.now().astimezone()
            tzname = getattr(now_local.tzinfo, "key", getattr(now_local.tzinfo, "tzname", lambda x=None: "local")())
            return f"La hora local es {now_local.strftime('%H:%M')} del {now_local.strftime('%Y-%m-%d')} ({tzname})."
    except Exception:
        now = datetime.now()
        return f"La hora (aprox. local) es {now.strftime('%H:%M')} del {now.strftime('%Y-%m-%d')}."


# ----------------- Aritmética básica (segura) -----------------
def _maybe_math_answer(message: str) -> str | None:
    msg = normalize(message)

    # reemplazos de palabras por operadores
    word_ops = {
        r"\bmas\b": "+",
        r"\bmenos\b": "-",
        r"\bpor\b": "*",
        r"\bx\b": "*",
        r"\bentre\b": "/",
        r"\bdividido\b": "/",
        r"\bmod(ulo)?\b": "%",
        r"\belevado\b": "**",
        r"\bpotencia\b": "**",
    }
    tmp = msg
    for pat, op in word_ops.items():
        tmp = re.sub(pat, f" {op} ", tmp)

    # buscar una expresión aritmética simple
    m = re.search(r"(-?\d+(?:[.,]\d+)?(?:\s*[\+\-\*\/\%\(\)\^]\s*-?\d+(?:[.,]\d+)?)*)", tmp)
    if not m:
        return None

    expr = m.group(1)
    expr = expr.replace(",", ".")
    expr = expr.replace("^", "**")

    # validar caracteres permitidos
    if not re.fullmatch(r"[\d\.\+\-\*\/\%\(\)\s\*]*", expr):
        return None

    # evaluar de forma segura con AST
    try:
        import ast
        import operator as op

        ops = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Mod: op.mod,
            ast.Pow: op.pow,
            ast.USub: op.neg,
            ast.UAdd: op.pos,
            ast.FloorDiv: op.floordiv,
        }

        def _eval(node):
            if isinstance(node, ast.Num):
                return node.n
            if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError("constante no numérica")
            if isinstance(node, ast.BinOp):
                return ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](_eval(node.operand))
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            raise ValueError("expresión no permitida")

        node = ast.parse(expr, mode="eval")
        result = _eval(node)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"Resultado: {result}"
    except Exception:
        return None


# ----------------- Gemini: llamada a API -----------------
def _gemini_available() -> bool:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(api_key) and genai is not None


def _build_context(extra: str = "") -> str:
    progs = fetch_programs()
    lista = "; ".join([f"{c}: {d}" for c, d in progs]) or "sin programas cargados"
    now_iso = datetime.now().astimezone().isoformat(timespec="seconds")
    ctx = (
        "Contexto de la Universidad:\n"
        f"- Programas disponibles (codigo: nombre): {lista}.\n"
        f"- Hora actual del servidor: {now_iso}.\n"
        "- Si la pregunta es sobre la universidad, usa estos datos.\n"
        "- Si es una pregunta general, respóndela normalmente.\n"
    )
    if extra:
        ctx += f"\nHechos locales:\n{extra}\n"
    return ctx


def ask_gemini(user_msg: str, extra_context: str = "") -> str:
    try:
        if not _gemini_available():
            return ""

        api_key = os.getenv("GEMINI_API_KEY").strip()
        genai.configure(api_key=api_key)

        system_prompt = (
            "Eres un asistente útil y confiable. Responde SIEMPRE en español, "
            "con claridad y brevedad. Si hay 'Hechos locales', respétalos y "
            "úsalos en tu respuesta. Si la pregunta es general, respóndela "
            "normalmente. Si no estás seguro, di la mejor aproximación."
        )
        context = _build_context(extra_context)

        def _call(model_name: str) -> str:
            model = genai.GenerativeModel(model_name=model_name)
            resp = model.generate_content(
                [
                    {"text": system_prompt},
                    {"text": context},
                    {"text": f"Usuario: {user_msg}"},
                ],
                generation_config={
                    "temperature": 0.6,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 512,
                },
            )
            return (getattr(resp, "text", "") or "").strip()

        model_primary = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        try:
            text = _call(model_primary)
            if text:
                return text
        except Exception:
            # Fallback de modelo
            try:
                text = _call("gemini-2.5-flash")
                if text:
                    return text
            except Exception:
                return ""
        return ""
    except Exception:
        return ""


# =================== APP ===================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
