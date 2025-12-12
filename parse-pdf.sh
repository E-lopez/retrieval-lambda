#!/bin/bash

# PDF Parser Script for Local Development
# Uses same libraries as preprocess-lambda: PyMuPDF (fitz), pytesseract, PIL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDF_DIR="${1:-$HOME/Documents/legal/juris}"
OUTPUT_FILE="${2:-$SCRIPT_DIR/parsed_documents.json}"

# Expand the path
PDF_DIR=$(eval echo "$PDF_DIR")

echo "PDF Parser - Local Development Tool"
echo "PDF Directory: $PDF_DIR"
echo "Output File: $OUTPUT_FILE"
echo ""

# Check if PDF directory exists
if [ ! -d "$PDF_DIR" ]; then
    echo "Error: PDF directory '$PDF_DIR' does not exist"
    echo "Usage: $0 [pdf_directory] [output_file]"
    echo "Example: $0 ./pdfs parsed_docs.json"
    exit 1
fi

# Check and install dependencies
echo "Checking Python dependencies..."
python3 -c "import fitz, pytesseract" 2>/dev/null || {
    echo "Installing required packages..."
    pip3 install PyMuPDF pytesseract Pillow
}

# Create Python script for PDF parsing
cat > /tmp/parse_pdfs.py << 'EOF'
import os
import sys
import json
import re
import fitz  # PyMuPDF
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    print("Warning: PIL/pytesseract not available. OCR will be skipped.")
    OCR_AVAILABLE = False
import io as pil_io
from datetime import datetime

def ocr_image(img_bytes):
    """OCR image bytes using pytesseract"""
    if not OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(pil_io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img, lang='spa+eng')
        return text.strip()
    except Exception as e:
        print(f"OCR failed: {e}")
        return ""

def extract_all_pages_text(file_path):
    """Extract text from all PDF pages. Use OCR if needed."""
    try:
        doc = fitz.open(file_path)
        if len(doc) == 0:
            return ""

        all_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            if text is None:
                text = ""

            # If no text found, try OCR
            if len(text.strip()) < 10 and OCR_AVAILABLE:
                try:
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    
                    # Convert to grayscale for better OCR
                    img = Image.open(pil_io.BytesIO(img_bytes))
                    img = img.convert('L')  # Convert to grayscale
                    
                    # Convert back to bytes
                    gray_bytes = pil_io.BytesIO()
                    img.save(gray_bytes, format='PNG')
                    gray_bytes = gray_bytes.getvalue()
                    
                    ocr_text = ocr_image(gray_bytes)
                    text = ocr_text if ocr_text else ""
                except Exception as e:
                    print(f"OCR failed for {file_path} page {page_num}: {e}")
                    text = ""
            
            all_text.append(text)
        
        doc.close()
        return "\n\n".join(all_text)
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")
        return ""

def clean_pdf_text(t):
    """Clean extracted PDF text"""
    # Remove "CODIGO CIVIL COLOMBIANO" at the top of pages
    t = re.sub(r'CODIGO CIVIL COLOMBIANO', '', t, flags=re.I)
    # Remove page number patterns like "Página 618 de 618"
    t = re.sub(r'Página\s+\d+\s+de\s+\d+', '', t, flags=re.I)
    t = re.sub(r'Page \d+ of \d+', ' ', t, flags=re.I)
    t = re.sub(r'\b\d+\s*/\s*\d+\b', ' ', t)
    t = re.sub(r'(Exhibit|Appendix)\s+[A-Z0-9]+', ' ', t, flags=re.I)
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', t)
    t = t.replace("\n", " ")
    t = (t.replace("ﬁ", "fi").replace("ﬂ", "fl")
            .replace("'", "'").replace(""", '"').replace(""", '"'))
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def split_into_chapters_and_articles(text):
    """Split text into chapters and articles based on patterns"""
    # Pattern for CAPÍTULO/CAPITULO followed by roman numeral and title until ARTÍCULO
    chapter_pattern = r'CAP[ÍI]TULO\s+([IVXLCDM]+)\s*\.?\s*(.*?)(?=CAP[ÍI]TULO\s+[IVXLCDM]+|$)'
    # Pattern for ARTÍCULO/ARTICULO followed by integer and "o." or "."
    article_pattern = r'ART[ÍI]CULO\s+(\d+)(?:o\.|\.)'
    
    chapters = []
    
    # Find all chapters with their titles
    chapter_matches = re.finditer(chapter_pattern, text, flags=re.I | re.DOTALL)
    chapter_list = list(chapter_matches)
    
    if not chapter_list:
        # No chapters found, treat entire text as one chapter
        chapters.append({
            'chapter_number': None,
            'chapter_title': 'Sin Capítulo',
            'articles': split_articles(text, article_pattern)
        })
    else:
        # Process each chapter
        for i, match in enumerate(chapter_list):
            chapter_num = match.group(1)
            chapter_title_part = match.group(2).strip()
            
            # Chapter content is already captured in group 2
            chapter_content = match.group(2)
            
            # Extract clean chapter title (first line or sentence)
            title_lines = chapter_title_part.split('\n')
            clean_title = title_lines[0].strip() if title_lines else ''
            
            chapters.append({
                'chapter_number': chapter_num,
                'chapter_title': f'CAPÍTULO {chapter_num}. {clean_title}',
                'articles': split_articles(chapter_content, article_pattern)
            })
    
    return chapters

def split_articles(text, article_pattern):
    """Split chapter text into articles"""
    articles = []
    
    # Find all articles with their numbers
    article_matches = re.finditer(article_pattern, text, flags=re.I)
    article_list = list(article_matches)
    
    if not article_list:
        # No articles found
        if text.strip():
            articles.append({
                'article_number': None,
                'article_title': 'Sin Artículo',
                'content': text.strip()
            })
    else:
        # Process each article
        for i, match in enumerate(article_list):
            # Use sequential index instead of extracted number
            article_index = i + 1
            
            # Get full article text from ARTÍCULO pattern to next ARTÍCULO pattern
            start_pos = match.start()
            if i + 1 < len(article_list):
                end_pos = article_list[i + 1].start()
                full_article_text = text[start_pos:end_pos].strip()
            else:
                full_article_text = text[start_pos:].strip()
            
            if full_article_text:
                articles.append({
                    'article_number': article_index,
                    'article_title': f'ARTÍCULO {article_index}',
                    'content': full_article_text
                })
    
    return articles

def main():
    if len(sys.argv) != 3:
        print("Usage: python parse_pdfs.py <pdf_directory> <output_file>")
        sys.exit(1)
    
    pdf_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(pdf_dir):
        print(f"Error: Directory {pdf_dir} does not exist")
        sys.exit(1)
    
    # Find all PDF files
    pdf_files = []
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF files")
    
    # Parse each PDF
    parsed_documents = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"Processing {i}/{len(pdf_files)}: {os.path.basename(pdf_path)}")
        
        raw_text = extract_all_pages_text(pdf_path)
        cleaned_text = clean_pdf_text(raw_text) if raw_text else ""
        
        # Extract articles directly without chapter structure
        article_pattern = r'ART[ÍI]CULO\s+(\d+)(?:o\.|\.)'
        articles = split_articles(cleaned_text, article_pattern) if cleaned_text else []
        
        document = {
            "filename": os.path.basename(pdf_path),
            "filepath": pdf_path,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "text_length": len(cleaned_text),
            "articles": articles,
            "total_articles": len(articles),
            "processed_at": datetime.now().isoformat()
        }
        
        parsed_documents.append(document)
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_documents": len(parsed_documents),
            "processed_at": datetime.now().isoformat(),
            "documents": parsed_documents
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nParsing complete!")
    print(f"Processed {len(parsed_documents)} documents")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
EOF

# Run the Python script
echo "Starting PDF parsing..."
python3 /tmp/parse_pdfs.py "$PDF_DIR" "$OUTPUT_FILE"

# Clean up
rm /tmp/parse_pdfs.py

echo ""
echo "PDF parsing completed!"
echo "Output saved to: $OUTPUT_FILE"