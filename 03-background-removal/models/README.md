# Model weights

Not committed. Fetch them with `python -m experiments.download`.

| key | file | architecture | trained for | license | source |
|---|---|---|---|---|---|
| `u2netp` | u2netp.onnx | U²-Net, small variant | salient objects | Apache-2.0 | [xuebinqin/U-2-Net](https://github.com/xuebinqin/U-2-Net), ONNX via [rembg](https://github.com/danielgatis/rembg) |
| `silueta` | silueta.onnx | U²-Net, pruned | salient objects | Apache-2.0 | [rembg](https://github.com/danielgatis/rembg) |
| `modnet` | modnet.onnx | MODNet | portrait matting | Apache-2.0 | [ZHKKKe/MODNet](https://github.com/ZHKKKe/MODNet), ONNX via [Xenova/modnet](https://huggingface.co/Xenova/modnet) |
| `isnet` | isnet-general-use.onnx | IS-Net (DIS) | general use | Apache-2.0 | [xuebinqin/DIS](https://github.com/xuebinqin/DIS), ONNX via [rembg](https://github.com/danielgatis/rembg) |
| `birefnet-lite` | birefnet-lite.onnx | BiRefNet, Swin-T backbone | general use | MIT | [ZhengPeng7/BiRefNet](https://github.com/ZhengPeng7/BiRefNet), ONNX via [onnx-community](https://huggingface.co/onnx-community/BiRefNet_lite-ONNX) |

Deliberately excluded: BRIA RMBG (non-commercial license).
