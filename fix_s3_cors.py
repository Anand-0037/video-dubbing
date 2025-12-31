import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize S3 client with region
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
bucket = os.getenv("S3_BUCKET_NAME")

print(f"Checking CORS for bucket: {bucket}")

cors_configuration = {
    'CORSRules': [{
        'AllowedHeaders': ['*'],
        'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
        'AllowedOrigins': ['*'],
        'ExposeHeaders': ['ETag'],
        'MaxAgeSeconds': 3000
    }]
}

# Check if bucket exists, create if not
try:
    s3.head_bucket(Bucket=bucket)
    print(f"Bucket {bucket} already exists.")
except Exception:
    print(f"Bucket {bucket} does not exist, creating it...")
    try:
        if os.getenv("AWS_REGION") == 'us-east-1':
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={'LocationConstraint': os.getenv("AWS_REGION")}
            )
        print(f"Bucket {bucket} created successfully.")
    except Exception as create_err:
        print(f"Failed to create bucket: {create_err}")

try:
    current = s3.get_bucket_cors(Bucket=bucket)
    print("Current CORS:")
    print(json.dumps(current.get('CORSRules', []), indent=2))
except Exception as e:
    print(f"No CORS configuration found or error: {e}")

print(f"Setting permissive CORS for {bucket}...")
try:
    s3.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_configuration)
    print("CORS updated successfully!")
except Exception as e:
    print(f"Failed to update CORS: {e}")
