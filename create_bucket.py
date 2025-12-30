
import boto3
from dubwizard_shared.config import shared_settings

s3 = boto3.client(
    "s3",
    region_name=shared_settings.AWS_REGION,
    aws_access_key_id=shared_settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=shared_settings.AWS_SECRET_ACCESS_KEY,
)

try:
    if shared_settings.AWS_REGION == "us-east-1":
        s3.create_bucket(Bucket=shared_settings.S3_BUCKET_NAME)
    else:
        s3.create_bucket(
            Bucket=shared_settings.S3_BUCKET_NAME,
            CreateBucketConfiguration={'LocationConstraint': shared_settings.AWS_REGION}
        )
    print(f"Bucket {shared_settings.S3_BUCKET_NAME} created successfully.")
except Exception as e:
    print(f"Error creating bucket: {e}")
