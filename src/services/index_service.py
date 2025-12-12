from venv import logger
from collections import defaultdict
import globals_cache as gc
from services.search_service import search
from models.corpus_domain_keyword import CORPUS_DOMAIN_KEYWORDS
from utils.s3_utils import upload_index
from utils.logger import log, get_correlation_id
from utils.LLM_utils import embed
from utils.file_utils import get_parsed_file


def create_index():
    text = get_parsed_file()
    print(f"Creating index with {len(text)} {type(text)} chapters")
    content = [
        f"{a['article_title']}: {a['content']}"
        for a in text
    ]

    print(f"Content {content[25]}")
    vectors = embed(content)  # shape: (N, 384)

    # 3. Collect metadata IDs
    indexed_data = [
        {
            "id": a["article_number"],
            "title": a["article_title"],
            "text": f"{a['article_title']}: {a['content']}",
        }
        for a in text
    ]

    upload_index('civil', vectors, indexed_data)
    return {'message': 'Index created successfully'}


def parse_query_obj(query_obj, mapping_table=CORPUS_DOMAIN_KEYWORDS):
    parsed_queries = defaultdict(lambda: {'facts': set(), 'queries': set()})
    
    for query_list in query_obj:
        fact_id = query_list.get('fact_id', None)
        for query in query_list.get('data', []):
            domains = mapping_table[query.get('domain', 'default')]
            if isinstance(domains, list):
                for domain in domains:
                    parsed_queries[domain]['facts'].add(fact_id)
                    parsed_queries[domain]['queries'].update(query.get('queries', []))
            domain = query.get('domain', '')

    parsed_queries = {domain: {'facts': list(data['facts']), 'queries': list(data['queries'])} 
            for domain, data in parsed_queries.items()}
    
    return parsed_queries


def run_multi_query(query_obj, top_k=5):
    cid = get_correlation_id(None)
    
    if gc.COLD_START:
        log("cold_start", cid=cid)
        gc.COLD_START = False
    else:
        log("warm_start", cid=cid)

    parsed_queries = parse_query_obj(query_obj)
    logger.info(f"Test aggregation: {parsed_queries}")

    for key, value in parsed_queries.items():
        index_name = key
        query_texts = value['queries']
        search_result = multi_search(query_texts, index_name=index_name, top_k=top_k, cid=cid)
        parsed_queries[index_name]['results'] = search_result

    return parsed_queries


def multi_search(query_texts, index_name, top_k=5, force_reload=False, cid=None):
    
    if force_reload:
        gc.loaded_timestamp = None
        log("force_reload_triggered", index=index_name, cid=cid)

    all_results = []
    seen_ids = set()
    
    for query_text in query_texts:
        logger.info(f"Running query: {query_text} on index: {index_name}")
        vector = embed([query_text])[0]
        results = search(vector, index_name, top_k=top_k, cid=cid)
        
        for result in results:
            article_id = result['metadata']['id']
            if article_id not in seen_ids:
                seen_ids.add(article_id)
                all_results.append(result)
    
    # Sort by score descending
    all_results.sort(key=lambda x: x['score'], reverse=True)
    
    log("multi_query_end", cid=cid, queries=len(query_texts), unique_results=len(all_results))
    
    return all_results