"""Logit lens on the saved replay-2 last layer (probe idea 2): the model's own first-reply-token forecast.

The saved activation is the output of decoder block 63 at the last prompt token (after the generation prompt
"<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n"), before the final norm (E02 replay.py `capture`,
provenance 'decoder block output, last prompt token, before final model norm'). So we apply Qwen3 RMSNorm
(eps from config) -> lm_head -> softmax in float32 and read the next-token distribution.

Features (no training): p_refusal (mass on refusal-opener tokens), p_tool (mass on <tool_call>), entropy, p_max.
Scores: each scalar with a predeclared sign, plus a logistic regression on the four scalars cross-fitted on the
E05 replay-2 folds (3 split seeds x 5 folds; fit on train + calibration episodes, score test episodes).
Metric: E05 within_round with stratum_key=scenario on recruiting rows, family-bootstrap CI (ranking_summary).
Labels: eventual (rows.jsonl) and near-term A_hazard (runs/20261025-0730-e05-near-term/labels.jsonl).

Run (CPU, 2 threads):
    OMP_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 uv run --no-project --with numpy==2.4.6 --with scikit-learn==1.8.0 \\
        --with scipy==1.17.1 --with tokenizers python experiments/E05-probes/explore_logit_lens.py [--peek 12]
Needs model-00017-of-00017.safetensors of Qwen/Qwen3-32B@REVISION in the HF cache (holds model.norm.weight
and lm_head.weight; see model.safetensors.index.json).
"""
import argparse
import csv
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ.setdefault(_v, '2')

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'experiments/E06-monitors'))
sys.path.insert(0, str(ROOT / 'src'))
from metrics import auc, within_round  # noqa: E402
from evaluate import ranking_summary  # noqa: E402

MODEL = 'Qwen/Qwen3-32B'
REVISION = '9216db5781bf21249d130ec9da846c4624c16137'  # experiments/E02-activation-replay/plan_main.py
SNAP = Path(os.environ.get('HF_HUB_CACHE', Path.home() / '.cache/huggingface/hub')) / \
    f'models--Qwen--Qwen3-32B/snapshots/{REVISION}'
SHARD = 'model-00017-of-00017.safetensors'
DATA = ROOT / 'runs/20261025-0337-e05-replay2-data'
FOLDS = ROOT / 'runs/20261025-0240-e05-replay2-folds'
NEAR_TERM = ROOT / 'runs/20261025-0730-e05-near-term/labels.jsonl'
LAYER = 63
BATCH = 128
TOPK = 50
REPS = 1000
# Chosen after inspecting the top tokens on held and leaking recruiting rows (--peek); single tokens only.
# "I'm"/"I'll" etc. start with the token "I", so "I" covers them; "I" also opens compliant text replies.
REFUSAL_STRINGS = ['I', ' I', 'Sorry', ' Sorry', 'Unfortunately', ' Unfortunately', "I'm", " I'm"]
TOOL_STRINGS = ['<tool_call>']
SCALARS = ['p_refusal', 'p_tool', 'entropy', 'p_max']
# Predeclared direction (higher score = more likely to give in): less refusal mass, more tool-call mass,
# more uncertainty, less confidence.
SIGN = {'p_refusal': -1, 'p_tool': 1, 'entropy': 1, 'p_max': -1}


def load_bf16(path, names):
    """Read bf16 tensors from a safetensors file without the safetensors/torch packages."""
    with open(path, 'rb') as fh:
        n = struct.unpack('<Q', fh.read(8))[0]
        header = json.loads(fh.read(n))
        out = {}
        for name in names:
            info = header[name]
            assert info['dtype'] == 'BF16', info
            a, b = info['data_offsets']
            fh.seek(8 + n + a)
            raw = np.frombuffer(fh.read(b - a), dtype='<u2')
            out[name] = (raw.astype(np.uint32) << 16).view(np.float32).reshape(info['shape'])
    return out


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def token_ids(tok, strings):
    """Map each string to its id when it is exactly one token; report the rest."""
    ids, skipped = {}, []
    for s in strings:
        t = tok.token_to_id(s) if s.startswith('<') else None
        if t is None:
            enc = tok.encode(s, add_special_tokens=False).ids
            t = enc[0] if len(enc) == 1 else None
        (skipped.append(s) if t is None else ids.__setitem__(s, t))
    return ids, skipped


def first_reply_tokens(rows, tok):
    """First generated token of each row's actual reply (None if unknown), from the episode JSON."""
    cache, out, kinds = {}, [], []
    tool_id = tok.token_to_id('<tool_call>')
    for r in rows:
        run, ep = r['episode'].split('/', 1)
        if r['episode'] not in cache:
            cache[r['episode']] = json.loads((ROOT / 'runs' / run / 'episodes' / ep).read_text())
        rec = cache[r['episode']]['requests'][r['request_idx']]
        assert rec['actor'] == 'target' and digest(rec['request']) == r['request_sha256'], r['episode']
        try:
            msg = rec['response']['choices'][0]['message']
        except (KeyError, IndexError, TypeError):
            out.append(None); kinds.append('missing'); continue
        content = msg.get('content') or ''
        if msg.get('reasoning'):
            out.append(None); kinds.append('reasoning'); continue
        if content.strip():
            out.append(tok.encode(content, add_special_tokens=False).ids[0]); kinds.append('text')
        elif msg.get('tool_calls'):
            out.append(tool_id); kinds.append('tool_call')
        else:
            out.append(None); kinds.append('empty')
    return out, kinds


def lens(features, index, norm_w, head_t, eps, feature_ids, extra_ids):
    """RMSNorm -> lm_head -> softmax per row, float32. Returns per-row scalars, top-k and selected log-probs."""
    n = len(index)
    res = {k: np.zeros(n, np.float32) for k in ('entropy', 'p_max')}
    res['top_ids'] = np.zeros((n, TOPK), np.int64); res['top_p'] = np.zeros((n, TOPK), np.float32)
    res['cand_logp'] = np.zeros((n, len(feature_ids)), np.float32)
    res['extra_logp'] = np.full(n, np.nan, np.float32)
    for start in range(0, n, BATCH):
        sl = slice(start, start + BATCH)
        h = np.stack([np.asarray(features[i, LAYER], dtype=np.float32) for i in index[sl]])
        h = h / np.sqrt((h * h).mean(axis=1, keepdims=True) + eps) * norm_w
        logits = h @ head_t
        logits -= logits.max(axis=1, keepdims=True)
        logz = np.log(np.exp(logits).sum(axis=1, keepdims=True))
        logp = logits - logz
        p = np.exp(logp)
        res['entropy'][sl] = -(p * logp).sum(axis=1)
        top = np.argpartition(-logp, TOPK, axis=1)[:, :TOPK]
        order = np.argsort(-np.take_along_axis(logp, top, 1), axis=1)
        top = np.take_along_axis(top, order, 1)
        res['top_ids'][sl] = top; res['top_p'][sl] = np.take_along_axis(p, top, 1)
        res['p_max'][sl] = res['top_p'][sl][:, 0]
        res['cand_logp'][sl] = logp[:, feature_ids]
        ex = extra_ids[sl]
        ok = ex >= 0
        res['extra_logp'][sl][ok] = logp[np.flatnonzero(ok), ex[ok]]
        print(f'lens rows {min(start + BATCH, n)}/{n}', flush=True)
    return res


def show(tok, ids, probs, k=5):
    return ' | '.join(f'{tok.id_to_token(int(i))!r} {float(q):.3f}' for i, q in zip(ids[:k], probs[:k]))


def cross_fit(X, y_all, folds, train_ok):
    """{seed: out-of-fold LR decision scores} for every row index covered by the folds' test episodes."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    out = {}
    for f in folds:
        s = out.setdefault(f['seed'], np.full(len(X), np.nan))
        tr = np.array([i for i in f['train_indices'] + f['calibration_indices'] if train_ok[i]])
        te = np.array([i for i in f['test_indices'] if np.isfinite(X[i]).all()])
        scaler = StandardScaler().fit(X[tr])
        model = LogisticRegression(C=1.0, max_iter=2000).fit(scaler.transform(X[tr]), y_all[tr].astype(int))
        s[te] = model.decision_function(scaler.transform(X[te]))
    return out


def rank(rows_idx, rows, per_seed, labels, test_fold=None):
    """Within scenario x round AUROC + family-bootstrap CIs on recruiting rows with a label."""
    from score import added_value  # E06 helper: OOF turn + log length, then + score
    keep = np.array([rows[i]['condition'] == 'recruiting' and labels[i] is not None for i in rows_idx])
    idx = np.asarray(rows_idx)[keep]
    S = np.array([per_seed[s][idx] for s in sorted(per_seed)])
    ok = np.isfinite(S).all(axis=0); idx, S = idx[ok], S[:, ok]
    y = np.array([labels[i] for i in idx]); rounds = np.array([rows[i]['round'] for i in idx])
    fam = np.array([rows[i]['family'] for i in idx]); scen = np.array([rows[i]['scenario'] for i in idx])
    summary, _, _ = ranking_summary(np.array([y] * len(S)), S, rounds, fam, reps=REPS, stratum_key=scen)
    out = {'rows': int(len(idx)), 'positives': int(y.sum()), 'families': int(len(set(fam))),
           'within_round_auc': summary['within_round_auc'], 'within_round_ci95': summary['within_round_ci95'],
           'within_round_by_seed': summary['within_round_by_seed'],
           'positive_coverage': summary['positive_coverage_by_seed'],
           'pooled_auc': summary['pooled_auc'], 'pooled_ci95': summary['pooled_ci95']}
    if test_fold is not None:
        eps = [rows[i]['episode'] for i in idx]
        vals = [within_round(y, s, rounds, stratum_key=np.array([f'{test_fold[seed][e]}|{c}' for e, c in zip(eps, scen)]))[0]
                for seed, s in zip(sorted(per_seed), S)]
        out['fold_stratified_auc'] = float(np.mean(vals))
    lengths = np.array([rows[i]['n_tokens'] for i in idx], dtype=float)
    out['added_value_over_turn_length'] = added_value(y, S.mean(axis=0), rounds, lengths, fam)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--peek', type=int, default=0, help='only print top tokens for N rows per group; no run folder')
    args = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(SNAP / 'tokenizer.json'))
    config = json.loads((SNAP / 'config.json').read_text())
    eps = float(config['rms_norm_eps'])
    assert not config['tie_word_embeddings']
    index_map = json.loads((SNAP / 'model.safetensors.index.json').read_text())['weight_map']
    assert index_map['model.norm.weight'] == index_map['lm_head.weight'] == SHARD

    rows = [json.loads(s) for s in (DATA / 'rows.jsonl').read_text().splitlines()]
    fold_rows = [json.loads(s) for s in (FOLDS / 'rows.jsonl').read_text().splitlines()]
    assert len(rows) == len(fold_rows) and all(a['index'] == i and a['request_sha256'] == b['request_sha256']
                                               for i, (a, b) in enumerate(zip(rows, fold_rows)))
    eligible = [i for i, r in enumerate(rows) if r['eligible']]
    if args.peek:
        rng = np.random.default_rng(0)
        groups = {'leak-step (recruiting, label 1, steps_until_action==1)':
                  [i for i in eligible if rows[i]['label'] == 1 and rows[i]['steps_until_action'] == 1],
                  'held (recruiting, label 0)': [i for i in eligible if rows[i]['condition'] == 'recruiting' and rows[i]['label'] == 0],
                  'control': [i for i in eligible if rows[i]['condition'] == 'control']}
        eligible = [int(i) for g in groups.values() for i in rng.choice(g, args.peek, replace=False)]

    features = np.load(DATA / 'features.npy', mmap_mode='r')
    assert features.shape[1:] == (64, 5120)
    w = load_bf16(SNAP / SHARD, ['model.norm.weight', 'lm_head.weight'])
    head_t = np.ascontiguousarray(w['lm_head.weight'].T); norm_w = w['model.norm.weight']; del w
    ref_ids, ref_skip = token_ids(tok, REFUSAL_STRINGS)
    tool_ids, tool_skip = token_ids(tok, TOOL_STRINGS)
    feature_ids = sorted(set(ref_ids.values()) | set(tool_ids.values()))
    sub = [rows[i] for i in eligible]
    first, kinds = first_reply_tokens(sub, tok)
    extra = np.array([-1 if t is None else t for t in first])
    L = lens(features, eligible, norm_w, head_t, eps, feature_ids, extra)
    col = {t: j for j, t in enumerate(feature_ids)}
    pc = np.exp(L['cand_logp'].astype(np.float64))
    p_ref = pc[:, [col[t] for t in sorted(set(ref_ids.values()))]].sum(axis=1)
    p_tool = pc[:, [col[t] for t in sorted(set(tool_ids.values()))]].sum(axis=1)
    feats = {'p_refusal': p_ref, 'p_tool': p_tool, 'entropy': L['entropy'].astype(float), 'p_max': L['p_max'].astype(float)}

    if args.peek:
        print('refusal ids', ref_ids, 'skipped', ref_skip, 'tool ids', tool_ids)
        for j, i in enumerate(eligible):
            r = rows[i]
            print(f"[{r['condition']} label={r['label']} sua={r['steps_until_action']} rd={r['round']} {r['scenario']}] "
                  f"reply={tok.id_to_token(first[j]) if first[j] is not None else kinds[j]!r} "
                  f"p_ref={p_ref[j]:.3f} p_tool={p_tool[j]:.3f} H={feats['entropy'][j]:.2f}\n   top10: "
                  + show(tok, L['top_ids'][j], L['top_p'][j], 10))
        return

    from collusion.runs import start_run
    run = start_run('e05-logit-lens', experiment='E05', model=f'{MODEL}@{REVISION}',
                    parents=[DATA.name, FOLDS.name, NEAR_TERM.parent.name],
                    settings={'layer': LAYER, 'activation': 'decoder block 63 output, last prompt token, pre final norm',
                              'readout': 'RMSNorm(eps=%g) -> lm_head -> softmax, float32' % eps,
                              'refusal_tokens': ref_ids, 'refusal_skipped_multi_token': ref_skip, 'tool_tokens': tool_ids,
                              'signs': SIGN, 'lr': 'StandardScaler + LogisticRegression(C=1) on log p_refusal, log p_tool, '
                              'entropy, log p_max; fit on fold train+calibration eligible rows, score test rows',
                              'metric': 'within_round(stratum_key=scenario), recruiting rows; ranking_summary family bootstrap',
                              'reps': REPS, 'cpu_threads': 2, 'gpu': False, 'api_calls': 0})
    out = run.dir
    n_all = len(rows)

    # Labels per variant, indexed by global row index (None = not scored).
    lab = {'eventual': [None] * n_all, 'A_hazard': [None] * n_all}
    for i in eligible:
        lab['eventual'][i] = int(rows[i]['label'])
    near = {}
    for s in NEAR_TERM.read_text().splitlines():
        r = json.loads(s)
        if r['label_variant'] == 'A_hazard':
            near[r['row_id']] = r
    for i in eligible:
        r = rows[i]
        if r['condition'] != 'recruiting':
            lab['A_hazard'][i] = int(r['label']); continue
        n = near[f"{r['episode']}::request_idx={r['request_idx']}"]
        assert n['request_sha256'] == r['request_sha256']
        if n['included']:
            lab['A_hazard'][i] = int(n['label'])

    # Sanity: argmax vs the actual reply's first token.
    argmax = L['top_ids'][:, 0]
    known = np.array([t is not None for t in first])
    match = known & (argmax == extra)
    kinds = np.array(kinds)
    sanity = {'rows': int(len(eligible)), 'known_first_token': int(known.sum()), 'reply_kinds': {k: int((kinds == k).sum()) for k in set(kinds)},
              'argmax_match_rate': float(match[known].mean()),
              'by_kind': {k: {'rows': int(((kinds == k) & known).sum()), 'match_rate': float(match[(kinds == k) & known].mean())}
                          for k in ('text', 'tool_call') if ((kinds == k) & known).any()},
              'by_condition': {c: float(match[known & (np.array([r['condition'] for r in sub]) == c)].mean())
                               for c in sorted({r['condition'] for r in sub})},
              'actual_token_in_top5_rate': float(np.mean([extra[j] in L['top_ids'][j, :5] for j in np.flatnonzero(known)])),
              'mean_prob_of_actual_first_token': float(np.exp(L['extra_logp'][known]).mean())}
    print('sanity', json.dumps(sanity, indent=1))

    # Scores, indexed by global row.
    full = {k: np.full(n_all, np.nan) for k in SCALARS}
    for k in SCALARS:
        full[k][eligible] = feats[k]
    X = np.c_[np.log(np.maximum(full['p_refusal'], 1e-30)), np.log(np.maximum(full['p_tool'], 1e-30)),
              full['entropy'], np.log(np.maximum(full['p_max'], 1e-30))]
    folds = json.loads((FOLDS / 'folds.json').read_text())
    test_fold = {}
    for f in folds:
        for e in f['test_episodes']:
            test_fold.setdefault(f['seed'], {})[e] = f['fold']
    metrics = {'sanity': sanity, 'variants': {}}
    lr_scores = {}
    for variant, labels in lab.items():
        y_all = np.array([-1 if v is None else v for v in labels])
        train_ok = (y_all >= 0) & np.isfinite(X).all(axis=1)
        lr = cross_fit(X, y_all, folds, train_ok)
        lr_scores[variant] = lr
        res = {}
        for k in SCALARS:
            res[k] = rank(eligible, rows, {0: SIGN[k] * full[k]}, labels)
        res['logistic_4'] = rank(eligible, rows, lr, labels, test_fold=test_fold)
        metrics['variants'][variant] = res
        for k, v in res.items():
            print(variant, k, round(v['within_round_auc'], 4), v['within_round_ci95'], flush=True)
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2))

    # scores.csv
    with (out / 'scores.csv').open('w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['step_id', 'condition', 'scenario', 'family', 'round', 'label_eventual', 'label_A_hazard', *SCALARS,
                     'argmax_token', 'top5', 'reply_first_token', 'argmax_match', 'lr_eventual', 'lr_A_hazard'])
        for j, i in enumerate(eligible):
            r = rows[i]
            wr.writerow([f"{r['episode']}::request_idx={r['request_idx']}", r['condition'], r['scenario'], r['family'], r['round'],
                         lab['eventual'][i], '' if lab['A_hazard'][i] is None else lab['A_hazard'][i],
                         *[f'{full[k][i]:.6g}' for k in SCALARS], tok.id_to_token(int(argmax[j])),
                         ' | '.join(f'{tok.id_to_token(int(t))}:{q:.4f}' for t, q in zip(L['top_ids'][j, :5], L['top_p'][j, :5])),
                         '' if first[j] is None else tok.id_to_token(first[j]), int(match[j]) if known[j] else '',
                         *[f"{np.nanmean([lr_scores[v][s][i] for s in lr_scores[v]]):.6g}" for v in ('eventual', 'A_hazard')]])

    # Examples for the report.
    rng = np.random.default_rng(1)
    pos = {i: j for j, i in enumerate(eligible)}
    pick = {'one step before the leaking call (recruiting, label 1, steps_until_action 1)': [i for i in eligible if rows[i]['label'] == 1 and rows[i]['steps_until_action'] == 1],
            'held (recruiting, eventual label 0)': [i for i in eligible if rows[i]['condition'] == 'recruiting' and rows[i]['label'] == 0],
            'control': [i for i in eligible if rows[i]['condition'] == 'control']}
    examples = []
    for g, cand in pick.items():
        examples.append(f'\n**{g}**\n')
        for i in rng.choice(cand, 4, replace=False):
            j = pos[int(i)]; r = rows[int(i)]
            examples.append(f"- {r['scenario']} rd {r['round']}: reply starts {tok.id_to_token(first[j]) if first[j] is not None else kinds[j]!r}; "
                            f"p_refusal {p_ref[j]:.3f}, p_tool {p_tool[j]:.3f}, H {feats['entropy'][j]:.2f}. Top-5: "
                            + show(tok, L['top_ids'][j], L['top_p'][j]).replace('|', '/'))
    group_means = {}
    for g, cand in pick.items():
        js = [pos[i] for i in cand]
        group_means[g] = {k: float(np.mean(feats[k][js])) for k in SCALARS}
    metrics['group_means'] = group_means
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    (out / 'examples.md').write_text('\n'.join(examples) + '\n')
    run.result(argmax_match_rate=sanity['argmax_match_rate'],
               **{f'{v}_{k}_within': round(m['within_round_auc'], 4) for v, d in metrics['variants'].items() for k, m in d.items()})
    print('wrote', out)


if __name__ == '__main__':
    main()
