import os
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

# Cloudflare R2 Configuration
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")  # https://<account-id>.r2.cloudflarestorage.com
R2_PRESIGNED_URL_EXPIRY = int(os.getenv("R2_PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour

class R2StorageService:
    """Manage file storage in Cloudflare R2 (S3-compatible)"""
    
    def __init__(self):
        # R2 uses S3-compatible API with custom endpoint
        self.s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name='auto',  # R2 uses 'auto' for region
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}  # R2 requires path-style
            )
        )
        self.bucket_name = R2_BUCKET_NAME
    
    def generate_r2_key(self, therapist_id: int, resource_id: int, filename: str) -> str:
        """
        Generate R2 object key
        Format: therapist_{id}/resources/{resource_id}/{filename}
        """
        # Sanitize filename
        safe_filename = filename.replace(" ", "_").replace("/", "_")
        return f"therapist_{therapist_id}/resources/{resource_id}/{safe_filename}"
    
    def generate_presigned_upload_url(
        self,
        r2_key: str,
        file_type: str,
        expiration: int = None
    ) -> str:
        """
        Generate presigned PUT URL for file upload to R2
        
        R2 doesn't support presigned POST - only PUT works!
        Frontend must use PUT with file as binary body
        
        Returns:
            str: Presigned PUT URL
        """
        if expiration is None:
            expiration = R2_PRESIGNED_URL_EXPIRY
        
        try:
            # Generate presigned PUT (R2 only supports this method)
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': r2_key,
                    'ContentType': file_type
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def generate_presigned_download_url(self, r2_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned GET URL for file download from R2
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': r2_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating download URL: {e}")
            raise
    
    def verify_file_exists(self, r2_key: str) -> Tuple[bool, int]:
        """
        Verify file exists in R2 and get its size
        
        Returns:
            Tuple of (exists: bool, size_bytes: int)
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=r2_key)
            return True, response['ContentLength']
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False, 0
            raise
    
    def download_file(self, r2_key: str, local_path: str):
        """
        Download file from R2 to local path (for processing)
        """
        try:
            self.s3_client.download_file(self.bucket_name, r2_key, local_path)
            logger.info(f"Downloaded {r2_key} to {local_path}")
        except ClientError as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    def delete_file(self, r2_key: str):
        """
        Delete file from R2
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=r2_key)
            logger.info(f"Deleted {r2_key}")
        except ClientError as e:
            logger.error(f"Error deleting file: {e}")
            raise

# Singleton instance
r2_storage = R2StorageService()