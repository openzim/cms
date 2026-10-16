#!/bin/bash

S3_URL="http://minio:9000"
BUCKETS=("zimfarm-zimchecks" "zimfarm-artifacts" "zimfarm-zims" "zimfarm-logs")

export AWS_ACCESS_KEY_ID="minio_key"
export AWS_SECRET_ACCESS_KEY="minio_secret"
export AWS_DEFAULT_REGION="us-east-1"

s3api() {
    aws --endpoint-url "$S3_URL" s3api "$@"
}

# Wait for S3 server
echo "Waiting for S3 server to be ready..."
for i in $(seq 1 30); do
    s3api list-buckets >/dev/null && echo "S3 server is ready!" && break
    sleep 2
    [ "$i" -eq 30 ] && { echo "ERROR: S3 server timeout"; exit 1; }
done

# Setup buckets
for bucket in "${BUCKETS[@]}"; do
    echo "Setting up bucket: $bucket"
    # Create bucket if it doesn't exist
    s3api head-bucket --bucket "$bucket" 2>/dev/null || s3api create-bucket --bucket "$bucket"
    # Set bucket to public (anonymous read/write, like `mc anonymous set public`)
    s3api put-bucket-policy --bucket "$bucket" --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Effect\": \"Allow\",
                \"Principal\": {\"AWS\": [\"*\"]},
                \"Action\": [\"s3:GetBucketLocation\", \"s3:ListBucket\", \"s3:ListBucketMultipartUploads\"],
                \"Resource\": [\"arn:aws:s3:::$bucket\"]
            },
            {
                \"Effect\": \"Allow\",
                \"Principal\": {\"AWS\": [\"*\"]},
                \"Action\": [\"s3:GetObject\", \"s3:PutObject\", \"s3:DeleteObject\", \"s3:AbortMultipartUpload\", \"s3:ListMultipartUploadParts\"],
                \"Resource\": [\"arn:aws:s3:::$bucket/*\"]
            }
        ]
    }"
done
echo "S3 setup complete"
