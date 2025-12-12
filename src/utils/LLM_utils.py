import requests
import json
import os
import numpy as np

def embed(text: list[str]) -> any:
    """
    Use Hugging Face Inference API for embeddings
    Fallback to simple approach if API fails
    """
    # Try Hugging Face Inference API first
    hf_token = os.getenv('HF_TOKEN')
    print(f"HF_TOKEN present: {bool(hf_token)}")
    
    if hf_token:
        try:
            headers = {"Authorization": f"Bearer {hf_token}"}
            response = requests.post(
                "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2",
                headers=headers,
                json={"inputs": text}
            )
            print(f"HF API response status: {response.status_code}")
            if response.status_code != 200:
                print(f"HF API error: {response.text}")
            else:
                result = response.json()
                print(f"HF API success: {len(result)} embeddings of dimension {len(result[0]) if result else 0}")
                return np.array(result)
        except Exception as e:
            print(f"HF API exception: {e}")
    else:
        print("No HF_TOKEN found, using fallback")
    
    # Fallback: Return 384-dimensional random vectors (matches stored embeddings)
    print(f"Using fallback embeddings for {len(text)} texts")
    
    # Generate consistent 384-dimensional vectors based on text hash
    embeddings = []
    for doc in text:
        # Use hash of text to generate consistent vector
        np.random.seed(hash(doc) % (2**32))
        vec = np.random.normal(0, 1, 384)
        # Normalize to unit vector
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec)
    
    return np.array(embeddings)