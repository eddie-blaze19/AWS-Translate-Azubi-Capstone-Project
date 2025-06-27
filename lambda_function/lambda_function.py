import json
import boto3
import os
import logging
from datetime import datetime
from urllib.parse import unquote_plus

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
translate_client = boto3.client('translate')

def lambda_handler(event, context):
    """
    Lambda function to process translation requests from S3
    """
    try:
        # Get bucket names from environment variables
        request_bucket = os.environ['REQUEST_BUCKET']
        response_bucket = os.environ['RESPONSE_BUCKET']
        
        # Process each record in the event
        for record in event['Records']:
            # Get bucket and object key from the event
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing file: {key} from bucket: {bucket}")
            
            # Download the JSON file from S3
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                file_content = response['Body'].read().decode('utf-8')
                
                # Parse JSON content
                translation_request = json.loads(file_content)
                
                # Validate required fields
                if not validate_translation_request(translation_request):
                    logger.error(f"Invalid translation request format in file: {key}")
                    continue
                
                # Process translation
                translation_result = process_translation(translation_request)
                
                # Generate output filename
                output_key = generate_output_key(key)
                
                # Upload result to response bucket
                upload_result_to_s3(response_bucket, output_key, translation_result)
                
                logger.info(f"Successfully processed translation for file: {key}")
                
            except Exception as e:
                logger.error(f"Error processing file {key}: {str(e)}")
                continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Translation processing completed successfully',
                'processed_files': len(event['Records'])
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Translation processing failed',
                'message': str(e)
            })
        }

def validate_translation_request(request_data):
    """
    Validate the structure of translation request
    """
    required_fields = ['source_language', 'target_language', 'texts']
    
    for field in required_fields:
        if field not in request_data:
            logger.error(f"Missing required field: {field}")
            return False
    
    if not isinstance(request_data['texts'], list):
        logger.error("'texts' field must be a list")
        return False
    
    if len(request_data['texts']) == 0:
        logger.error("'texts' list cannot be empty")
        return False
    
    return True

def process_translation(translation_request):
    """
    Process translation using AWS Translate service
    """
    source_language = translation_request['source_language']
    target_language = translation_request['target_language']
    texts = translation_request['texts']
    
    translated_texts = []
    total_characters = 0
    
    try:
        for text_item in texts:
            if isinstance(text_item, dict) and 'text' in text_item:
                text_to_translate = text_item['text']
                text_id = text_item.get('id', len(translated_texts))
            else:
                text_to_translate = str(text_item)
                text_id = len(translated_texts)
            
            # Skip empty texts
            if not text_to_translate.strip():
                translated_texts.append({
                    'id': text_id,
                    'original_text': text_to_translate,
                    'translated_text': '',
                    'character_count': 0
                })
                continue
            
            # Translate text using AWS Translate
            logger.info(f"Translating text ID {text_id} from {source_language} to {target_language}")
            
            translation_response = translate_client.translate_text(
                Text=text_to_translate,
                SourceLanguageCode=source_language,
                TargetLanguageCode=target_language
            )
            
            translated_text = translation_response['TranslatedText']
            character_count = len(text_to_translate)
            total_characters += character_count
            
            translated_texts.append({
                'id': text_id,
                'original_text': text_to_translate,
                'translated_text': translated_text,
                'character_count': character_count
            })
            
            logger.info(f"Successfully translated text ID {text_id}")
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise e
    
    # Prepare result
    result = {
        'translation_metadata': {
            'source_language': source_language,
            'target_language': target_language,
            'total_texts': len(texts),
            'total_characters': total_characters,
            'timestamp': datetime.utcnow().isoformat(),
            'processing_status': 'completed'
        },
        'translations': translated_texts,
        'original_request': translation_request
    }
    
    return result

def generate_output_key(input_key):
    """
    Generate output key for translated file
    """
    # Remove file extension and add timestamp
    base_name = os.path.splitext(input_key)[0]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_translated_{timestamp}.json"

def upload_result_to_s3(bucket, key, result_data):
    """
    Upload translation result to S3 response bucket
    """
    try:
        # Convert result to JSON string
        json_content = json.dumps(result_data, indent=2, ensure_ascii=False)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json_content.encode('utf-8'),
            ContentType='application/json',
            ServerSideEncryption='AES256',
            Metadata={
                'processing-timestamp': datetime.utcnow().isoformat(),
                'content-type': 'translation-result'
            }
        )
        
        logger.info(f"Successfully uploaded result to s3://{bucket}/{key}")
        
    except Exception as e:
        logger.error(f"Error uploading result to S3: {str(e)}")
        raise e