import json
import re
from typing import Dict, Any

def parse_event(event: Dict[str, Any]):
    http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    path = event.get('path') or event.get('rawPath', '/')
    body = event.get('body')
    path_parameters = event.get('pathParameters') or {}
    headers = event.get('headers') or {}
    origin = headers.get('origin') or headers.get('Origin')
    
    # Handle base64 encoded body (common with binary/multipart data)
    is_base64_encoded = event.get('isBase64Encoded', False)
    if is_base64_encoded and body:
        import base64
        try:
            body = base64.b64decode(body)
        except Exception:
            pass
    
    return http_method, path, body, path_parameters, headers, origin

def parse_multipart_form_data(body, content_type):
    if 'boundary=' not in content_type:
        return {}, []
    
    boundary = content_type.split('boundary=')[1].strip()
    
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    parts = body.split(f'--{boundary}'.encode())
    
    form_data = {}
    files = []
    
    for part in parts[1:-1]:
        if not part.strip():
            continue
            
        header_end = part.find(b'\r\n\r\n')
        if header_end == -1:
            continue
            
        headers = part[:header_end].decode('utf-8', errors='ignore')
        content = part[header_end + 4:].rstrip(b'\r\n')
        
        if 'Content-Disposition: form-data' in headers:
            name_match = re.search(r'name="([^"]+)"', headers)
            if name_match:
                field_name = name_match.group(1)
                
                if 'filename=' in headers:
                    filename_match = re.search(r'filename="([^"]+)"', headers)
                    filename = filename_match.group(1) if filename_match else 'unknown'
                    files.append({
                        'filename': filename,
                        'content': content,
                        'field_name': field_name
                    })
                else:
                    form_data[field_name] = content.decode('utf-8', errors='ignore')
    
    return form_data, files

def create_response(status_code: int, body: Dict[str, Any], origin: str) -> Dict[str, Any]:
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, Origin, X-Requested-With'
    }

    if origin and origin in ['http://localhost:3000', 'http://localhost:5173', 'https://kredilatam.com']:
        headers['Access-Control-Allow-Origin'] = origin
        headers['Access-Control-Allow-Credentials'] = 'true'
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }