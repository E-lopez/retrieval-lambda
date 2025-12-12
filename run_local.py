#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging for local development
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from lambda_function import lambda_handler
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    class LocalHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            event = {
                'httpMethod': 'GET',
                'path': self.path,
                'body': None,
                'headers': dict(self.headers)
            }
            response = lambda_handler(event, {})
            self.send_response(response['statusCode'])
            for key, value in response['headers'].items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response['body'].encode())
            
        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            body_bytes = self.rfile.read(content_length)
            
            # Handle binary data properly - don't decode to string
            # Pass raw bytes to Lambda handler
            event = {
                'httpMethod': 'POST',
                'path': self.path,
                'body': body_bytes,  # Pass as bytes
                'headers': dict(self.headers)
            }
            response = lambda_handler(event, {})
            self.send_response(response['statusCode'])
            for key, value in response['headers'].items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response['body'].encode())
    
    print("🚀 Preprocess Handler running locally at http://localhost:8080")
    print("📋 Available endpoints:")
    print("  GET  /health")
    print("  POST /preprocess-facts")
    print("\n💡 Test with:")
    print("  curl http://localhost:8080/health")
    print("\n⏹️  Press Ctrl+C to stop")
    
    server = HTTPServer(('0.0.0.0', 8080), LocalHandler)
    server.serve_forever()