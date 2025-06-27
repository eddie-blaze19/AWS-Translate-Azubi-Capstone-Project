import json
import boto3
import os

# Initialize the S3 client
s3 = boto3.client('s3')
# Get the response bucket name from the Lambda's environment variables
response_bucket = os.environ['RESPONSE_BUCKET']

def lambda_handler(event, context):
    """
    This function is triggered by API Gateway to retrieve a translated file from S3.
    """
    # Extract the request_id from the URL path parameter
    # The key in S3 will be the request_id (e.g., "req-xyz123.json")
    try:
        request_id = event['pathParameters']['request_id']
    except KeyError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Required for CORS
            },
            'body': json.dumps({'message': 'Error: Missing request_id in path.'})
        }

    try:
        # Attempt to get the object from the S3 response bucket
        response = s3.get_object(Bucket=response_bucket, Key=request_id)
        # Read the content of the file
        file_content = response['Body'].read().decode('utf-8')
        
        # Return a 200 OK response with the file content
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Required for CORS
            },
            'body': file_content
        }

    except s3.exceptions.NoSuchKey:
        # This is the expected "error" when the file isn't ready yet
        # The frontend will poll until it stops receiving this 404 status
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Required for CORS
            },
            'body': json.dumps({'message': 'Translation not found or still processing.'})
        }
        
    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # Required for CORS
            },
            'body': json.dumps({'message': 'An internal server error occurred.'})
        }