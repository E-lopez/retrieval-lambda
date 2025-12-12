#!/bin/bash
set -e

# Configuration
S3_BUCKET=${1:-preprocess-deployment-bucket}

echo "🚀 Building and deploying Lambda layers to S3 bucket: $S3_BUCKET"

# Build OCR layer (includes PyMuPDF)
echo "Building OCR layer (includes PyMuPDF)..."
cd layers/ocr-layer
./build.sh

# Upload OCR layer to S3
echo "Uploading OCR layer to S3..."
aws s3 cp ocr-layer.zip s3://${S3_BUCKET}/layers/ocr-layer.zip

cd ../..

# Build spacy layer
echo "Building spaCy layer..."
cd layers/spacy-layer
./build.sh

# Upload spacy layer to S3
echo "Uploading spaCy layer to S3..."
aws s3 cp spacy-layer.zip s3://${S3_BUCKET}/layers/spacy-layer.zip

cd ../..

echo "✅ Layers uploaded to S3 successfully!"
echo "Layers will be deployed via CloudFormation template."
echo "S3 paths:"
echo "- s3://${S3_BUCKET}/layers/ocr-layer.zip"
echo "- s3://${S3_BUCKET}/layers/spacy-layer.zip"