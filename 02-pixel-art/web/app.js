// Browser front-end. All image processing runs in Python (Pyodide) via bridge.py.
//
// Optional config, set before this script loads:
//   window.PIXELART_CONFIG = { endpoint: "/api/tool-events/", pyBase: "" }
// `endpoint` receives analytics + feedback as JSON POSTs. Without it, events only go to the console.

const CONFIG = { pyBase: "../", endpoint: null, ...window.PIXELART_CONFIG };
const PY_FILES = ["__init__", "color", "quantize", "dither", "palettes", "pipeline"];
const MAX_SIDE = 1024;   // input is shrunk to this first; pixel art never needs more

const I18N = {
  fa: {
    back: "→ بازگشت به سایت", title: "ساخت پیکسل‌آرت", tagline: "هر عکسی رو به پیکسل‌آرت تبدیل کن. کاملاً داخل مرورگر خودت اجرا می‌شه.",
    by: "ساخته‌شده توسط", author: "میلاد مبصری", loading: "در حال بارگذاری موتور… (فقط بار اول، حدود ۱۵ ثانیه)",
    choose: "یه عکس انتخاب کن", drop: "یا اینجا رهاش کن", original: "عکس اصلی", result: "پیکسل‌آرت",
    size: "اندازه (تعداد پیکسل در عرض)", palette: "پالت رنگ", auto: "یادگرفته از خود عکس", gray4: "خاکستری (۴)",
    colors: "تعداد رنگ", dither: "دیترینگ", ditherNone: "بدون دیترینگ (رنگ‌های تخت)",
    ditherBayer: "Bayer (الگوی رترو)", ditherFs: "Floyd–Steinberg (نرم)", space: "روش تطبیق رنگ",
    spaceLab: "ادراکی (CIELAB)", spaceRgb: "RGB ساده (برای مقایسه)",
    spaceHint: "با رنگ کم روی RGB بزن تا ببینی جزئیات کوچک و پررنگ چطور گم می‌شن.",
    used: "رنگ‌های استفاده‌شده", save: "⬇ دانلود PNG", new: "↺ یه عکس دیگه",
    fbTitle: "چطور بود؟", good: "👍 عالی شد", bad: "👎 مشکل داشت",
    fbPlaceholder: "چه مشکلی بود یا چه امکانی اضافه بشه؟ (اختیاری)", send: "ارسال نظر",
    thanks: "ممنون! نظرت ارسال شد.", privacy: "🔒 عکس‌هات روی دستگاه خودت پردازش می‌شن و هیچ‌وقت آپلود نمی‌شن.",
    loadError: "بارگذاری موتور ناموفق بود. اینترنت رو چک کن و صفحه رو دوباره باز کن.",
  },
};
const lang = new URLSearchParams(location.search).get("lang") === "fa" ? "fa" : "en";
const t = (key, fallback) => I18N[lang]?.[key] ?? fallback;
const $ = (sel) => document.querySelector(sel);

let bridge = null;
let artUrl = null;
let vote = null;
let rendering = false, pending = false;
const sessionId = crypto.randomUUID?.() ?? String(Math.random());

// ---------- analytics & feedback ----------
function track(event, data = {}) {
  const payload = { tool: "pixelart", event, ...data, lang, session: sessionId, ts: new Date().toISOString(), ua: navigator.userAgent };
  console.debug("[pixelart]", payload);
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
  if (lang === "fa") document.title = "ساخت پیکسل‌آرت — میلاد مبصری";
}

// ---------- engine ----------
async function fetchText(url) {
  const res = await fetch(url, { cache: "no-cache" });   // revalidate, so code updates reach returning visitors
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.text();
}

async function boot() {
  const started = performance.now();
  try {
    const pyodide = await loadPyodide();
    await pyodide.loadPackage(["numpy", "opencv-python"]);
    pyodide.FS.mkdirTree("/home/pyodide/pixelart");
    await Promise.all([
      ...PY_FILES.map(async (name) =>
        pyodide.FS.writeFile(`/home/pyodide/pixelart/${name}.py`, await fetchText(`${CONFIG.pyBase}pixelart/${name}.py`))),
      fetchText("bridge.py").then((src) => pyodide.FS.writeFile("/home/pyodide/bridge.py", src)),
    ]);
    bridge = pyodide.pyimport("bridge");
    $("#loader").hidden = true;
    $("#upload").hidden = false;
    track("engine_ready", { ms: Math.round(performance.now() - started) });
  } catch (err) {
    $("#loader-text").textContent = t("loadError", "Could not load the engine. Check your connection and reload.");
    track("engine_error", { message: String(err) });
  }
}

// ---------- photo input ----------
async function openPhoto(file) {
  if (!file?.type.startsWith("image/")) return;
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale), h = Math.round(bitmap.height * scale);
  const canvas = new OffscreenCanvas(w, h);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bitmap, 0, 0, w, h);
  bridge.load(ctx.getImageData(0, 0, w, h).data, w, h);
  $("#photo").src = URL.createObjectURL(await canvas.convertToBlob());
  track("photo_loaded", { width: w, height: h });

  $("#upload").hidden = true;
  $("#editor").hidden = false;
  render();
}

// ---------- rendering ----------
function settings() {
  const palette = $("#palette").value;
  return {
    width: +$("#width").value,
    colors: palette === "auto" ? +$("#colors").value : palette,
    dither: $("#dither").value,
    space: $("#space").value,
  };
}

async function render() {
  if (rendering) { pending = true; return; }   // coalesce rapid changes into one follow-up render
  rendering = true;
  $("#busy").hidden = false;
  await new Promise(requestAnimationFrame);    // let the spinner paint before the blocking Python call
  const s = settings();
  const started = performance.now();
  const res = bridge.process(s.width, s.colors, s.dither, s.space);
  if (artUrl) URL.revokeObjectURL(artUrl);
  artUrl = URL.createObjectURL(new Blob([res.png], { type: "image/png" }));
  $("#art").src = artUrl;
  $("#swatches").replaceChildren(...res.colors.map((hex) =>
    Object.assign(document.createElement("span"), { title: hex, style: `background:${hex}` })));
  track("rendered", { ...s, colors: String(s.colors), ms: Math.round(performance.now() - started) });
  $("#busy").hidden = true;
  rendering = false;
  if (pending) { pending = false; render(); }
}

// ---------- controls ----------
for (const id of ["width", "colors"]) {
  $(`#${id}`).addEventListener("input", (e) => ($(`#${id}-out`).textContent = e.target.value));
  $(`#${id}`).addEventListener("change", render);   // on release, not on every slider step
}
for (const id of ["dither", "space"]) $(`#${id}`).addEventListener("change", render);
$("#palette").addEventListener("change", () => {
  const auto = $("#palette").value === "auto";
  $("#colors-field").hidden = !auto;   // fixed palettes have their own size
  render();
});

$("#save").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([bridge.download()], { type: "image/png" }));
  Object.assign(document.createElement("a"), { href: url, download: "pixel-art.png" }).click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  track("downloaded", { ...settings(), colors: String(settings().colors) });
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
    vote = btn.dataset.vote;
    document.querySelectorAll("[data-vote]").forEach((b) => b.classList.toggle("active", b === btn));
  }));
$("#fb-send").addEventListener("click", () => {
  const text = $("#fb-text").value.trim().slice(0, 2000);
  if (!vote && !text) return;
  track("feedback", { vote, text, ...settings(), colors: String(settings().colors) });
  $("#fb-send").disabled = true;
  $("#fb-thanks").hidden = false;
});

applyLanguage();
track("page_view", { referrer: document.referrer });
boot();
