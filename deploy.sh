#!/bin/bash

set -e

# Configuration
ENVIRONMENT=${1:-dev}
S3_BUCKET=${2:-preprocess-deployment-bucket}
STACK_NAME="preprocess-lambda-${ENVIRONMENT}"
AWS_REGION="us-east-1"

# Check for clean command
if [ "$1" = "clean" ]; then
    echo "🗑️  Deleting CloudFormation stack: $STACK_NAME"
    aws cloudformation delete-stack --stack-name ${STACK_NAME} --region ${AWS_REGION}
    echo "✅ Stack deletion initiated. Check AWS Console for progress."
    exit 0
fi

# Verify AWS credentials are configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' or set AWS_PROFILE"
    exit 1
fi

echo "Deploying Preprocess Lambda for environment: $ENVIRONMENT"
echo "S3 Bucket: $S3_BUCKET"
echo "AWS Identity: $(aws sts get-caller-identity --query 'Arn' --output text)"
echo "Stack Name: $STACK_NAME"
echo "Region: $AWS_REGION"

# Create S3 bucket for files if it doesn't exist
echo "📦 Checking S3 bucket for files..."
if ! aws s3 ls s3://preprocess-files-bucket 2>/dev/null; then
    echo "Creating S3 bucket: preprocess-files-bucket"
    aws s3 mb s3://preprocess-files-bucket --region us-east-1
else
    echo "S3 bucket already exists"
fi

# Create deployment package
echo "Creating deployment package..."
rm -rf package/
mkdir -p package/

# Install dependencies with proper wheels for Lambda
echo "Installing dependencies..."

# Install only essential dependencies (everything else comes from layers)
echo "Installing minimal dependencies..."
python3 -m pip install \
--platform manylinux2014_aarch64 \
--target=package \
--implementation cp \
--python-version 3.11 \
--only-binary=:all: \
--upgrade \
requests dateparser

# Copy source code (exclude conflicting packages)
echo "Copying source code..."
cp -r src/ package/
cp lambda_function.py package/

# Remove any remaining heavy packages that might have been installed as dependencies
echo "Cleaning up heavy packages..."
rm -rf package/numpy* package/scipy* package/pandas* package/PIL* package/pillow*
rm -rf package/spacy* package/thinc* package/cymem* package/preshed*
rm -rf package/murmurhash* package/wasabi* package/srsly* package/catalogue*
rm -rf package/typer* package/click* package/blis*

echo "Function package optimized - heavy dependencies will come from layers"

# Create ZIP file
echo "Creating ZIP file..."
cd package
zip -r ../function.zip . -x "*.pyc" "*__pycache__*"
cd ..

# Build and upload layers first
echo "Building and uploading layers..."
./deploy-layers.sh ${S3_BUCKET}

# Upload function to S3
echo "Uploading function to S3..."
aws s3 cp function.zip s3://${S3_BUCKET}/preprocess-lambda/function.zip

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file cloudformation-template.yml \
    --stack-name ${STACK_NAME} \
    --parameter-overrides \
        Environment=${ENVIRONMENT} \
        S3Bucket=${S3_BUCKET} \
        S3Key=preprocess-lambda/function.zip \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}

# Get stack outputs
echo "Getting stack outputs..."
API_URL=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

FUNCTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`PreprocessLambdaFunctionArn`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

echo ""
echo "Deployment completed successfully!"
echo "Environment: $ENVIRONMENT"
echo "Function ARN: $FUNCTION_ARN"
echo ""
echo "API Url: ${API_URL}"
echo ""
echo "Clean up..."
rm -rf package/
rm function.zip