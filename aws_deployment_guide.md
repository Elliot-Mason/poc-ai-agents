# AWS ECS Fargate Deployment Guide for AI Agents

This guide provides instructions to containerize and deploy the three Bedrock-backed agent applications to **AWS ECS Fargate** using standard AWS IAM authentication.

---

## 1. Repository Structure & Mono-repo Choice

Keeping all three applications in a single repository (a mono-repo) is **fully supported** and recommended for this stage. You do not need to break them into three separate repositories unless you want separate ownership or isolation in CI/CD pipelines.

In a mono-repo structure:
- You build three separate Docker images, referencing their respective folders.
- You push them to three different **Amazon ECR** (Elastic Container Registry) repositories.
- You deploy them as three separate **ECS Services** in your ECS Cluster (or under a single cluster behind an Application Load Balancer using path-based routing).

---

## 2. Containerization

We have created/updated the following `Dockerfiles` for each application. They inherit from `python:3.10-slim`, install dependencies, run DB initialization scripts, and start `uvicorn` on port `8080` (standard for AWS ECS):

1. **AI Mortgage**: [aimortgage/unsafe/Dockerfile](file:///C:/Users/Elliot/Desktop/Desktop/Dev/Work/poc-ai-agents/aimortgage/unsafe/Dockerfile)
2. **Blackcard**: [blackcard/unsafe/Dockerfile](file:///C:/Users/Elliot/Desktop/Desktop/Dev/Work/poc-ai-agents/blackcard/unsafe/Dockerfile)
3. **Credit Card Bot**: [creditcardbot/unsafe/Dockerfile](file:///C:/Users/Elliot/Desktop/Desktop/Dev/Work/poc-ai-agents/creditcardbot/unsafe/Dockerfile)

---

## 3. Bedrock & IAM Integration

### Client Adapter Updates
We updated the Bedrock client code in the adapters:
- [aimortgage/unsafe/llm/bedrock_adapter.py](file:///C:/Users/Elliot/Desktop/Desktop/Dev/Work/poc-ai-agents/aimortgage/unsafe/llm/bedrock_adapter.py)
- [blackcard/unsafe/llm/bedrock_adapter.py](file:///C:/Users/Elliot/Desktop/Desktop/Dev/Work/poc-ai-agents/blackcard/unsafe/llm/bedrock_adapter.py)

**What changed**: 
Previously, the code only supported bearer token authentication via `AWS_BEARER_TOKEN_BEDROCK`. We modified the adapters to support a fallback. If the bearer token is not set, they will instantiate a standard `boto3` client:
```python
self._boto3_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=aws_region,
)
```
This automatically resolves credentials from the container environment using standard AWS credentials lookup, meaning they will **natively authorize via your ECS Fargate Task Roles** without any code changes!

### IAM Policies Setup
Ensure that the IAM Role associated with your ECS Tasks (the **Task Role**) has a policy attached with permission to call Amazon Bedrock. 

Example Bedrock Converse Policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:Converse",
                "bedrock:ConverseStream"
            ],
            "Resource": "*"
        }
    ]
}
```

> [!NOTE]
> Make sure the policy is attached to the **ECS Task Role** (which grants permissions to the application code running inside the container) and NOT just the **ECS Task Execution Role** (which is only used by the ECS Agent to pull images from ECR and send logs to CloudWatch).

---

## 4. Build and Push to Amazon ECR

For each of the three applications, follow these steps to build the docker image and push it to ECR:

### Step 4.1: Log in to ECR
```bash
# Retrieve an authentication token and authenticate your Docker client to your registry
aws ecr get-login-password --region <YOUR_AWS_REGION> | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com
```

### Step 4.2: Create ECR Repositories (One-time setup)
```bash
aws ecr create-repository --repository-name aimortgage-unsafe --region <YOUR_AWS_REGION>
aws ecr create-repository --repository-name blackcard-unsafe --region <YOUR_AWS_REGION>
aws ecr create-repository --repository-name creditcardbot-unsafe --region <YOUR_AWS_REGION>
```

### Step 4.3: Build, Tag, and Push Images

#### 1. AI Mortgage
Run from repository root:
```bash
docker build -t aimortgage-unsafe -f aimortgage/unsafe/Dockerfile aimortgage/unsafe
docker tag aimortgage-unsafe:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/aimortgage-unsafe:latest
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/aimortgage-unsafe:latest
```

#### 2. Blackcard
Run from repository root:
```bash
docker build -t blackcard-unsafe -f blackcard/unsafe/Dockerfile blackcard/unsafe
docker tag blackcard-unsafe:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/blackcard-unsafe:latest
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/blackcard-unsafe:latest
```

#### 3. Credit Card Bot
Run from repository root:
```bash
docker build -t creditcardbot-unsafe -f creditcardbot/unsafe/Dockerfile creditcardbot/unsafe
docker tag creditcardbot-unsafe:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/creditcardbot-unsafe:latest
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/creditcardbot-unsafe:latest
```

---

## 5. ECS Fargate Setup

### Step 5.1: Create Task Definitions
For each of the three applications, register a new Task Definition with AWS ECS:
1. **Launch Type**: Fargate.
2. **Task Role**: Select your role with Amazon Bedrock Converse permissions.
3. **Task Execution Role**: Select standard role with ECR pull & CloudWatch logging permissions (`AmazonECSTaskExecutionRolePolicy`).
4. **Container Settings**:
   - **Image**: `<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/<APP-NAME>-unsafe:latest`
   - **Port Mappings**: Port `8080` (TCP).
   - **Environment Variables**:
     - `BEDROCK_MODEL_ID`: `anthropic.claude-sonnet-4-5-20250929-v1:0` (or another model ID)
     - `AWS_REGION`: `<YOUR_AWS_REGION>` (e.g., `us-east-1` or `ap-southeast-2`)
     - Do **NOT** set `AWS_BEARER_TOKEN_BEDROCK`. When omitted, the app automatically switches to the `boto3` IAM task-role credential path.

### Step 5.2: Create ECS Services
Deploy the task definitions into your ECS Cluster:
1. Select **Fargate** launch type.
2. Select your target **Service Name** (e.g. `aimortgage-service`).
3. Set **Number of Tasks** (e.g. `1` or `2`).
4. Configure your **VPC and Subnets** (Fargate requires private subnets with NAT Gateway or public subnets with public IP enabled).
5. Add an **Application Load Balancer (ALB)** (Optional but recommended):
   - You can place all three services behind a single ALB using path-based routing (e.g., `/mortgage/*` to `aimortgage`, `/blackcard/*` to `blackcard`, and `/creditcard/*` to `creditcardbot`), or use separate ALBs/ports.

---

## 6. ECS Task Definition JSON Templates

Below are the complete, ready-to-register Task Definition JSON documents for each of the three applications. 

You can save these to files (e.g., `aimortgage-task.json`) and register them via AWS CLI:
```bash
aws ecs register-task-definition --cli-input-json file://aimortgage-task.json
```

### 6.1 AI Mortgage Task Definition (`aimortgage-task.json`)
```json
{
  "family": "aimortgage-unsafe-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": [
    "FARGATE"
  ],
  "cpu": "256",
  "memory": "512",
  "taskRoleArn": "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/<YOUR_ECS_TASK_ROLE_NAME>",
  "executionRoleArn": "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/<YOUR_ECS_TASK_EXECUTION_ROLE_NAME>",
  "containerDefinitions": [
    {
      "name": "aimortgage-unsafe",
      "image": "<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/aimortgage-unsafe:latest",
      "cpu": 256,
      "memory": 512,
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "<YOUR_AWS_REGION>"
        },
        {
          "name": "BEDROCK_MODEL_ID",
          "value": "anthropic.claude-sonnet-4-5-20250929-v1:0"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/aimortgage-unsafe-task",
          "awslogs-region": "<YOUR_AWS_REGION>",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
```

### 6.2 Blackcard Task Definition (`blackcard-task.json`)
```json
{
  "family": "blackcard-unsafe-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": [
    "FARGATE"
  ],
  "cpu": "256",
  "memory": "512",
  "taskRoleArn": "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/<YOUR_ECS_TASK_ROLE_NAME>",
  "executionRoleArn": "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/<YOUR_ECS_TASK_EXECUTION_ROLE_NAME>",
  "containerDefinitions": [
    {
      "name": "blackcard-unsafe",
      "image": "<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/blackcard-unsafe:latest",
      "cpu": 256,
      "memory": 512,
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "<YOUR_AWS_REGION>"
        },
        {
          "name": "BEDROCK_MODEL_ID",
          "value": "anthropic.claude-sonnet-4-5-20250929-v1:0"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/blackcard-unsafe-task",
          "awslogs-region": "<YOUR_AWS_REGION>",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
```

### 6.3 Credit Card Bot Task Definition (`creditcardbot-task.json`)
```json
{
  "family": "creditcardbot-unsafe-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": [
    "FARGATE"
  ],
  "cpu": "256",
  "memory": "512",
  "taskRoleArn": "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/<YOUR_ECS_TASK_ROLE_NAME>",
  "executionRoleArn": "arn:aws:iam::<YOUR_AWS_ACCOUNT_ID>:role/<YOUR_ECS_TASK_EXECUTION_ROLE_NAME>",
  "containerDefinitions": [
    {
      "name": "creditcardbot-unsafe",
      "image": "<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_AWS_REGION>.amazonaws.com/creditcardbot-unsafe:latest",
      "cpu": 256,
      "memory": 512,
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "<YOUR_AWS_REGION>"
        },
        {
          "name": "BEDROCK_MODEL_ID",
          "value": "anthropic.claude-sonnet-4-5-20250929-v1:0"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/creditcardbot-unsafe-task",
          "awslogs-region": "<YOUR_AWS_REGION>",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
```
