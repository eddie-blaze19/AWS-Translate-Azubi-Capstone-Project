# AWS-Translate-Azubi-Capstone-Project
This project implements a serverless translation solution using AWS services with Infrastructure-as-Code principles. The solution automatically processes JSON files containing text for translation, uses AWS Translate for language conversion, and stores results in S3. 

![AWS](https://img.shields.io/badge/AWS-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Serverless](https://img.shields.io/badge/Serverless-FD5750?style=for-the-badge&logo=serverless&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-623CE4?style=for-the-badge&logo=terraform&logoColor=white)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Source S3     │───▶│   Lambda        │───▶│   Destination   │
│   Bucket        │    │   Function      │    │   S3 Bucket     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │                 │
                       │  AWS Translate  │
                       │   Service       │
                       │                 │
                       └─────────────────┘
```

## ✨ Features

- **Serverless Architecture**: Built with AWS Lambda, S3, and managed services
- **Event-Driven**: Automatically processes files uploaded to S3
- **Multi-Language Support**: Supports 75+ languages via AWS Translate
- **Infrastructure as Code**: Automated deployment with Terraform/CloudFormation
- **Scalable**: Handles varying workloads automatically
- **Cost-Effective**: Pay-per-use pricing model

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0 OR AWS CLI for CloudFormation
- Python 3.9+

### Deployment

#### Option 1: Terraform
```bash
git clone https://github.com/eddie-blaze19/AWS-Translate-Azubi-Capstone-Project.git
cd AWS-Translate-Azubi-Capstone-Project/infrastructure/terraform
terraform init
terraform plan
terraform apply
```

#### Option 2: CloudFormation
```bash
git clone https://github.com/eddie-blaze19/AWS-Translate-Azubi-Capstone-Project.git
cd AWS-Translate-Azubi-Capstone-Project
aws cloudformation create-stack \
  --stack-name aws-translate-solution \
  --template-body file://infrastructure/cloudformation/template.yaml \
  --capabilities CAPABILITY_IAM
```

## 📋 Usage

### Input Format
Upload JSON files to the source S3 bucket with this structure:
```json
{
  "text": "Hello, how are you today?",
  "source_language": "en",
  "target_language": "es",
  "metadata": {
    "document_id": "doc_001",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Output Format
Translated results are automatically saved to the destination bucket:
```json
{
  "original_text": "Hello, how are you today?",
  "translated_text": "Hola, ¿cómo estás hoy?",
  "source_language": "en",
  "target_language": "es",
  "translation_metadata": {
    "confidence_score": 0.95,
    "translation_time": "2024-01-15T10:30:05Z"
  },
  "metadata": {
    "document_id": "doc_001",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## 📁 Project Structure

```
AWS-Translate-Azubi-Capstone-Project/
├── src/
│   ├── lambda/
│   │   ├── translate_function.py      # Main Lambda function
│   │   ├── requirements.txt           # Python dependencies
│   │   └── utils/                     # Utility functions
│   └── tests/
│       ├── test_translate_function.py # Unit tests
│       └── sample_data/               # Test data
├── infrastructure/
│   ├── terraform/                     # Terraform IaC files
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── cloudformation/                # CloudFormation templates
│       └── template.yaml
├── docs/                              # Additional documentation
└── examples/                          # Sample files
    ├── sample_input.json
    └── sample_output.json
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `DEST_BUCKET_NAME` | Destination S3 bucket | Set by IaC |
| `SOURCE_LANGUAGE` | Default source language | `auto` |
| `TARGET_LANGUAGE` | Default target language | `en` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### Supported Languages
Common language codes supported by AWS Translate:

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | `en` | Spanish | `es` |
| French | `fr` | German | `de` |
| Italian | `it` | Portuguese | `pt` |
| Chinese | `zh` | Japanese | `ja` |
| Arabic | `ar` | Russian | `ru` |

## 🧪 Testing

```bash
# Install dependencies
pip install -r src/lambda/requirements.txt
pip install pytest

# Run tests
python -m pytest src/tests/ -v
```

## 📊 Monitoring

The solution includes built-in monitoring:
- **CloudWatch Logs**: Lambda execution logs
- **CloudWatch Metrics**: Translation success/failure rates
- **CloudWatch Alarms**: Error rate alerts

Access logs:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/translate"
```


## 🔒 Security

- Server-side encryption for all S3 buckets
- IAM roles with least-privilege access
- Input validation and sanitization
- VPC configuration support
- CloudTrail audit logging

## 🛠️ Troubleshooting

### Common Issues

**Lambda timeout errors**
```bash
# Check CloudWatch logs
aws logs filter-log-events --log-group-name "/aws/lambda/translate-function"
```

**Permission denied**
- Verify IAM roles have necessary permissions
- Check S3 bucket policies

**Translation failures**
- Validate JSON input format
- Verify language codes are supported

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- 📧 Email: [your-email@example.com]
- 🐛 Issues: [GitHub Issues](https://github.com/eddie-blaze19/AWS-Translate-Azubi-Capstone-Project/issues)
- 📖 Documentation: [Project Wiki](https://github.com/eddie-blaze19/AWS-Translate-Azubi-Capstone-Project/wiki)

## 🏆 Acknowledgments

- Built as part of the Azubi Africa Capstone Project
- Powered by AWS Serverless technologies
- Infrastructure as Code best practices

 
