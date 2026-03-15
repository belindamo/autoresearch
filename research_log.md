Autonomous GPT pretraining research using Karpathy's autoresearch framework. We fork belindamo/autoresearch on branch `autoresearch/sundial`, modify `train.py` hyperparameters and architecture, and run 5-minute training experiments on Modal A100-80GB GPUs. The goal is to minimize val_bpb (validation bits per byte). Current best: **1.0387** (down from 1.1186 baseline).

## Sessions

- **Session 1 (2026-03-12):** Set up fork, Modal runner, and ran 4 experiments — baseline (1.1186), higher matrix LR (1.0776 ✓), deeper model (1.1471 ✗), smaller batch size (1.0591 ✓). Full log
- **Session 2 (2026-03-12):** Halved batch size again (2^18→2^17, device*batch=64) — 1357 steps, val*bpb=1.0472 ✓ new best. Full log
- **Session 3 (2026-03-12):** Halved batch further (2^17→2^16, device*batch=32) — 2557 steps but val*bpb=1.0584 ✗ regressed, gradient noise too high. Full log
- **Session 4 (2026-03-13):** Increased embedding LR (0.6→1.0) — val_bpb=1.0458 ✓ small improvement, zero complexity cost. Full log
- **Session 5 (2026-03-13):** Compound: added 2% warmup + matrix LR 0.06→0.08 — val_bpb=1.0437 ✓ new best, improved throughput. Full log
- **Session 6 (2026-03-13):** Reduced warmdown ratio 0.67→0.5 — val_bpb=1.0557 ✗ regressed, long warmdown is important for convergence. Full log
- **Session 7 (2026-03-13):** Reduced weight decay 0.2→0.1 — val_bpb=1.0420 ✓ new best, less regularization helps in short training runs. Full log
- **Session 8 (2026-03-13):** Reduced weight decay 0.1→0.05 — val_bpb=1.0395 ✓ new best, continuing the trend of less regularization for short runs. Full log
- **Session 9 (2026-03-13):** Reduced weight decay 0.05→0.025 — val_bpb=1.0437 ✗ regressed, 0.05 is the sweet spot; further reduction is counterproductive. Full log
- **Session 10 (2026-03-13):** Increased logit softcap 15→30 — val_bpb=1.0440 ✗ regressed, wider logit range hurts; softcap=15 provides beneficial regularization. Full log
- **Session 11 (2026-03-13):** Increased warmdown ratio 0.67→0.75 — val_bpb=1.0401 ✗ regressed, 0.67 is optimal (both higher and lower hurt). Full log
- **Session 12 (2026-03-13):** Increased scalar LR 0.5→0.8 — val_bpb=1.0401 ✗ regressed, scalar LR=0.5 is already well-tuned for per-layer gating. Full log
- **Session 13 (2026-03-13):** Increased matrix LR 0.08→0.1 — val_bpb=1.0413 ✗ regressed, Muon optimizer LR=0.08 is optimal; higher causes overshooting. Full log
- **Session 14 (2026-03-14):** Increased unembedding LR 0.004→0.008 — val*bpb=1.0468 ✗ regressed, lm*head is sensitive to LR; 0.004 is well-calibrated. Full log
- **Session 15 (2026-03-14):** Increased warmup ratio 0.02→0.05 — val_bpb=1.0387 ✓ new best, longer warmup stabilizes early training for Muon optimizer. Full log
- **Session 16 (2026-03-14):** Increased warmup ratio 0.05→0.08 — val_bpb=1.0500 ✗ regressed, too much warmup eats into effective training time; 0.05 is the sweet spot. Full log
- **Session 17 (2026-03-14):** Lowered softcap 15→10 — val_bpb=1.0408 ✗ regressed, tighter logit clamping too restrictive; softcap=15 is optimal (both 10 and 30 are worse). Full log
- **Session 18 (2026-03-14):** Increased embedding LR 1.0→1.5 — val_bpb=1.0475 ✗ regressed, embeddings overshoot at higher LR; 1.0 is optimal (0.6 < 1.0 > 1.5). Full log
- **Session 19 (2026-03-14):** Lowered matrix LR 0.08→0.07 — val_bpb=1.0473 ✗ regressed, Muon LR=0.08 confirmed optimal from both sides (0.07 < 0.08 > 0.1). Full log
- **Session 20 (2026-03-14):** Increased FINAL*LR*FRAC 0.0→0.01 — val_bpb=1.0472 ✗ regressed, full annealing to zero is important for warmdown convergence. Full log
- **Session 21 (2026-03-14):** Increased Adam beta1 0.8→0.9 — val_bpb=1.0517 ✗ regressed, higher momentum too sluggish for short training; beta1=0.8 is well-calibrated. Full log
- **Session 22 (2026-03-14):** Increased x0*lambda init 0.1→0.15 — val*bpb=1.0484 ✗ regressed, stronger skip connections dilute residual stream; init=0.1 is well-calibrated. Full log
- **Session 23 (2026-03-14):** Reduced Muon momentum target 0.95→0.90 — val*bpb=1.0470 ✗ regressed vs 1.0387 best, though at same-throughput comparison it's neutral. Also reverted unlogged beta2/x0*lambda commits. Notable GPU variance: session 15's best (1.0387) was at 1560 steps/16.35% MFU vs typical ~1340 steps/14% MFU. Full log
- **Session 24 (2026-03-14):** Reduced warmdown ratio 0.67→0.60 — val_bpb=1.0491 ✗ regressed, completing the warmdown map: 0.50→1.0557, 0.60→1.0491, **0.67→best**, 0.75→1.0401. Full log
- **Session 25 (2026-03-15):** Increased depth 8→10 (85.9M params, 811 steps) — val_bpb=1.0610 ✗ regressed, larger model gets too few training steps in 5 min to converge; depth 8 is optimal for this time budget. Full log