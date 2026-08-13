// Helper fetch bersama untuk semua halaman. Tidak ada framework/build step --
// disengaja supaya sesuai lokasi (app/frontend, di-serve statis oleh backend
// FastAPI yang sama, lihat app/backend/main.py bagian StaticFiles mount).
//
// API_TOKEN: untuk dashboard internal-only ini disimpan sebagai constant di
// sini (bukan login system) -- SESUAIKAN sebelum deploy, JANGAN commit token
// asli ke git. Nilainya HARUS sama dengan BACKEND_API_TOKEN di .env backend.
const API_BASE = "";
const API_TOKEN = window.__API_TOKEN__ || "___SET_ME___";

async function callAction(action, params = {}) {
  const res = await fetch(`${API_BASE}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Token": API_TOKEN },
    body: JSON.stringify({ action, params }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Action ${action} gagal (${res.status})`);
  }
  return (await res.json()).data;
}

function fmtDate(v) {
  if (!v) return "-";
  const d = new Date(v);
  if (isNaN(d.getTime())) return String(v);
  return d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
}

function badge(value) {
  if (!value) return "-";
  return `<span class="badge ${value}">${value}</span>`;
}

function esc(v) {
  if (v === null || v === undefined) return "-";
  return String(v).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function qs(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function goToFindings(params) {
  const usp = new URLSearchParams(params);
  window.location.href = `findings.html?${usp.toString()}`;
}

function goToDetail(findingId) {
  window.location.href = `finding-detail.html?id=${encodeURIComponent(findingId)}`;
}
