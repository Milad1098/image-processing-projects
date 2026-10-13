# Roadmap

- [ ] **WebGPU.** ONNX Runtime Web's WebGPU backend could bring IS-Net or BiRefNet within
  reach on capable devices; measure and fall back to WASM elsewhere.
- [ ] **Quantized models** (int8 / fp16): smaller downloads; measure the accuracy cost with
  the existing benchmark before shipping.
- [ ] **Automatic mode.** A tiny person detector (or MODNet's own confidence) to pick the
  model, instead of asking the user.
- [x] **Edge refinement.** Done: edge tightening (guided filter evaluated and rejected).
- [ ] **Color decontamination.** Re-estimate foreground colors in the soft edge band so fine
  hair can stay semi-transparent without a halo; needs a test set with true foreground colors.
- [ ] **More test data:** product photos and fine structures (DIS5K), the case where the
  current object model is weakest.
