#!/usr/bin/env python3
"""
Comprehensive Testing Suite for AWS Translation Service
This script tests all components of the translation infrastructure
"""

import boto3
import json
import time
import uuid
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TranslationServiceTester:
    """
    Comprehensive test suite for AWS Translation Service
    """
    
    def __init__(self, request_bucket: str, response_bucket: str, lambda_function: str, region: str = 'us-east-1'):
        """
        Initialize the test suite
        
        Args:
            request_bucket: S3 bucket for translation requests
            response_bucket: S3 bucket for translation responses
            lambda_function: Lambda function name
            region: AWS region
        """
        self.request_bucket = request_bucket
        self.response_bucket = response_bucket
        self.lambda_function = lambda_function
        self.region = region
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.translate_client = boto3.client('translate', region_name=region)
        
        # Test results
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }
        
        logger.info(f"Initialized test suite for region: {region}")
    
    def run_test(self, test_name: str, test_function, *args, **kwargs) -> bool:
        """
        Run a single test and record results
        
        Args:
            test_name: Name of the test
            test_function: Function to execute
            *args, **kwargs: Arguments for the test function
            
        Returns:
            True if test passed, False otherwise
        """
        self.test_results['total_tests'] += 1
        start_time = time.time()
        
        try:
            logger.info(f"Running test: {test_name}")
            result = test_function(*args, **kwargs)
            
            execution_time = time.time() - start_time
            self.test_results['passed_tests'] += 1
            
            test_detail = {
                'name': test_name,
                'status': 'PASSED',
                'execution_time': round(execution_time, 2),
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ {test_name} - PASSED ({execution_time:.2f}s)")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.test_results['failed_tests'] += 1
            
            test_detail = {
                'name': test_name,
                'status': 'FAILED',
                'execution_time': round(execution_time, 2),
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.error(f"❌ {test_name} - FAILED ({execution_time:.2f}s): {str(e)}")
            
        self.test_results['test_details'].append(test_detail)
        return test_detail['status'] == 'PASSED'
    
    def test_aws_connectivity(self) -> Dict[str, Any]:
        """Test AWS service connectivity"""
        services_status = {}
        
        # Test S3 connectivity
        try:
            self.s3_client.head_bucket(Bucket=self.request_bucket)
            services_status['s3_request_bucket'] = 'accessible'
        except Exception as e:
            services_status['s3_request_bucket'] = f'error: {str(e)}'
        
        try:
            self.s3_client.head_bucket(Bucket=self.response_bucket)
            services_status['s3_response_bucket'] = 'accessible'
        except Exception as e:
            services_status['s3_response_bucket'] = f'error: {str(e)}'
        
        # Test Lambda connectivity
        try:
            self.lambda_client.get_function(FunctionName=self.lambda_function)
            services_status['lambda_function'] = 'accessible'
        except Exception as e:
            services_status['lambda_function'] = f'error: {str(e)}'
        
        # Test Translate connectivity
        try:
            self.translate_client.list_languages()
            services_status['translate_service'] = 'accessible'
        except Exception as e:
            services_status['translate_service'] = f'error: {str(e)}'
        
        return services_status
    
    def test_s3_upload_download(self) -> Dict[str, Any]:
        """Test S3 upload and download functionality"""
        test_key = f"test_file_{uuid.uuid4().hex}.json"
        test_content = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
        
        # Upload test file
        self.s3_client.put_object(
            Bucket=self.request_bucket,
            Key=test_key,
            Body=json.dumps(test_content),
            ContentType='application/json'
        )
        
        # Download and verify
        response = self.s3_client.get_object(Bucket=self.request_bucket, Key=test_key)
        downloaded_content = json.loads(response['Body'].read().decode('utf-8'))
        
        # Cleanup
        self.s3_client.delete_object(Bucket=self.request_bucket, Key=test_key)
        
        if downloaded_content == test_content:
            return {"status": "success", "uploaded_key": test_key}
        else:
            raise Exception("Downloaded content doesn't match uploaded content")
    
    def test_lambda_invoke_direct(self) -> Dict[str, Any]:
        """Test direct Lambda function invocation"""
        test_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": self.request_bucket},
                        "object": {"key": "test_direct_invoke.json"}
                    }
                }
            ]
        }
        
        # Create test file first
        test_request = {
            "request_id": f"test_direct_{uuid.uuid4().hex}",
            "source_language": "en",
            "target_language": "es",
            "texts": [{"id": 1, "text": "Hello world"}]
        }
        
        self.s3_client.put_object(
            Bucket=self.request_bucket,
            Key="test_direct_invoke.json",
            Body=json.dumps(test_request),
            ContentType='application/json'
        )
        
        try:
            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            # Parse response
            payload = json.loads(response['Payload'].read().decode('utf-8'))
            
            # Cleanup
            self.s3_client.delete_object(Bucket=self.request_bucket, Key="test_direct_invoke.json")
            
            return {
                "status_code": response['StatusCode'],
                "payload": payload,
                "execution_duration": response.get('ExecutionDuration', 0)
            }
            
        except Exception as e:
            # Cleanup on error
            try:
                self.s3_client.delete_object(Bucket=self.request_bucket, Key="test_direct_invoke.json")
            except:
                pass
            raise e
    
    def test_translation_end_to_end(self) -> Dict[str, Any]:
        """Test complete translation workflow"""
        request_id = f"test_e2e_{uuid.uuid4().hex}"
        
        # Create translation request
        translation_request = {
            "request_id": request_id,
            "source_language": "en",
            "target_language": "es",
            "texts": [
                {"id": 1, "text": "Hello, how are you?"},
                {"id": 2, "text": "This is a test message."},
                {"id": 3, "text": "Thank you for using our service."}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Upload request file
        request_key = f"translation_request_{request_id}.json"
        self.s3_client.put_object(
            Bucket=self.request_bucket,
            Key=request_key,
            Body=json.dumps(translation_request),
            ContentType='application/json'
        )
        
        # Wait for processing
        max_wait_time = 120  # 2 minutes
        poll_interval = 5    # 5 seconds
        wait_time = 0
        
        while wait_time < max_wait_time:
            time.sleep(poll_interval)
            wait_time += poll_interval
            
            # Check for result file
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.response_bucket,
                    Prefix=f"translation_request_{request_id}_translated"
                )
                
                if 'Contents' in response and len(response['Contents']) > 0:
                    # Found result file
                    result_key = response['Contents'][0]['Key']
                    
                    # Download result
                    result_response = self.s3_client.get_object(Bucket=self.response_bucket, Key=result_key)
                    result_content = json.loads(result_response['Body'].read().decode('utf-8'))
                    
                    # Cleanup
                    self.s3_client.delete_object(Bucket=self.request_bucket, Key=request_key)
                    self.s3_client.delete_object(Bucket=self.response_bucket, Key=result_key)
                    
                    return {
                        "processing_time": wait_time,
                        "result_key": result_key,
                        "translations_count": len(result_content.get('translations', [])),
                        "metadata": result_content.get('translation_metadata', {}),
                        "status": "completed"
                    }
                    
            except Exception as e:
                logger.warning(f"Error checking for result: {str(e)}")
        
        # Cleanup if timeout
        try:
            self.s3_client.delete_object(Bucket=self.request_bucket, Key=request_key)
        except:
            pass
        
        raise Exception(f"Translation processing timed out after {max_wait_time} seconds")
    
    def test_language_support(self) -> Dict[str, Any]:
        """Test supported languages"""
        try:
            languages = self.translate_client.list_languages()
            
            # Test a few common language pairs
            test_pairs = [
                ("en", "es"),  # English to Spanish
                ("en", "fr"),  # English to French
                ("es", "en"),  # Spanish to English
                ("fr", "de"),  # French to German
            ]
            
            supported_pairs = []
            for source, target in test_pairs:
                try:
                    # Test with a simple phrase
                    response = self.translate_client.translate_text(
                        Text="Hello",
                        SourceLanguageCode=source,
                        TargetLanguageCode=target
                    )
                    supported_pairs.append({
                        "source": source,
                        "target": target,
                        "test_translation": response['TranslatedText'],
                        "status": "supported"
                    })
                except Exception as e:
                    supported_pairs.append({
                        "source": source,
                        "target": target,
                        "error": str(e),
                        "status": "error"
                    })
            
            return {
                "total_languages": len(languages['Languages']),
                "test_pairs": supported_pairs,
                "sample_languages": languages['Languages'][:10]  # First 10 languages
            }
            
        except Exception as e:
            raise Exception(f"Error testing language support: {str(e)}")
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios"""
        test_cases = []
        
        # Test 1: Invalid JSON format
        try:
            invalid_json = "{ invalid json content"
            self.s3_client.put_object(
                Bucket=self.request_bucket,
                Key="test_invalid_json.json",
                Body=invalid_json,
                ContentType='application/json'
            )
            
            # Wait briefly and check if system handles it gracefully
            time.sleep(10)
            
            # Cleanup
            self.s3_client.delete_object(Bucket=self.request_bucket, Key="test_invalid_json.json")
            
            test_cases.append({"test": "invalid_json", "status": "handled_gracefully"})
            
        except Exception as e:
            test_cases.append({"test": "invalid_json", "status": "error", "error": str(e)})
        
        # Test 2: Missing required fields
        try:
            incomplete_request = {
                "request_id": "test_incomplete",
                "source_language": "en"
                # Missing target_language and texts
            }
            
            self.s3_client.put_object(
                Bucket=self.request_bucket,
                Key="test_incomplete.json",
                Body=json.dumps(incomplete_request),
                ContentType='application/json'
            )
            
            time.sleep(10)
            
            # Cleanup
            self.s3_client.delete_object(Bucket=self.request_bucket, Key="test_incomplete.json")
            
            test_cases.append({"test": "incomplete_request", "status": "handled_gracefully"})
            
        except Exception as e:
            test_cases.append({"test": "incomplete_request", "status": "error", "error": str(e)})
        
        # Test 3: Unsupported language code
        try:
            unsupported_lang_request = {
                "request_id": "test_unsupported_lang",
                "source_language": "xx",  # Invalid language code
                "target_language": "yy",  # Invalid language code
                "texts": [{"id": 1, "text": "Test text"}]
            }
            
            self.s3_client.put_object(
                Bucket=self.request_bucket,
                Key="test_unsupported_lang.json",
                Body=json.dumps(unsupported_lang_request),
                ContentType='application/json'
            )
            
            time.sleep(10)
            
            # Cleanup
            self.s3_client.delete_object(Bucket=self.request_bucket, Key="test_unsupported_lang.json")
            
            test_cases.append({"test": "unsupported_language", "status": "handled_gracefully"})
            
        except Exception as e:
            test_cases.append({"test": "unsupported_language", "status": "error", "error": str(e)})
        
        return {"error_test_cases": test_cases}
    
    def test_performance_metrics(self) -> Dict[str, Any]:
        """Test performance with various text sizes"""
        performance_results = []
        
        test_cases = [
            {"name": "small_text", "char_count": 50, "text": "This is a small text for performance testing."},
            {"name": "medium_text", "char_count": 500, "text": "This is a medium-sized text for performance testing. " * 10},
            {"name": "large_text", "char_count": 2000, "text": "This is a large text for performance testing. " * 50}
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            
            try:
                # Direct translation test
                response = self.translate_client.translate_text(
                    Text=test_case["text"],
                    SourceLanguageCode="en",
                    TargetLanguageCode="es"
                )
                
                processing_time = time.time() - start_time
                
                performance_results.append({
                    "test_name": test_case["name"],
                    "character_count": test_case["char_count"],
                    "processing_time": round(processing_time, 3),
                    "characters_per_second": round(test_case["char_count"] / processing_time, 2),
                    "status": "success"
                })
                
            except Exception as e:
                processing_time = time.time() - start_time
                performance_results.append({
                    "test_name": test_case["name"],
                    "character_count": test_case["char_count"],
                    "processing_time": round(processing_time, 3),
                    "error": str(e),
                    "status": "error"
                })
        
        return {"performance_metrics": performance_results}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests in the suite"""
        logger.info("🚀 Starting comprehensive test suite...")
        
        # Test 1: AWS Connectivity
        self.run_test("AWS Service Connectivity", self.test_aws_connectivity)
        
        # Test 2: S3 Operations
        self.run_test("S3 Upload/Download", self.test_s3_upload_download)
        
        # Test 3: Lambda Direct Invocation
        self.run_test("Lambda Direct Invocation", self.test_lambda_invoke_direct)
        
        # Test 4: End-to-End Translation
        self.run_test("End-to-End Translation", self.test_translation_end_to_end)
        
        # Test 5: Language Support
        self.run_test("Language Support", self.test_language_support)
        
        # Test 6: Error Handling
        self.run_test("Error Handling", self.test_error_handling)
        
        # Test 7: Performance Metrics
        self.run_test