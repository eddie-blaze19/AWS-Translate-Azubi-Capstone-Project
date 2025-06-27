#!/usr/bin/env python3
"""
AWS Translation Client
A Python client for interacting with the AWS Translation Infrastructure
"""

import boto3
import json
import os
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AWSTranslationClient:
    """
    Client for AWS Translation Service using S3 and AWS Translate
    """
    
    def __init__(self, request_bucket: str, response_bucket: str, region: str = 'us-east-1'):
        """
        Initialize the translation client
        
        Args:
            request_bucket: S3 bucket name for translation requests
            response_bucket: S3 bucket name for translation responses
            region: AWS region
        """
        self.request_bucket = request_bucket
        self.response_bucket = response_bucket
        self.region = region
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=region)
        self.translate_client = boto3.client('translate', region_name=region)
        
        logger.info(f"Initialized AWS Translation Client for region: {region}")
    
    def create_translation_request(self, 
                                 texts: List[str], 
                                 source_language: str, 
                                 target_language: str,
                                 request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a translation request object
        
        Args:
            texts: List of texts to translate
            source_language: Source language code (e.g., 'en', 'es', 'fr')
            target_language: Target language code
            request_id: Optional request identifier
            
        Returns:
            Translation request dictionary
        """
        if not request_id:
            request_id = f"req_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert simple strings to structured format
        structured_texts = []
        for i, text in enumerate(texts):
            structured_texts.append({
                'id': i,
                'text': text
            })
        
        request_data = {
            'request_id': request_id,
            'source_language': source_language,
            'target_language': target_language,
            'texts': structured_texts,
            'timestamp': datetime.utcnow().isoformat(),
            'client_info': {
                'version': '1.0',
                'client_type': 'python_client'
            }
        }
        
        return request_data
    
    def submit_translation_request(self, request_data: Dict[str, Any]) -> str:
        """
        Submit translation request to S3 bucket
        
        Args:
            request_data: Translation request data
            
        Returns:
            S3 key of uploaded request file
        """
        try:
            # Generate unique filename
            filename = f"translation_request_{request_data['request_id']}.json"
            
            # Convert to JSON
            json_content = json.dumps(request_data, indent=2, ensure_ascii=False)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.request_bucket,
                Key=filename,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                ServerSideEncryption='AES256',
                Metadata={
                    'request-id': request_data['request_id'],
                    'source-language': request_data['source_language'],
                    'target-language': request_data['target_language'],
                    'text-count': str(len(request_data['texts']))
                }
            )
            
            logger.info(f"Translation request submitted: s3://{self.request_bucket}/{filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error submitting translation request: {str(e)}")
            raise e
    
    def wait_for_translation_result(self, request_id: str, timeout: int = 300, poll_interval: int = 5) -> Optional[Dict[str, Any]]:
        """
        Wait for translation result to be available
        
        Args:
            request_id: Request identifier
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Translation result or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # List objects in response bucket with request_id prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=self.response_bucket,
                    Prefix=f"translation_request_{request_id}_translated"
                )
                
                if 'Contents' in response and len(response['Contents']) > 0:
                    # Get the most recent result
                    latest_object = max(response['Contents'], key=lambda x: x['LastModified'])
                    result_key = latest_object['Key']
                    
                    # Download and parse result
                    result_data = self.get_translation_result(result_key)
                    logger.info(f"Translation result retrieved: s3://{self.response_bucket}/{result_key}")
                    return result_data
                
                logger.info(f"Waiting for translation result... ({int(time.time() - start_time)}s)")
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error checking for translation result: {str(e)}")
                time.sleep(poll_interval)
        
        logger.warning(f"Translation result timeout after {timeout} seconds")
        return None
    
    def get_translation_result(self, result_key: str) -> Dict[str, Any]:
        """
        Get translation result from S3
        
        Args:
            result_key: S3 key of result file
            
        Returns:
            Translation result data
        """
        try:
            response = self.s3_client.get_object(Bucket=self.response_bucket, Key=result_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error retrieving translation result: {str(e)}")
            raise e
    
    def translate_texts_sync(self, 
                           texts: List[str], 
                           source_language: str, 
                           target_language: str,
                           timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        Synchronous translation method
        
        Args:
            texts: List of texts to translate
            source_language: Source language code
            target_language: Target language code
            timeout: Maximum wait time for result
            
        Returns:
            Translation result or None if timeout
        """
        # Create request
        request_data = self.create_translation_request(texts, source_language, target_language)
        
        # Submit request
        self.submit_translation_request(request_data)
        
        # Wait for result
        return self.wait_for_translation_result(request_data['request_id'], timeout)
    
    def translate_direct(self, 
                        texts: List[str], 
                        source_language: str, 
                        target_language: str) -> Dict[str, Any]:
        """
        Direct translation using AWS Translate (bypassing S3/Lambda)
        
        Args:
            texts: List of texts to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Translation results
        """
        translated_texts = []
        total_characters = 0
        
        try:
            for i, text in enumerate(texts):
                if not text.strip():
                    translated_texts.append({
                        'id': i,
                        'original_text': text,
                        'translated_text': '',
                        'character_count': 0
                    })
                    continue
                
                # Translate using AWS Translate
                response = self.translate_client.translate_text(
                    Text=text,
                    SourceLanguageCode=source_language,
                    TargetLanguageCode=target_language
                )
                
                character_count = len(text)
                total_characters += character_count
                
                translated_texts.append({
                    'id': i,
                    'original_text': text,
                    'translated_text': response['TranslatedText'],
                    'character_count': character_count
                })
            
            return {
                'translation_metadata': {
                    'source_language': source_language,
                    'target_language': target_language,
                    'total_texts': len(texts),
                    'total_characters': total_characters,
                    'timestamp': datetime.utcnow().isoformat(),
                    'processing_status': 'completed',
                    'method': 'direct'
                },
                'translations': translated_texts
            }
            
        except Exception as e:
            logger.error(f"Direct translation error: {str(e)}")
            raise e
    
    def list_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages from AWS Translate
        
        Returns:
            List of supported languages
        """
        try:
            response = self.translate_client.list_languages()
            return response['Languages']
        except Exception as e:
            logger.error(f"Error getting supported languages: {str(e)}")
            raise e

def main():
    """
    Command-line interface for the translation client
    """
    parser = argparse.ArgumentParser(description='AWS Translation Client')
    parser.add_argument('--request-bucket', required=True, help='S3 bucket for requests')
    parser.add_argument('--response-bucket', required=True, help='S3 bucket for responses')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--source-lang', required=True, help='Source language code')
    parser.add_argument('--target-lang', required=True, help='Target language code')
    parser.add_argument('--text', action='append', required=True, help='Text to translate (can be repeated)')
    parser.add_argument('--method', choices=['sync', 'direct'], default='sync', help='Translation method')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout for sync method')
    
    args = parser.parse_args()
    
    # Initialize client
    client = AWSTranslationClient(args.request_bucket, args.response_bucket, args.region)
    
    try:
        if args.method == 'sync':
            logger.info("Using synchronous translation method (S3 + Lambda)")
            result = client.translate_texts_sync(
                args.text, 
                args.source_lang, 
                args.target_lang, 
                args.timeout
            )
        else:
            logger.info("Using direct translation method (AWS Translate)")
            result = client.translate_direct(
                args.text, 
                args.source_lang, 
                args.target_lang
            )
        
        if result:
            print("\n" + "="*80)
            print("TRANSLATION RESULTS")
            print("="*80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("Translation failed or timed out")
            
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()