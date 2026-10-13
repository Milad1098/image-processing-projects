// Background remover, fully client-side: ONNX Runtime Web runs the network, this file does
// the same pre/post-processing as bgremove/models.py (tests/test_web_parity checks they agree).
//
// Optional config, set before this script loads:
//   window.BGREMOVE_CONFIG = { endpoint: "/api/tool-events/" }
// `endpoint` receives analytics + feedback as JSON POSTs. Without it, events only go to the console.

const CONFIG = { endpoint: null, ...window.BGREMOVE_CONFIG };
const IMAGENET = { mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225] };
// Model files on Hugging Face (CORS-enabled), pinned to a commit so they can never change under us.
// Both are byte-identical to the files benchmarked in docs/RESULTS.md.
const MODELS = {
  person: {
    url: "https://huggingface.co/Xenova/modnet/resolve/fa2fa546052fba4c08921230a26cc69a333fca12/onnx/model.onnx",
    mb: 26, size: null, mean: [0.5, 0.5, 0.5], std: [0.5, 0.5, 0.5], output: "alpha", divideByMax: false,
  },
  object: {
    url: "https://huggingface.co/BritishWerewolf/U-2-Netp/resolve/7112208dbac3a3642496c8d54e2f0f9bb3dc1dc8/onnx/model.onnx",
    mb: 5, size: 320, ...IMAGENET, output: "minmax", divideByMax: true,
  },
};
const MODNET_REF = 512;   // MODNet short side, as in models.py
const MAX_SIDE = 2048;    // input photos are shrunk to this first (memory on phones)
const CREDIT = "miladmobaseri.ir";

const I18N = {
  fa: {
    back: "→ بازگشت به سایت", title: "حذف پس‌زمینه", tagline: "پس‌زمینه‌ی عکس رو با یادگیری عمیق حذف کن. کاملاً داخل مرورگر خودت اجرا می‌شه.",
    by: "ساخته‌شده توسط", author: "میلاد مبصری", modeLabel: "توی عکس چی هست؟", person: "👤 آدم", object: "📦 شیء / محصول",
    personNote: "مدل پرتره (MODNet، ۲۶ مگابایت): بهترین برای آدم‌ها، حتی مو.",
    objectNote: "مدل عمومی سبک (U²-Net-P، ۵ مگابایت): برای اشیا و محصولات؛ روی سوژه‌های شلوغ دقتش کمتره.",
    choose: "یه عکس انتخاب کن", drop: "یا اینجا رهاش کن", original: "عکس اصلی", result: "نتیجه",
    bgLabel: "پس‌زمینه‌ی جدید", transparent: "شفاف", white: "سفید", color: "رنگی", blur: "محو",
    save: "⬇ دانلود PNG", new: "↺ یه عکس دیگه", fbTitle: "چطور بود؟", good: "👍 تمیز درآمد", bad: "👎 مشکل داشت",
    fbPlaceholder: "چه مشکلی بود یا چه امکانی اضافه بشه؟ (اختیاری)", send: "ارسال نظر", thanks: "ممنون! نظرت ارسال شد.",
    privacy: "🔒 عکس‌هات روی دستگاه خودت پردازش می‌شن و هیچ‌وقت آپلود نمی‌شن.",
    downloading: "در حال دانلود مدل ({mb} مگابایت، فقط بار اول)…", running: "در حال حذف پس‌زمینه…",
    loadError: "دانلود مدل ناموفق بود. اینترنت رو چک کن و دوباره امتحان کن.", took: "{ms} میلی‌ثانیه روی دستگاه شما",
  },
};
const lang = new URLSearchParams(location.search).get("lang") === "fa" ? "fa" : "en";
const t = (key, fallback, vars = {}) => (I18N[lang]?.[key] ?? fallback).replace(/\{(\w+)\}/g, (_, k) => vars[k]);
const $ = (sel) => document.querySelector(sel);

const state = { mode: "person", bg: "transparent", photo: null, alpha: null, vote: null };
const sessions = {};
const sessionId = crypto.randomUUID?.() ?? String(Math.random());

ort.env.wasm.wasmPaths = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/";
// threads need cross-origin isolation, which a normal page doesn't have; one thread then
ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;

// ---------- analytics & feedback ----------
function track(event, data = {}) {
  const payload = { tool: "bgremove", event, ...data, lang, session: sessionId, ts: new Date().toISOString(), ua: navigator.userAgent };
  console.debug("[bgremove]", payload);
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
  if (lang === "fa") document.title = "حذف پس‌زمینه — میلاد مبصری";
}

// ---------- model download (cached across visits) ----------
async function fetchModel(spec) {
  const cache = await caches.open("bgremove-models-v1").catch(() => null);
  const hit = await cache?.match(spec.url);
  if (hit) return new Uint8Array(await hit.arrayBuffer());

  const res = await fetch(spec.url);
  if (!res.ok) throw new Error(`model download: ${res.status}`);
  const total = +res.headers.get("content-length") || spec.mb * 1e6;
  const reader = res.body.getReader();
  const bytes = new Uint8Array(total);
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    bytes.set(value, got);
    got += value.length;
    $("#progress-bar").style.width = `${Math.min(100, (got / total) * 100)}%`;
  }
  const data = bytes.subarray(0, got);
  cache?.put(spec.url, new Response(data)).catch(() => {});   // best effort: private mode may refuse
  return data;
}

async function getSession(mode) {
  if (!sessions[mode]) {
    const spec = MODELS[mode];
    $("#loader-text").textContent = t("downloading", "Downloading the model ({mb} MB, first time only)…", { mb: spec.mb });
    const started = performance.now();
    sessions[mode] = ort.InferenceSession.create(await fetchModel(spec), { executionProviders: ["wasm"] });
    await sessions[mode];
    track("model_ready", { mode, ms: Math.round(performance.now() - started) });
  }
  return sessions[mode];
}

// ---------- pre/post-processing (mirrors bgremove/models.py) ----------
function inputSize(spec, h, w) {
  if (spec.size) return [spec.size, spec.size];
  const scale = MODNET_REF / Math.min(h, w);
  return [Math.max(32, Math.round((h * scale) / 32) * 32), Math.max(32, Math.round((w * scale) / 32) * 32)];
}

function preprocess(source, spec) {
  const [ih, iw] = inputSize(spec, source.height, source.width);
  const canvas = new OffscreenCanvas(iw, ih);
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(source, 0, 0, iw, ih);
  const px = ctx.getImageData(0, 0, iw, ih).data;
  let scale = 255;
  if (spec.divideByMax) {
    scale = 1;
    for (let i = 0; i < px.length; i += 4) scale = Math.max(scale, px[i], px[i + 1], px[i + 2]);
  }
  const plane = ih * iw;
  const data = new Float32Array(3 * plane);
  for (let i = 0; i < plane; i++) {
    for (let c = 0; c < 3; c++) data[c * plane + i] = (px[i * 4 + c] / scale - spec.mean[c]) / spec.std[c];
  }
  return new ort.Tensor("float32", data, [1, 3, ih, iw]);
}

function postprocess(output, spec, width, height) {
  const [, , ih, iw] = output.dims;
  const m = output.data;
  let lo = 0, hi = 1;
  if (spec.output === "minmax") {
    lo = Infinity; hi = -Infinity;
    for (const v of m) { if (v < lo) lo = v; if (v > hi) hi = v; }
  }
  const small = new ImageData(iw, ih);
  for (let i = 0; i < m.length; i++) {
    const a = Math.round(Math.min(1, Math.max(0, (m[i] - lo) / Math.max(hi - lo, 1e-6))) * 255);
    small.data[i * 4] = small.data[i * 4 + 1] = small.data[i * 4 + 2] = a;
    small.data[i * 4 + 3] = 255;
  }
  const src = new OffscreenCanvas(iw, ih);
  src.getContext("2d").putImageData(small, 0, 0);
  const full = new OffscreenCanvas(width, height);
  const ctx = full.getContext("2d");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(src, 0, 0, width, height);   // bilinear upscale of the matte, like cv2.INTER_LINEAR
  const up = ctx.getImageData(0, 0, width, height).data;
  const alpha = new Uint8ClampedArray(width * height);
  for (let i = 0; i < alpha.length; i++) alpha[i] = up[i * 4];
  return alpha;
}

async function removeBackground(source, mode) {
  const spec = MODELS[mode];
  const session = await getSession(mode);
  $("#loader-text").textContent = t("running", "Removing the background…");
  await new Promise(requestAnimationFrame);
  const started = performance.now();
  const result = await session.run({ [session.inputNames[0]]: preprocess(source, spec) });
  const alpha = postprocess(result[session.outputNames[0]], spec, source.width, source.height);
  return { alpha, ms: Math.round(performance.now() - started) };
}
window.__bgremove = { removeBackground, inputSize };   // used by the parity test

// ---------- composition ----------
function compose(canvas, { withCredit = false } = {}) {
  const { photo, alpha } = state;
  const w = photo.width, h = photo.height;
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");

  const cut = new OffscreenCanvas(w, h);
  const cctx = cut.getContext("2d");
  cctx.drawImage(photo, 0, 0);
  const px = cctx.getImageData(0, 0, w, h);
  for (let i = 0; i < alpha.length; i++) px.data[i * 4 + 3] = alpha[i];
  cctx.putImageData(px, 0, 0);

  ctx.clearRect(0, 0, w, h);
  if (state.bg === "white" || state.bg === "color") {
    ctx.fillStyle = state.bg === "white" ? "#ffffff" : $("#bg-color").value;
    ctx.fillRect(0, 0, w, h);
  } else if (state.bg === "blur") {
    ctx.filter = `blur(${Math.round(Math.max(w, h) / 80)}px)`;
    ctx.drawImage(photo, 0, 0);
    ctx.filter = "none";
  }
  ctx.drawImage(cut, 0, 0);

  if (withCredit) {
    const size = Math.max(11, Math.round(w / 70));
    ctx.font = `${size}px sans-serif`;
    ctx.textAlign = "right";
    ctx.fillStyle = "rgba(128, 128, 128, 0.7)";
    ctx.fillText(CREDIT, w - size * 0.6, h - size * 0.6);
  }
}

// ---------- flow ----------
async function openPhoto(file) {
  if (!file?.type.startsWith("image/")) return;
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const photo = new OffscreenCanvas(Math.round(bitmap.width * scale), Math.round(bitmap.height * scale));
  photo.getContext("2d").drawImage(bitmap, 0, 0, photo.width, photo.height);
  state.photo = photo;
  $("#photo").src = URL.createObjectURL(await photo.convertToBlob());
  await run();
}

async function run() {
  if (!state.photo) return;
  $("#upload").hidden = true;
  $("#loader").hidden = false;
  $("#progress-bar").style.width = "0";
  try {
    const { alpha, ms } = await removeBackground(state.photo, state.mode);
    state.alpha = alpha;
    compose($("#result-canvas"));
    $("#timing").textContent = t("took", "{ms} ms on your device", { ms });
    $("#editor").hidden = false;
    track("removed", { mode: state.mode, ms, width: state.photo.width, height: state.photo.height });
  } catch (err) {
    $("#loader-text").textContent = t("loadError", "Could not download the model. Check your connection and try again.");
    track("model_error", { mode: state.mode, message: String(err) });
    $("#upload").hidden = false;
    return;
  }
  $("#loader").hidden = true;
}

function select(attr, value) {
  document.querySelectorAll(`[data-${attr}]`).forEach((b) => {
    b.classList.toggle("active", b.dataset[attr] === value);
    b.setAttribute("aria-checked", b.dataset[attr] === value);
  });
}

document.querySelectorAll("[data-mode]").forEach((btn) => btn.addEventListener("click", () => {
  state.mode = btn.dataset.mode;
  select("mode", state.mode);
  $("#mode-note").textContent = state.mode === "person"
    ? t("personNote", "Portrait model (MODNet, 26 MB): best for people, hair included.")
    : t("objectNote", "Light general model (U²-Net-P, 5 MB): for objects and products; less accurate on busy scenes.");
  track("mode_changed", { mode: state.mode });
  run();
}));

document.querySelectorAll("[data-bg]").forEach((btn) => btn.addEventListener("click", () => {
  state.bg = btn.dataset.bg;
  select("bg", state.bg);
  $("#bg-color").hidden = state.bg !== "color";
  $("#result-view").classList.toggle("checker", state.bg === "transparent");
  if (state.alpha) compose($("#result-canvas"));
  track("background_changed", { bg: state.bg });
}));
$("#bg-color").addEventListener("input", () => state.alpha && compose($("#result-canvas")));

$("#save").addEventListener("click", () => {
  const canvas = document.createElement("canvas");
  compose(canvas, { withCredit: true });
  canvas.toBlob((blob) => {
    const url = URL.createObjectURL(blob);
    Object.assign(document.createElement("a"), { href: url, download: "no-background.png" }).click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }, "image/png");
  track("downloaded", { mode: state.mode, bg: state.bg });
});
$("#new").addEventListener("click", () => {
  $("#editor").hidden = true;
  $("#upload").hidden = false;
  $("#file").value = "";
  state.photo = state.alpha = null;
});

$("#file").addEventListener("change", (e) => openPhoto(e.target.files[0]));
const drop = $(".drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
drop.addEventListener("drop", (e) => { e.preventDefault(); openPhoto(e.dataTransfer.files[0]); });

document.querySelectorAll("[data-vote]").forEach((btn) => btn.addEventListener("click", () => {
  state.vote = btn.dataset.vote;
  document.querySelectorAll("[data-vote]").forEach((b) => b.classList.toggle("active", b === btn));
}));
$("#fb-send").addEventListener("click", () => {
  const text = $("#fb-text").value.trim().slice(0, 2000);
  if (!state.vote && !text) return;
  track("feedback", { vote: state.vote, text, mode: state.mode, bg: state.bg });
  $("#fb-send").disabled = true;
  $("#fb-thanks").hidden = false;
});

applyLanguage();
track("page_view", { referrer: document.referrer });
