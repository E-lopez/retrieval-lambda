import json
import sys
import logging
from typing import Dict, Any

from utils.http_utils import create_response, parse_event

# Configure paths for Lambda environment
sys.path.insert(0, '/opt/python')  # Layer path first
sys.path.insert(0, 'src')  # Source path

# Configure logging globally
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        http_method, path, body, path_parameters, headers, origin = parse_event(event)

        if http_method == 'OPTIONS':
            return create_response(200, {}, origin)

        return handle_route(http_method, path, body, path_parameters, origin)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return create_response(500, {'error': 'Internal server error'}, origin)


def handle_route(http_method, path, body, path_parameters, origin):
    if path in ['/health', '/']:
        return create_response(200, {'status': 'healthy', 'service': 'retrieval-lambda'}, origin)
        
    if path == '/create-index' and http_method == 'GET':
        from services.index_service import create_index
        result = create_index()
        return create_response(200, result, origin)

    if path == '/query' and http_method == 'POST':
        try:
            request_data = json.loads(body) if body else {}
        except json.JSONDecodeError as e:
            return create_response(400, {'error': f'Invalid JSON: {str(e)}'}, origin)
            
        from services.index_service import run_multi_query
        query_obj = request_data.get('queries', [])
        #print(f"Query obj: {query_obj}")
        if isinstance(query_obj, str):
            query_obj = [query_obj]
        top_k = request_data.get('top_k', 5)
        result = run_multi_query(query_obj, top_k)
        return create_response(200, result, origin)
    
    return create_response(404, {'error': f'Endpoint not found: {http_method} {path}'}, origin)
