import json
import os


def get_parsed_file():
  # Read parsed_documents.json file
    json_file_path = os.path.join(os.path.dirname(__file__), '../../parsed_documents.json')
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        # Extract articles in all documents
        for document in doc.get('documents', []):
            articles = document.get('articles', [])
        
        return articles
        
    except FileNotFoundError:
        return {'error': 'parsed_documents.json file not found'}
    except Exception as e:
        return {'error': f'Failed to load documents: {str(e)}'}