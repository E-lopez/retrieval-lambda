import numpy as np
from utils.s3_utils import load_index
from utils.logger import log

def search(vector, index_name, top_k=5, cid=None):
    vecs, meta = load_index(index_name, cid)

    # Cosine similarity
    norms = np.linalg.norm(vecs, axis=1) * np.linalg.norm(vector)
    sims = (vecs @ vector) / norms
    idx = np.argsort(-sims)[:top_k]

    results = [{"score": float(sims[i]), "metadata": meta[i]} for i in idx]
    log("search_completed", index=index_name, top_k=top_k, cid=cid)
    return results
