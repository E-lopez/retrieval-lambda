import logging
import json
import time
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log(event, **kwargs):
    message = {"event": event, "timestamp": time.time(), **kwargs}
    logger.info(json.dumps(message, ensure_ascii=False))

def get_correlation_id(event):
    if isinstance(event, dict) and "headers" in event:
        return event["headers"].get("x-correlation-id", str(uuid.uuid4()))
    return str(uuid.uuid4())
