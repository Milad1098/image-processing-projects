<div align="center">

# پروژه‌های پردازش تصویر · Image Processing Projects

**مجموعه‌ای از ابزارهای کوچک و کاربردی بینایی ماشین، هر کدام با دموی زنده و شرح کامل ساخت**

[![Tests](https://github.com/Milad1098/image-processing-projects/actions/workflows/tests.yml/badge.svg)](https://github.com/Milad1098/image-processing-projects/actions/workflows/tests.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB)
![OpenCV](https://img.shields.io/badge/OpenCV-5-5C3EE8)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](#english)

</div>

<div dir="rtl">

| # | پروژه | تکنیک‌های اصلی | دمو | وضعیت |
|---|---|---|---|---|
| 01 | [**اسکنر اسناد**](01-document-scanner/) | لبه‌یابی، کانتور، تبدیل پرسپکتیو، حذف سایه، آستانه‌گذاری تطبیقی | [امتحانش کن](https://miladmobaseri.ir/fa/tools/scanner) | ✅ |
| 02 | [**ساخت پیکسل‌آرت**](02-pixel-art/) | K-Means از صفر، فضای رنگ CIELAB، دیترینگ؛ هر تصمیم با آزمایش | به‌زودی | ✅ |
| 03 | [**حذف پس‌زمینه**](03-background-removal/) | یادگیری عمیق در مرورگر (ONNX)؛ مقایسه‌ی ۵ مدل روی دو دیتاست استاندارد | به‌زودی | ✅ |
| 04 | افزایش کیفیت تصویر | سوپررزولوشن با یادگیری عمیق | | ⏳ |

</div>

<p align="center">
  <a href="01-document-scanner/"><img src="01-document-scanner/docs/images/before-after.jpg" height="300" alt="Document scanner: phone photo and cleaned scan"></a>
  <a href="02-pixel-art/"><img src="02-pixel-art/docs/images/lab-vs-rgb.png" height="300" alt="Pixel art: RGB vs CIELAB color clustering"></a>
  <a href="03-background-removal/"><img src="03-background-removal/docs/images/hero.png" height="300" alt="Background removal in the browser"></a>
</p>

---

<a name="english"></a>
## English

A series of small, practical computer-vision tools. Each one ships with a live demo,
tests, and a case study of how it was built, including what failed along the way.

| # | Project | Core techniques | Demo | Status |
|---|---|---|---|---|
| 01 | [**Document Scanner**](01-document-scanner/) | Edge detection, contours, perspective transform, shadow removal, adaptive threshold; runs in the browser via WebAssembly | [Try it](https://miladmobaseri.ir/en/tools/scanner) | ✅ |
| 02 | [**Pixel Art Maker**](02-pixel-art/) | K-Means from scratch, CIELAB, dithering (wavefront-vectorized Floyd–Steinberg); every decision backed by a reproducible experiment | soon | ✅ |
| 03 | [**Background Remover**](03-background-removal/) | Deep learning in the browser (ONNX Runtime Web); 5 networks + a classic baseline benchmarked on two public datasets | soon | ✅ |
| 04 | Image Super-Resolution | Deep-learning upscaling | | ⏳ |

Each project is self-contained: its own `requirements.txt`, README, tests and `docs/`.

## License

[MIT](LICENSE) © Milad Mobaseri
