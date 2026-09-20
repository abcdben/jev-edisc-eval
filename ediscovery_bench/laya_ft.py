"""Supervised fine-tune of the Laya English checkpoint on a dev split of one corpus.

Recipe follows ConvAI's own fine-tuning notebook (RLCD: REINFORCE over Gaussian
logit noise with a group-mean baseline and a strictly proper scoring reward, plus a
soft cross-entropy term; cosine LR; post-hoc temperature fit), adapted to a single
device (MPS/CPU/CUDA). Like their notebook, we train at max_len=1024 / head_max_len=256.

Split is by document (seeded). Training items are the `compact` Noul question for
every (doc, question) pair in the dev split, with the gold label as a soft target
(0.97 for clean gold, 0.75 for gray-flagged docs). Only the first 1024-token window
of each document is used for training; evaluation may use the chunk lever.

This is a SUPERVISED result and must be reported separately from the zero-shot table.
Evaluate only on <corpus>/ft_test.jsonl; `bench report -d <that file>` restricts every
other model to the same held-out documents.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from pathlib import Path

from .config import MODELS
from .providers.laya_ import LayaProvider
from .providers.typesafe import JevConfig
from .tasks import Document, TaskSet, load_corpus

TRAIN_CFG = dict(
    epochs=2,
    micro_batch=8,
    grad_accum=4,
    group_size=4,
    lr_encoder=2.5e-5,
    lr_head=1.0e-4,
    sigma_start=0.4,
    sigma_end=0.1,
    max_len=1024,
    head_max_len=256,
    target_clean=0.97,
    target_gray=0.75,
    calib_frac=0.10,
    grad_ckpt=False,
    amp=False,  # bf16 autocast on MPS produced NaNs; fp32 is fine
    train_top_layers=8,  # ModernBERT-large has 28; train the top N + final norm + decision head (0 = all)
    neg_ratio=4.0,  # keep at most this many negatives per positive (None = all)
)


# ---------------------------------------------------------------- split ----
def make_split(data: Path, out_dir: Path, frac_train: float = 0.30, seed: int = 11, min_pos: int = 15) -> tuple[Path, Path]:
    """Doc-level split. Guarantees >= min_pos positives per question in train where the corpus has them."""
    rows = [json.loads(l) for l in data.read_text().splitlines() if l.strip()]
    rng = random.Random(seed)
    rng.shuffle(rows)
    n_train = int(round(frac_train * len(rows)))
    qids = sorted({q for r in rows for q in (r.get("labels") or {})})
    train: list[dict] = []
    ids: set[str] = set()
    for q in qids:
        pos = [r for r in rows if q in (r.get("labels") or {}) and r["id"] not in ids]
        for r in pos[:min_pos]:
            train.append(r)
            ids.add(r["id"])
    for r in rows:
        if len(train) >= n_train:
            break
        if r["id"] not in ids:
            train.append(r)
            ids.add(r["id"])
    test = [r for r in rows if r["id"] not in ids]
    out_dir.mkdir(parents=True, exist_ok=True)
    p_tr, p_te = out_dir / "ft_train.jsonl", out_dir / "ft_test.jsonl"
    p_tr.write_text("".join(json.dumps(r) + "\n" for r in train))
    p_te.write_text("".join(json.dumps(r) + "\n" for r in test))
    (out_dir / "ft_split.json").write_text(json.dumps({"seed": seed, "frac_train": frac_train, "train_ids": sorted(ids)}, indent=1))
    return p_tr, p_te


# ---------------------------------------------------------------- items ----
def build_items(ts: TaskSet, docs: list[Document], tok, max_len: int, head_max_len: int, target_clean: float, target_gray: float) -> list[dict]:
    from laya.common import QTYPES, build_sequence, render_options

    prov = LayaProvider(MODELS["laya"], cfg=JevConfig(compact=True), variant="compact")
    items: list[dict] = []
    for d in docs:
        state = prov._state(ts, d.text)
        for qid in ts.qids:
            q = ts.questions[qid]
            qdef = prov._noul(ts, q, prov._instr(q))
            internal = {"t": "noul", "ins": qdef["instructions"], "crit": qdef.get("criteria")}
            seq, markers = build_sequence(tok, state, internal, max_len, head_max_len)
            if len(markers) != len(render_options(internal)):
                continue
            y = 1.0 if d.gold(qid, ts.negative_label) == ts.positive_label else 0.0
            conf = target_gray if qid in d.gray else target_clean
            t_true = conf if y == 1.0 else 1.0 - conf
            items.append({"ids": seq, "markers": markers, "qtype": QTYPES["noul"], "target": [1.0 - t_true, t_true], "label": int(y), "doc": d.id, "q": qid})
    return items


def _collate(items, pad_id, device):
    import torch

    n, L = len(items), max(len(it["ids"]) for it in items)
    kmax = max(len(it["markers"]) for it in items)
    ids = torch.full((n, L), pad_id, dtype=torch.long)
    att = torch.zeros((n, L), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    target = torch.zeros((n, kmax), dtype=torch.float32)
    for i, it in enumerate(items):
        ids[i, : len(it["ids"])] = torch.tensor(it["ids"])
        att[i, : len(it["ids"])] = 1
        k = len(it["markers"])
        mpos[i, :k] = torch.tensor(it["markers"])
        mmask[i, :k] = True
        target[i, : len(it["target"])] = torch.tensor(it["target"])
    qtype = torch.tensor([it["qtype"] for it in items])
    return {k: v.to(device) for k, v in dict(input_ids=ids, attention_mask=att, marker_pos=mpos, marker_mask=mmask, target=target, qtype=qtype).items()}


def _fit_temp(sel):
    import torch

    if len(sel) < 10:
        return 1.0
    kmax = max(len(z) for z, _ in sel)
    Z = torch.full((len(sel), kmax), -1e4)
    T = torch.zeros((len(sel), kmax))
    for i, (z, t) in enumerate(sel):
        Z[i, : len(z)] = torch.tensor(z)
        T[i, : len(t)] = torch.tensor(t, dtype=torch.float32)
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = -(T * torch.log_softmax(Z / log_t.exp(), -1)).sum(-1).mean()
        loss.backward()
        return loss

    opt.step(closure)
    return float(torch.clamp(log_t.exp(), 0.3, 10.0).item())


# ---------------------------------------------------------------- train ----
def train(task: Path, train_data: Path, out_dir: Path, device: str | None = None, log=print, **overrides) -> Path:
    os.environ.setdefault("USE_TF", "0")
    import numpy as np
    import torch
    from huggingface_hub import snapshot_download
    from safetensors.torch import load_file, save_file
    from transformers import AutoTokenizer
    from laya.agent import _fix_tokenizer_config
    from laya.common import build_model, proper_reward

    C = {**TRAIN_CFG, **overrides}
    ts = TaskSet.load(task)
    docs = load_corpus(train_data)

    model_dir = snapshot_download("convaiinnovations/laya", allow_patterns=["*.json", "*.safetensors", "tokenizer/*", "encoder/*"])
    _fix_tokenizer_config(model_dir)
    tok = AutoTokenizer.from_pretrained(os.path.join(model_dir, "tokenizer"))
    cfg = json.load(open(os.path.join(model_dir, "rl_agent_config.json")))
    cfg["max_len"], cfg["head_max_len"] = C["max_len"], C["head_max_len"]

    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"))
    model = build_model(cfg, encoder_dir=os.path.join(model_dir, "encoder"))
    model.load_state_dict(load_file(os.path.join(model_dir, "model.safetensors")), strict=True)
    try:
        model.encoder.config.reference_compile = False
    except Exception:  # noqa: BLE001
        pass
    if C.get("grad_ckpt"):
        model.encoder.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.to(dev).train()

    items = build_items(ts, docs, tok, C["max_len"], C["head_max_len"], C["target_clean"], C["target_gray"])
    rng = random.Random(1)
    rng.shuffle(items)
    n_cal = max(50, int(C["calib_frac"] * len(items)))
    calib, items = items[:n_cal], items[n_cal:]
    if C.get("neg_ratio"):
        pos = [it for it in items if it["label"] == 1]
        neg = [it for it in items if it["label"] == 0]
        items = pos + neg[: int(C["neg_ratio"] * len(pos))]
        rng.shuffle(items)
    n_pos = sum(it["label"] for it in items)
    log(f"[laya-ft] {len(docs)} docs -> {len(items)} train items ({n_pos} positive), {len(calib)} calibration items; device={dev}")

    # Optionally freeze the embeddings and lower encoder layers.
    top = int(C.get("train_top_layers") or 0)
    if top:
        layers = list(model.encoder.layers)
        for p in model.encoder.parameters():
            p.requires_grad_(False)
        for layer in layers[-top:]:
            for p in layer.parameters():
                p.requires_grad_(True)
        for n, p in model.encoder.named_parameters():
            if "final_norm" in n:
                p.requires_grad_(True)
        log(f"[laya-ft] training top {top}/{len(layers)} encoder layers + head")
    enc_params = [p for n, p in model.named_parameters() if n.startswith("encoder.") and p.requires_grad]
    head_params = [p for n, p in model.named_parameters() if not n.startswith("encoder.")]
    opt = torch.optim.AdamW([{"params": enc_params, "lr": C["lr_encoder"]}, {"params": head_params, "lr": C["lr_head"]}], weight_decay=0.01)
    steps_per_epoch = math.ceil(len(items) / (C["micro_batch"] * C["grad_accum"]))
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, steps_per_epoch * C["epochs"]), eta_min=1e-6)
    amp_dtype = torch.float16 if dev.type == "cuda" else torch.bfloat16
    use_amp = dev.type in ("cuda", "mps") and C.get("amp", True)

    def batches(epoch_items):
        """Length-bucketed micro-batches (pads to the longest in the batch, so sort-then-chunk)."""
        srt = sorted(epoch_items, key=lambda it: len(it["ids"]))
        chunks = [srt[i : i + C["micro_batch"]] for i in range(0, len(srt), C["micro_batch"])]
        rng.shuffle(chunks)
        return chunks

    t0 = time.time()
    G = C["group_size"]
    for epoch in range(C["epochs"]):
        sigma = C["sigma_start"] + (C["sigma_end"] - C["sigma_start"]) * (epoch / max(1, C["epochs"] - 1))
        opt.zero_grad(set_to_none=True)
        accum = 0
        ep_loss = 0.0
        n_b = 0
        chunks = batches(items)
        for ci, chunk in enumerate(chunks):
            batch = _collate(chunk, tok.pad_token_id, dev)
            with torch.autocast(dev.type, dtype=amp_dtype, enabled=use_amp):
                logits, act = model(batch["input_ids"], batch["attention_mask"], batch["marker_pos"], batch["marker_mask"], batch["qtype"])
            logits = logits.float()
            mask = batch["marker_mask"]
            k = mask.sum(-1, keepdim=True).float()
            target = batch["target"]
            eps = torch.randn((G,) + logits.shape, device=dev) * sigma * mask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mask
            z = logits.detach().unsqueeze(0) + eps
            q = torch.softmax(z.masked_fill(~mask, -1e4), -1)
            with torch.no_grad():
                r = proper_reward(q, target.unsqueeze(0), batch["qtype"], mask, w_sph=0.75, w_rps=1.0)
                adv = r - r.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sigma**2)
            loss_rl = -(adv * logp).mean()
            loss_ce = -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1)).sum(-1).mean()
            loss = (loss_rl + loss_ce) / C["grad_accum"] + 0.0 * act.sum()
            if not torch.isfinite(loss):
                log(f"[laya-ft] non-finite loss at epoch {epoch+1} batch {ci}; skipping batch")
                opt.zero_grad(set_to_none=True)
                continue
            loss.backward()
            accum += 1
            if accum % C["grad_accum"] == 0 or ci + 1 == len(chunks):
                gn = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
                if torch.isfinite(gn):
                    opt.step()
                else:
                    log(f"[laya-ft] non-finite grad norm at epoch {epoch+1} batch {ci}; skipping step")
                sched.step()
                opt.zero_grad(set_to_none=True)
            ep_loss += loss.item() * C["grad_accum"]
            n_b += 1
            if n_b % 25 == 0:
                log(f"[laya-ft] epoch {epoch+1}/{C['epochs']} batch {n_b}/{len(chunks)} loss={loss.item()*C['grad_accum']:.4f} ce={loss_ce.item():.4f} reward={r.mean().item():.3f} {time.time()-t0:.0f}s")
        log(f"[laya-ft] === epoch {epoch+1} done: avg loss {ep_loss/max(1,n_b):.4f}, {time.time()-t0:.0f}s ===")

    # ---- temperature fit on held-out calibration items --------------------
    model.eval()
    preds = []
    with torch.no_grad():
        for b in range(0, len(calib), 16):
            batch = _collate(calib[b : b + 16], tok.pad_token_id, dev)
            with torch.autocast(dev.type, dtype=amp_dtype, enabled=use_amp):
                l, _ = model(batch["input_ids"], batch["attention_mask"], batch["marker_pos"], batch["marker_mask"], batch["qtype"])
            l = l.float().cpu().numpy()
            for i, it in enumerate(calib[b : b + 16]):
                preds.append((l[i, : len(it["markers"])], it["target"]))
    t_noul = _fit_temp(preds)
    acc = float(np.mean([(float(z[1] > z[0]) == float(t[1] > t[0])) for z, t in preds]))
    log(f"[laya-ft] calibration: fitted noul temperature {t_noul:.3f}; calib-set accuracy {acc:.3f}")

    # ---- save in laya.load()-compatible layout ----------------------------
    out_dir.mkdir(parents=True, exist_ok=True)
    sd = {k: v.detach().half().contiguous().cpu() for k, v in model.state_dict().items()}
    save_file(sd, str(out_dir / "model.safetensors"))
    model.encoder.config.save_pretrained(str(out_dir / "encoder"))
    tok.save_pretrained(str(out_dir / "tokenizer"))
    base_temps = cfg.get("temperature", [1.0, 1.0, 1.0])
    cfg.update(
        fine_tuned=True,
        model_name=f"laya-ft-{ts.name}",
        temperature=[base_temps[0], base_temps[1], t_noul],
        fine_tune={"corpus": ts.name, "train_file": str(train_data), "n_docs": len(docs), "n_items": len(items), **{k: v for k, v in C.items()}},
    )
    (out_dir / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    log(f"[laya-ft] saved to {out_dir} ({time.time()-t0:.0f}s total)")
    return out_dir
