// Browser front-end. All image processing runs in Python (Pyodide) via bridge.py.
//
// Optional config, set before this script loads:
//   window.SCANNER_CONFIG = { endpoint: "/api/tool-events/", pyBase: "" }
// `endpoint` receives analytics + feedback as JSON POSTs. Without it, events only go to the console.

const CONFIG = { pyBase: "../", endpoint: null, ...window.SCANNER_CONFIG };
const PY_FILES = ["__init__", "detect", "enhance", "orient", "pipeline", "export", "watermark"];
const MAX_SIDE = 2000;   // photos are downscaled to this before processing: keeps phones fast
const HANDLE_HIT = 28;   // touch-friendly grab radius for corners, in CSS px

const I18N = {
  fa: {
    title: "اسکنر اسناد", tagline: "عکس گوشی رو به یه اسکن تمیز تبدیل کن. کاملاً داخل مرورگر خودت اجرا می‌شه.",
    by: "ساخته‌شده توسط", author: "میلاد مبصری", back: "→ بازگشت به سایت", loading: "در حال بارگذاری موتور اسکنر… (فقط بار اول، حدود ۱۵ ثانیه)",
    choose: "از یه سند عکس بگیر یا انتخابش کن", drop: "یا اینجا رهاش کن",
    crop: "۱. گوشه‌ها رو تنظیم کن", result: "۲. نتیجه",
    magic: "رنگی", gray: "خاکستری", bw: "سیاه‌وسفید", original: "اصلی",
    rotLeft: "⟲ چرخش", rotRight: "چرخش ⟳", add: "➕ افزودن به PDF", savePng: "⬇ تصویر",
    new: "↺ اسکن یه عکس دیگه", pages: "صفحه‌های PDF", savePdf: "⬇ دانلود PDF",
    fbTitle: "چطور بود؟", good: "👍 خوب کار کرد", bad: "👎 مشکل داشت",
    fbPlaceholder: "چه مشکلی بود یا چه امکانی اضافه بشه؟ (اختیاری)", send: "ارسال نظر",
    thanks: "ممنون! نظرت ارسال شد.", privacy: "🔒 عکس‌هات روی دستگاه خودت پردازش می‌شن و هیچ‌وقت آپلود نمی‌شن.",
    detected: "✅ برگه پیدا شد. اگه لازمه، گوشه‌ها رو بکش.", notDetected: "⚠️ برگه پیدا نشد. گوشه‌ها رو روی گوشه‌های برگه بکش.",
    loadError: "بارگذاری موتور ناموفق بود. اینترنت رو چک کن و صفحه رو دوباره باز کن.",
  },
};
const lang = new URLSearchParams(location.search).get("lang") === "fa" ? "fa" : "en";
const t = (key, fallback) => I18N[lang]?.[key] ?? fallback;

const $ = (sel) => document.querySelector(sel);
const canvas = $("#crop");
const ctx = canvas.getContext("2d");

const state = { photo: null, corners: [], turns: 0, mode: "magic", dragging: -1, pages: [], pngUrl: null, vote: null };
let bridge = null;
const sessionId = crypto.randomUUID?.() ?? String(Math.random());

// ---------- analytics & feedback ----------
function track(event, data = {}) {
  const payload = { tool: "scanner", event, ...data, lang, session: sessionId, ts: new Date().toISOString(), ua: navigator.userAgent };
  console.debug("[scanner]", payload);
  if (!CONFIG.endpoint) return;
  const body = JSON.stringify(payload);
  if (!navigator.sendBeacon?.(CONFIG.endpoint, new Blob([body], { type: "application/json" }))) {
    fetch(CONFIG.endpoint, { method: "POST", body, headers: { "Content-Type": "application/json" }, keepalive: true }).catch(() => {});
  }
}
window.addEventListener("error", (e) => track("js_error", { message: e.message }));

// ---------- i18n ----------
function applyLanguage() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n, el.textContent)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder, el.placeholder)));
  if (lang === "fa") document.title = "اسکنر اسناد — میلاد مبصری";
}

// ---------- engine ----------
async function boot() {
  const started = performance.now();
  try {
    const pyodide = await loadPyodide();
    await pyodide.loadPackage(["numpy", "opencv-python", "pillow"]);
    pyodide.FS.mkdirTree("/home/pyodide/scanner");
    await Promise.all([
      ...PY_FILES.map(async (name) =>
        pyodide.FS.writeFile(`/home/pyodide/scanner/${name}.py`, await fetchText(`${CONFIG.pyBase}scanner/${name}.py`))),
      fetchText("bridge.py").then((src) => pyodide.FS.writeFile("/home/pyodide/bridge.py", src)),
    ]);
    bridge = pyodide.pyimport("bridge");
    $("#loader").hidden = true;
    $("#upload").hidden = false;
    track("engine_ready", { ms: Math.round(performance.now() - started) });
  } catch (err) {
    $("#loader-text").textContent = t("loadError", "Could not load the scanner engine. Check your connection and reload.");
    track("engine_error", { message: String(err) });
  }
}

async function fetchText(url) {
  const res = await fetch(url, { cache: "no-cache" });   // revalidate, so code updates reach returning visitors
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.text();
}

// ---------- photo input ----------
async function openPhoto(file) {
  if (!file?.type.startsWith("image/")) return;
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale), h = Math.round(bitmap.height * scale);
  const off = new OffscreenCanvas(w, h);
  const octx = off.getContext("2d");
  octx.drawImage(bitmap, 0, 0, w, h);
  state.photo = off;

  const started = performance.now();
  const info = bridge.load(octx.getImageData(0, 0, w, h).data, w, h);
  Object.assign(state, { corners: info.corners, turns: info.turns, mode: "magic" });
  setActiveMode("magic");
  $("#detect-status").textContent = info.detected
    ? t("detected", "✅ Page detected. Drag the corners if needed.")
    : t("notDetected", "⚠️ No page found. Drag the corners onto the page.");
  track("photo_scanned", { detected: info.detected, rotated: info.turns, width: w, height: h, ms: Math.round(performance.now() - started) });

  $("#upload").hidden = true;
  $("#editor").hidden = false;
  drawCrop();
  await processScan();
}

// ---------- crop canvas with draggable corners ----------
function drawCrop() {
  const { photo, corners } = state;
  canvas.width = photo.width;
  canvas.height = photo.height;
  ctx.drawImage(photo, 0, 0);
  const unit = photo.width / canvas.clientWidth;   // image px per CSS px, keeps handles the same on-screen size
  ctx.lineWidth = 3 * unit;
  ctx.strokeStyle = "#22c55e";
  ctx.fillStyle = "rgb(34 197 94 / .12)";
  ctx.beginPath();
  corners.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  corners.forEach(([x, y], i) => {
    ctx.beginPath();
    ctx.arc(x, y, (state.dragging === i ? 14 : 10) * unit, 0, Math.PI * 2);
    ctx.fillStyle = "#ff4d4f";
    ctx.fill();
    ctx.lineWidth = 2 * unit;
    ctx.strokeStyle = "#fff";
    ctx.stroke();
  });
}

function toImageCoords(e) {
  const rect = canvas.getBoundingClientRect();
  const s = canvas.width / rect.width;
  return [(e.clientX - rect.left) * s, (e.clientY - rect.top) * s, s];
}

canvas.addEventListener("pointerdown", (e) => {
  const [x, y, s] = toImageCoords(e);
  const dists = state.corners.map(([cx, cy]) => Math.hypot(cx - x, cy - y));
  const nearest = dists.indexOf(Math.min(...dists));
  if (dists[nearest] > HANDLE_HIT * s * 2) return;
  state.dragging = nearest;
  canvas.setPointerCapture(e.pointerId);
  drawCrop();
});
canvas.addEventListener("pointermove", (e) => {
  if (state.dragging < 0) return;
  const [x, y] = toImageCoords(e);
  state.corners[state.dragging] = [Math.max(0, Math.min(canvas.width - 1, x)), Math.max(0, Math.min(canvas.height - 1, y))];
  drawCrop();
});
canvas.addEventListener("pointerup", () => {
  if (state.dragging < 0) return;
  state.dragging = -1;
  drawCrop();
  track("corners_adjusted");
  processScan();
});
window.addEventListener("resize", () => state.photo && drawCrop());

// ---------- rendering ----------
async function processScan() {
  $("#busy").hidden = false;
  await new Promise(requestAnimationFrame);   // let the spinner paint before the blocking Python call
  const png = bridge.process(state.corners, state.turns, state.mode);
  if (state.pngUrl) URL.revokeObjectURL(state.pngUrl);
  state.pngUrl = URL.createObjectURL(new Blob([png], { type: "image/png" }));
  $("#result").src = state.pngUrl;
  $("#busy").hidden = true;
}

function setActiveMode(mode) {
  document.querySelectorAll("[data-mode]").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
    b.setAttribute("aria-checked", b.dataset.mode === mode);
  });
}

document.querySelectorAll("[data-mode]").forEach((btn) =>
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    setActiveMode(state.mode);
    track("filter_changed", { mode: state.mode });
    processScan();
  }));

$("#rot-left").addEventListener("click", () => rotate(-1));
$("#rot-right").addEventListener("click", () => rotate(1));
function rotate(delta) {
  state.turns = (state.turns + delta + 4) % 4;
  track("rotated", { turns: state.turns });
  processScan();
}

// ---------- pages & downloads ----------
$("#add").addEventListener("click", () => {
  bridge.add_page();
  state.pages.push(state.pngUrl);
  state.pngUrl = null;   // ownership moved to the page thumbnail
  processScan();
  renderPages();
  track("page_added", { pages: state.pages.length, mode: state.mode });
});

function renderPages() {
  const box = $("#pages");
  box.replaceChildren(...state.pages.map((url, i) => {
    const item = document.createElement("div");
    item.className = "page-thumb";
    const img = Object.assign(document.createElement("img"), { src: url, alt: `Page ${i + 1}` });
    const del = Object.assign(document.createElement("button"), { textContent: "×", ariaLabel: `Remove page ${i + 1}` });
    del.addEventListener("click", () => {
      bridge.remove_page(i);
      URL.revokeObjectURL(state.pages.splice(i, 1)[0]);
      renderPages();
    });
    item.append(img, del);
    return item;
  }));
  $("#page-count").textContent = state.pages.length;
  $("#pages-card").hidden = state.pages.length === 0;
}

function download(url, name) {
  Object.assign(document.createElement("a"), { href: url, download: name }).click();
}
$("#save-png").addEventListener("click", () => {
  download(state.pngUrl, "scan.png");
  track("downloaded", { kind: "png", mode: state.mode });
});
$("#save-pdf").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([bridge.pdf()], { type: "application/pdf" }));
  download(url, "scan.pdf");
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  track("downloaded", { kind: "pdf", pages: state.pages.length });
});
$("#new").addEventListener("click", () => {
  $("#editor").hidden = true;
  $("#upload").hidden = false;
  $("#file").value = "";
});

// ---------- upload: picker + drag & drop ----------
$("#file").addEventListener("change", (e) => openPhoto(e.target.files[0]));
const drop = $(".drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
drop.addEventListener("drop", (e) => { e.preventDefault(); openPhoto(e.dataTransfer.files[0]); });

// ---------- feedback ----------
document.querySelectorAll("[data-vote]").forEach((btn) =>
  btn.addEventListener("click", () => {
    state.vote = btn.dataset.vote;
    document.querySelectorAll("[data-vote]").forEach((b) => b.classList.toggle("active", b === btn));
  }));
$("#fb-send").addEventListener("click", () => {
  const text = $("#fb-text").value.trim().slice(0, 2000);
  if (!state.vote && !text) return;
  track("feedback", { vote: state.vote, text, pages: state.pages.length, mode: state.mode });
  $("#fb-send").disabled = true;
  $("#fb-thanks").hidden = false;
});

applyLanguage();
track("page_view", { referrer: document.referrer });
boot();
