# AWS Translation Infrastructure with Terraform
provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "aws-translate-solution"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Random suffix for unique bucket names
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket for Translation Requests
resource "aws_s3_bucket" "request_bucket" {
  bucket = "${var.project_name}-request-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Translation Request Bucket"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Bucket for Translation Responses
resource "aws_s3_bucket" "response_bucket" {
  bucket = "${var.project_name}-response-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Translation Response Bucket"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Bucket versioning for request bucket
resource "aws_s3_bucket_versioning" "request_bucket_versioning" {
  bucket = aws_s3_bucket.request_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket versioning for response bucket
resource "aws_s3_bucket_versioning" "response_bucket_versioning" {
  bucket = aws_s3_bucket.response_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket server-side encryption for request bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "request_bucket_encryption" {
  bucket = aws_s3_bucket.request_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket server-side encryption for response bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "response_bucket_encryption" {
  bucket = aws_s3_bucket.response_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket lifecycle configuration for request bucket
resource "aws_s3_bucket_lifecycle_configuration" "request_bucket_lifecycle" {
  bucket = aws_s3_bucket.request_bucket.id

  rule {
    id     = "delete_old_files"
    status = "Enabled"

    filter {} # APPLIES RULE TO ALL OBJECTS

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# S3 Bucket lifecycle configuration for response bucket
resource "aws_s3_bucket_lifecycle_configuration" "response_bucket_lifecycle" {
  bucket = aws_s3_bucket.response_bucket.id

  rule {
    id     = "delete_old_files"
    status = "Enabled"

    filter {} # APPLIES RULE TO ALL OBJECTS

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# S3 Bucket public access block for request bucket
resource "aws_s3_bucket_public_access_block" "request_bucket_pab" {
  bucket = aws_s3_bucket.request_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket public access block for response bucket
resource "aws_s3_bucket_public_access_block" "response_bucket_pab" {
  bucket = aws_s3_bucket.response_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Role for Lambda function
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "Lambda Execution Role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for Lambda function
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy"
  description = "IAM policy for translation Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.request_bucket.arn}/*",
          "${aws_s3_bucket.response_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.request_bucket.arn,
          aws_s3_bucket.response_bucket.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "translate:TranslateText",
          "translate:DescribeTextTranslationJob",
          "translate:ListTextTranslationJobs"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Create Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_function"
  output_path = "${path.module}/lambda_function.zip"
}

# Lambda function
resource "aws_lambda_function" "translation_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-translator"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.9"
  timeout          = 300

  environment {
    variables = {
      REQUEST_BUCKET  = aws_s3_bucket.request_bucket.bucket
      RESPONSE_BUCKET = aws_s3_bucket.response_bucket.bucket
    }
  }

  tags = {
    Name        = "Translation Processor"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.translation_processor.function_name}"
  retention_in_days = 14

  tags = {
    Name        = "Translation Lambda Logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 bucket notification for Lambda trigger
resource "aws_s3_bucket_notification" "s3_notification" {
  bucket = aws_s3_bucket.request_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.translation_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.s3_invoke_lambda]
}

# Lambda permission for S3 to invoke the function
resource "aws_lambda_permission" "s3_invoke_lambda" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.translation_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.request_bucket.arn
}

# API Gateway
resource "aws_api_gateway_rest_api" "translation_api" {
  name        = "${var.project_name}-api"
  description = "API for translation service"
}

resource "aws_api_gateway_resource" "upload_resource" {
  rest_api_id = aws_api_gateway_rest_api.translation_api.id
  parent_id   = aws_api_gateway_rest_api.translation_api.root_resource_id
  path_part   = "upload"
}

resource "aws_api_gateway_method" "upload_method" {
  rest_api_id   = aws_api_gateway_rest_api.translation_api.id
  resource_id   = aws_api_gateway_resource.upload_resource.id
  http_method   = "POST"
  authorization = "NONE"
}
# Integration for /upload resource to S3
# This integration allows API Gateway to put objects into the S3 bucket
resource "aws_api_gateway_integration" "s3_integration" {
  rest_api_id             = aws_api_gateway_rest_api.translation_api.id
  resource_id             = aws_api_gateway_resource.upload_resource.id
  http_method             = aws_api_gateway_method.upload_method.http_method
  integration_http_method = "PUT"
  type                    = "AWS"
  credentials             = aws_iam_role.api_gateway_s3_role.arn
  
  uri                     = "arn:aws:apigateway:${var.aws_region}:s3:path/{bucket}/{key}"

  request_parameters = {
    "integration.request.path.bucket" = "'${aws_s3_bucket.request_bucket.bucket}'"
    "integration.request.path.key"    = "method.request.body.request_id"
    "integration.request.header.Content-Type" = "'application/json'"
  }

  # --- FIX IS HERE ---
  request_templates = {
    "application/json" = <<EOF
{
    "source_language": "$input.path('$.source_language')",
    "target_language": "$input.path('$.target_language')",
    "texts": [
        {
            "id": 1,
            "text": "$input.path('$.text')"
        }
    ]
}
EOF
  }
}

# START: CORS CONFIGURATION FOR /upload
resource "aws_api_gateway_method" "upload_options_method" {
  rest_api_id   = aws_api_gateway_rest_api.translation_api.id
  resource_id   = aws_api_gateway_resource.upload_resource.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "upload_options_integration" {
  rest_api_id   = aws_api_gateway_rest_api.translation_api.id
  resource_id   = aws_api_gateway_resource.upload_resource.id
  http_method   = aws_api_gateway_method.upload_options_method.http_method
  type          = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_200" {
  rest_api_id = aws_api_gateway_rest_api.translation_api.id
  resource_id = aws_api_gateway_resource.upload_resource.id
  http_method = aws_api_gateway_method.upload_options_method.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.translation_api.id
  resource_id = aws_api_gateway_resource.upload_resource.id
  http_method = aws_api_gateway_method.upload_options_method.http_method
  status_code = aws_api_gateway_method_response.options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'",
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.upload_options_integration]
}
# END: CORS CONFIGURATION

resource "aws_iam_role" "api_gateway_s3_role" {
  name = "${var.project_name}-api-gateway-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "api_gateway_s3_policy" {
  name        = "${var.project_name}-api-gateway-s3-policy"
  description = "Policy for API Gateway to put objects in S3"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = "s3:PutObject",
        Effect   = "Allow",
        Resource = "${aws_s3_bucket.request_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_gateway_s3_attachment" {
  role       = aws_iam_role.api_gateway_s3_role.name
  policy_arn = aws_iam_policy.api_gateway_s3_policy.arn
}

resource "aws_api_gateway_resource" "result_resource" {
  rest_api_id = aws_api_gateway_rest_api.translation_api.id
  parent_id   = aws_api_gateway_rest_api.translation_api.root_resource_id
  path_part   = "result"
}

resource "aws_api_gateway_resource" "result_proxy_resource" {
  rest_api_id = aws_api_gateway_rest_api.translation_api.id
  parent_id   = aws_api_gateway_resource.result_resource.id
  path_part   = "{request_id}"
}

resource "aws_api_gateway_method" "result_method" {
  rest_api_id   = aws_api_gateway_rest_api.translation_api.id
  resource_id   = aws_api_gateway_resource.result_proxy_resource.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.request_id" = true
  }
}


resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.translation_api.id
  resource_id             = aws_api_gateway_resource.result_proxy_resource.id
  http_method             = aws_api_gateway_method.result_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.retrieval_lambda.invoke_arn
}

resource "aws_lambda_permission" "api_gateway_invoke_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.retrieval_lambda.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.translation_api.execution_arn}/*/${aws_api_gateway_method.result_method.http_method}${aws_api_gateway_resource.result_proxy_resource.path}"
}

data "archive_file" "retrieval_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/retrieval_function/lambda_function.py"
  output_path = "${path.module}/retrieval_function.zip"
}

resource "aws_lambda_function" "retrieval_lambda" {
  filename         = data.archive_file.retrieval_lambda_zip.output_path
  function_name    = "${var.project_name}-retriever"
  role             = aws_iam_role.retrieval_lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.retrieval_lambda_zip.output_base64sha256
  runtime          = "python3.9"
  timeout          = 30

  environment {
    variables = {
      RESPONSE_BUCKET = aws_s3_bucket.response_bucket.bucket
    }
  }
}

resource "aws_iam_role" "retrieval_lambda_role" {
  name = "${var.project_name}-retrieval-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "retrieval_lambda_policy" {
  name        = "${var.project_name}-retrieval-lambda-policy"
  description = "Policy for retrieval Lambda to read from S3"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = "s3:GetObject",
        Effect   = "Allow",
        Resource = "${aws_s3_bucket.response_bucket.arn}/*"
      },
      {
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "retrieval_lambda_attachment" {
  role       = aws_iam_role.retrieval_lambda_role.name
  policy_arn = aws_iam_policy.retrieval_lambda_policy.arn
}

resource "aws_api_gateway_deployment" "api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.translation_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.upload_resource.id,
      aws_api_gateway_method.upload_method.id,
      aws_api_gateway_integration.s3_integration.id,
      aws_api_gateway_resource.result_proxy_resource.id,
      aws_api_gateway_method.result_method.id,
      aws_api_gateway_integration.lambda_integration.id,
      # Add the new CORS resources to the trigger
      aws_api_gateway_method.upload_options_method.id,
      aws_api_gateway_integration.upload_options_integration.id,
      aws_api_gateway_method_response.options_200.id,
      aws_api_gateway_integration_response.options_integration_response.id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.translation_api.id
  stage_name    = var.environment
}


# Outputs
output "request_bucket_name" {
  description = "Name of the S3 bucket for translation requests"
  value       = aws_s3_bucket.request_bucket.bucket
}

output "response_bucket_name" {
  description = "Name of the S3 bucket for translation responses"
  value       = aws_s3_bucket.response_bucket.bucket
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.translation_processor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.translation_processor.arn
}

output "api_gateway_invoke_url" {
  description = "Invoke URL for the API Gateway"
  value       = aws_api_gateway_stage.api_stage.invoke_url
}