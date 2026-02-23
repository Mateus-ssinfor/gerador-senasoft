// -------- Modal (Visualizar Proposta) --------
async function viewProposal(id) {
  const res = await fetch(`/api/proposta/${id}`);
  if (!res.ok) {
    alert("Erro ao carregar proposta.");
    return;
  }
  const d = await res.json();

  document.getElementById("modalMeta").innerText =
    `#${d.id} — ${d.client_name}\nCriada: ${d.criada}\nExpira: ${d.expira}`;

  document.getElementById("modalPayload").innerText =
    `CPF: ${d.cpf}\nModelo: ${d.modelo}\nFranquia: ${d.franquia}\nValor: ${d.valor}`;

  document.getElementById("modal").showModal();
}

function closeModal() {
  document.getElementById("modal").close();
}

// -------- Sidebar Toggle --------
function setupSidebar() {
  const root = document.getElementById("appRoot");
  const btn = document.getElementById("toggleSidebar");
  if (!root || !btn) return;

  // manter preferencia
  const saved = localStorage.getItem("sidebar_expanded");
  if (saved === "1") root.classList.add("expanded");

  btn.addEventListener("click", () => {
    root.classList.toggle("expanded");
    localStorage.setItem("sidebar_expanded", root.classList.contains("expanded") ? "1" : "0");
  });
}

// -------- Máscara de Data (dd/mm/aa) --------
function maskDateInput(el) {
  el.addEventListener("input", () => {
    let v = el.value.replace(/\D/g, "").slice(0, 6); // 6 dígitos
    if (v.length >= 3) v = v.slice(0, 2) + "/" + v.slice(2);
    if (v.length >= 6) v = v.slice(0, 5) + "/" + v.slice(5);
    el.value = v;
  });
}

function setupDateMasks() {
  const di = document.getElementById("data_inicio");
  const dt = document.getElementById("data_termino");
  const dv = document.getElementById("data_venc");
  if (di) maskDateInput(di);
  if (dt) maskDateInput(dt);
  if (dv) maskDateInput(dv);
}

window.addEventListener("DOMContentLoaded", () => {
  setupSidebar();
  setupDateMasks();
});

// --- PWA: Service Worker ---
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

// Máscara: dd/mm/aa (digite só números: 200226 -> 20/02/26)
function maskDate(el) {
  el.addEventListener("input", () => {
    let v = el.value.replace(/\D/g, "").slice(0, 6);
    if (v.length >= 3) v = v.slice(0, 2) + "/" + v.slice(2);
    if (v.length >= 6) v = v.slice(0, 5) + "/" + v.slice(5);
    el.value = v;
  });
}

// Máscara: hh:mm (digite só números: 1330 -> 13:30)
function maskTime(el) {
  el.addEventListener("input", () => {
    let v = el.value.replace(/\D/g, "").slice(0, 4);
    if (v.length >= 3) v = v.slice(0, 2) + ":" + v.slice(2);
    el.value = v;
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".mask-date").forEach(maskDate);
  document.querySelectorAll(".mask-time").forEach(maskTime);
});