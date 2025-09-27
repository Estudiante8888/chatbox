(function () {
  const log = document.getElementById("chatLog");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const chips = document.getElementById("quickChips");

  function nowTime() {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function addMsg(role, text) {
    const wrap = document.createElement("div");
    wrap.className = role === "user" ? "text-end my-2" : "text-start my-2";
    const badge = role === "user" ? "bg-primary" : "bg-secondary";
    wrap.innerHTML = `
      <div class="d-inline-block px-3 py-2 rounded-3 ${
        role === "user" ? "text-white" : "text-light"
      } ${badge}">
        ${escapeHtml(text)}
        <div class="opacity-75 small mt-1" style="text-align:${
          role === "user" ? "right" : "left"
        }">${nowTime()}</div>
      </div>
    `;
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "text-start my-2";
    wrap.id = "typing";
    wrap.innerHTML = `
      <div class="d-inline-block px-3 py-2 rounded-3 text-light bg-secondary">
        <span class="me-2">Escribiendo</span>
        <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
        <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
        <span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span>
      </div>
    `;
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById("typing");
    if (t) t.remove();
  }

  function escapeHtml(s) {
    return s.replace(
      /[&<>"']/g,
      (m) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        }[m])
    );
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;

    addMsg("user", msg);
    input.value = "";
    input.focus();
    addTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      removeTyping();
      addMsg("bot", data.reply || "No entendí la respuesta del servidor.");
    } catch (err) {
      console.error(err);
      removeTyping();
      addMsg("bot", "Error de conexión 😞");
    }
  });

  // Chips de preguntas rápidas
  if (chips) {
    chips.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-q]");
      if (!btn) return;
      input.value = btn.dataset.q;
      form.requestSubmit();
    });
  }

  // Bienvenida
  addMsg(
    "bot",
    '¡Hola! Puedo listar programas, buscar por nombre o por código. Ejemplos: "lista de programas", "buscar programacion", "codigo 2".'
  );
})();
