# src/utils/s3_loader.py
import io
import json
import time
import boto3
import numpy as np
import os
import globals_cache as gc
from utils.cache_ttl_utils import is_cache_expired
from utils.logger import log  # optional structured logging

BUCKET = "legal-system-embeddings-v1"

def get_s3_client():
    """Get S3 client with proper credential handling"""
    # Check if running in local development (env variables present)
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        # Local development - use env variables (with session token if present)
        client_kwargs = {
            'service_name': 's3',
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'region_name': os.getenv('AWS_REGION', 'us-east-1')
        }
        # Add session token if present (for temporary credentials)
        if os.getenv('AWS_SESSION_TOKEN'):
            client_kwargs['aws_session_token'] = os.getenv('AWS_SESSION_TOKEN')
        
        return boto3.client(**client_kwargs)
    else:
        # Deployed environment - use IAM role
        return boto3.client('s3', region_name='us-east-1')

s3 = get_s3_client()


def create_bucket_if_not_exists(bucket_name):
    """Create S3 bucket if it doesn't exist"""
    try:
        s3.head_bucket(Bucket=bucket_name)
        log("bucket_exists", bucket=bucket_name)
    except Exception as e:
        if "404" in str(e) or "NoSuchBucket" in str(e):
            try:
                log("creating_bucket", bucket=bucket_name)
                s3.create_bucket(Bucket=bucket_name)
                log("bucket_created", bucket=bucket_name)
            except Exception as create_error:
                if "BucketAlreadyExists" in str(create_error):
                    log("bucket_exists_globally", bucket=bucket_name)
                else:
                    raise
        else:
            log("bucket_check_error", bucket=bucket_name, error=str(e))
            raise


def load_index(index_name, cid=None):
    if gc.loaded_index_name == index_name and not is_cache_expired():
        log("index_cache_hit", index=index_name, cid=cid)
        return gc.vectors, gc.metadata

    # Fetch vectors from S3 into memory
    vec_obj = io.BytesIO()
    s3.download_fileobj(BUCKET, f"{index_name}/vectors.npy", vec_obj)
    vec_obj.seek(0)
    gc.vectors = np.load(vec_obj)

    # Fetch metadata
    meta_obj = io.BytesIO()
    s3.download_fileobj(BUCKET, f"{index_name}/metadata.jsonl", meta_obj)
    meta_obj.seek(0)
    gc.metadata = [json.loads(line) for line in meta_obj.getvalue().decode("utf-8").splitlines()]

    gc.loaded_index_name = index_name
    gc.loaded_timestamp = time.time()

    log("index_loaded", index=index_name, vectors=len(gc.vectors), cid=cid)
    return gc.vectors, gc.metadata


def upload_index(index_name, vectors, metadata, cid=None):
    """
    Upload vectors (NumPy array) and metadata (list of dicts) to S3.
    Memory-only, no /tmp file usage.
    """
    # Ensure bucket exists
    create_bucket_if_not_exists(BUCKET)
    
    # --- Upload vectors.npy ---
    vec_key = f"{index_name}/vectors.npy"
    vec_buffer = io.BytesIO()
    np.save(vec_buffer, vectors)
    vec_buffer.seek(0)

    log("s3_upload_start", file=vec_key, cid=cid)
    s3.upload_fileobj(vec_buffer, BUCKET, vec_key)
    log("s3_upload_end", file=vec_key, cid=cid)

    # --- Upload metadata.jsonl ---
    meta_key = f"{index_name}/metadata.jsonl"
    meta_buffer = io.BytesIO()
    meta_content = "\n".join(json.dumps(item, ensure_ascii=False) for item in metadata)
    meta_buffer.write(meta_content.encode("utf-8"))
    meta_buffer.seek(0)

    log("s3_upload_start", file=meta_key, cid=cid)
    s3.upload_fileobj(meta_buffer, BUCKET, meta_key)
    log("s3_upload_end", file=meta_key, cid=cid)

    log("index_uploaded", index=index_name, vectors=vectors.shape[0], cid=cid)

    return
