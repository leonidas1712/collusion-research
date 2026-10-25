"""Causal within-episode trajectory features from memory-mapped replay activations."""
import numpy as np

LAYERS = (24, 32, 40)


def trajectory_links(rows):
    previous = np.full(len(rows), -1, dtype=int)
    anchor = np.full(len(rows), -1, dtype=int)
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(row['episode'], []).append(i)
    for indices in groups.values():
        indices.sort(key=lambda i: rows[i]['request_idx'])
        first = next((i for i in indices if rows[i].get('token_in_context')
                      and isinstance(rows[i].get('ordinal'), int)
                      and isinstance(rows[i].get('first_read'), int)
                      and rows[i]['ordinal'] > rows[i]['first_read']), None)
        for position, i in enumerate(indices):
            if position:
                previous[i] = indices[position-1]
                assert rows[previous[i]]['request_idx'] < rows[i]['request_idx']
            if first is not None and rows[first]['request_idx'] <= rows[i]['request_idx']:
                anchor[i] = first
    return previous, anchor


def feature_values(current, previous, anchor):
    delta = current - previous
    norms = np.linalg.norm(current) * np.linalg.norm(previous)
    cosine_change = 1 - float(np.dot(current, previous) / max(float(norms), 1e-12))
    scalars = np.array([np.linalg.norm(delta), np.linalg.norm(current-anchor), cosine_change], dtype=np.float32)
    return delta, scalars


def extract(rows, x, directory):
    previous, anchor = trajectory_links(rows)
    valid = (previous >= 0) & (anchor >= 0)
    delta = np.lib.format.open_memmap(directory/'delta.npy', mode='w+', dtype=np.float32,
                                    shape=(len(rows), len(LAYERS), x.shape[-1]))
    scalar = np.lib.format.open_memmap(directory/'scalar.npy', mode='w+', dtype=np.float32,
                                     shape=(len(rows), len(LAYERS), 3))
    delta[:] = np.nan; scalar[:] = np.nan
    for j, layer in enumerate(LAYERS):
        for i in np.flatnonzero(valid):
            current = np.asarray(x[i, layer], dtype=np.float32)
            prior = np.asarray(x[previous[i], layer], dtype=np.float32)
            first = np.asarray(x[anchor[i], layer], dtype=np.float32)
            delta[i,j], scalar[i,j] = feature_values(current, prior, first)
        delta.flush(); scalar.flush()
        print('FEATURE_LAYER',layer,flush=True)
    np.savez(directory/'trajectory_links.npz', previous=previous, anchor=anchor, valid=valid)
    return delta, scalar, valid
