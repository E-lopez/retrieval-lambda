#!/bin/bash

# Setup script for S3 deployment bucket
DEPLOYMENT_BUCKET=${1:-spacy-deployment-deployment-bucket}
AWS_REGION=${2:-us-east-1}

echo "Setting up deployment bucket: $DEPLOYMENT_BUCKET in region: $AWS_REGION"

# Create bucket with proper region
if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3 mb s3://$DEPLOYMENT_BUCKET
else
    aws s3 mb s3://$DEPLOYMENT_BUCKET --region $AWS_REGION
fi

# Set bucket policy for deployment access
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):root"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::$DEPLOYMENT_BUCKET/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket $DEPLOYMENT_BUCKET --policy file://bucket-policy.json

# Clean up
rm bucket-policy.json

echo "Deployment bucket setup complete: $DEPLOYMENT_BUCKET"
echo ""
echo "Next steps:"
echo "1. Run deployment:"
echo "   ./deploy.sh dev $DEPLOYMENT_BUCKET YOUR_DOPPLER_TOKEN"