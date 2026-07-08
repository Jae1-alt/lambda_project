
# 🛡️ AWS Serverless RBAC & Authentication Platform

> A living engineering portfolio and Infrastructure-as-Code project documenting the design, implementation, and debugging of a secure, multi-language serverless architecture on AWS.

This project implements a production-ready **Role-Based Access Control (RBAC)** system, layered over **Amazon Cognito authentication**, **API Gateway routing**, and **AWS WAF edge protection**. It features Python and Node.js Lambda functions, Terraform-driven infrastructure, JWT token verification, and an emerging telemetry pipeline for token lifecycle tracking.

---

## 🏛️ System Architecture & Core Principles

### The "Bouncer & Bartender" Paradigm
To conceptualize the division of security responsibilities across the AWS infrastructure, this architecture utilizes a strict separation between Authentication (AuthN) and Authorization (AuthZ):

*   **The Bouncer (API Gateway + Cognito Authorizer):** Handles the heavy cryptographic lifting. It intercepts HTTP requests, verifies the JWT signature against Cognito's public keys (JWKS), and checks expiration. If the token is invalid, it rejects the request immediately with a `401 Unauthorized`. If valid, it passes the request to the compute layer with an enriched payload containing the user's `cognito:groups`.
*   **The Bartender (AWS Lambda):** Receives the enriched event payload and focuses purely on business logic and fine-grained access control. It evaluates the user's groups against the specific route requirements. If the user lacks the required role, it returns a `403 Forbidden`.

### Security & Design Principles

| Principle | Implementation |
| :--- | :--- |
| **Defense in Depth** | Explicit route validation (`event.resource`) combined with group validation inside the Lambda function, operating independently of API Gateway routing. |
| **Least Privilege** | Explicit `Allow` logic. The system defaults to `deny-all`. Access is only granted when identity claims mathematically intersect with route requirements. |
| **Separation of Concerns** | AuthN (Cognito) is decoupled from AuthZ (Lambda). Infrastructure configuration is decoupled from compute code via serialized environment variables. |
| **Enterprise Mapping** | Cognito Groups map to Active Directory Security Groups. Cognito Users map to AD Users. Group Membership maps to Role Assignment. |

---

## 📂 Project Structure

```text
├── 0_Images
│   ├── SMS_MFA-Challenge_Code.png
│   └── Software_Token_MFA-Challenge.png
├── 0_notes
│   ├── 0.Obstacles_Debugging
│   │   ├── 01.Obstacles_passed.md
│   │   └── 02.Obstacles_passed.md
│   └── 1.Project_Documentations
│       ├── 01.Lambda_API-GW_WAF_etc
│       │   └── 01.Part1_API-GW_WAF_etc.md
│       ├── 02.Cognito_Authentication_etc
│       │   ├── 01.Cognito_integration_&_Authentication.md
│       │   ├── 02.Infrastructure_Implementation-Authorizering_Cognito_to_API-GW.md
│       │   ├── 03.Execution_and_Authentication.md
│       │   └── 04.Debugging_&_Edge_Cases.md
│       └── 03.RBAC
│           ├── 01.RBAC_Architectual_Foundations.md
│           ├── 02.Infra_&_Terraform_Quirks.md
│           ├── 03.Compute_Implementation_&_Quirks.md
│           └── 04.Idenity_Verification_&_Debugging.md
├── 0.function_code
│   ├── 1.initial_functions
│   │   ├── chewbacca-node-lambda.js
│   │   ├── chewbacca-python-lambda.py
│   │   └── zip_files
│   │       ├── chewbacca-python-lambda.zip
│   │       └── lambda_node_fucntion.zip
│   └── 2.rbac_functions
│       ├── node_rbac_v1_5.js
│       ├── python_rbac_v1_5.py
│       └── zip_files
│           ├── node_rbac_v1_5.zip
│           └── python_rbac_v1_5.zip
├── 0.policies
│   ├── lambda_to_bedrock_invoke.json
│   ├── lambda_to_dynamodb.json
│   └── waf_role.json
├── 0.python_codes
│   ├── easier_get_token_v2.py
│   ├── flavor_get_token.py
│   ├── token.txt
│   └── verify_groups_v1_5.py
├── 00_variables_0.tf
├── 00_variables_1_cognito_etc.auto.tfvars
├── 00_variables_1_cognito_etc.tf
├── 00.auth.tf
├── 00.data.tf
├── 1.older_codes
│   ├── lambda_function_codes
│   │   ├── node_rbac.js
│   │   ├── python_rbac_v1.py
│   │   ├── python_rbac.py
│   │   └── route_rbac_v1.py
│   └── python_codes
│       ├── easier_get_token_edit1.py
│       ├── easier_get_token_templ.py
│       ├── secret_hash.py
│       └── verify_groups.py
├── main-01_lambda.tf
├── main-02_api_gateways+.tf
├── main-03_iam.tf
├── main-04_waf.tf
├── main-05_cognito+.tf
└── output.tf
```

---

## 🚀 Implementation Phases

### ✅ Phase 1: Core API & Edge Security [Complete]
*   API Gateway routing for multi-language endpoints (`/python`, `/node`).
*   AWS WAF WebACL deployment for edge-layer rate limiting and common exploit protection.
*   Terraform IaC modularization (`main-01` through `main-04`).

### ✅ Phase 2: Identity & Authentication (Cognito) [Complete]
*   Cognito User Pool creation with MFA challenges (SMS & Software Token).
*   JWT token generation, validation, and claim extraction.
*   Discovery of OAuth2 token boundaries: **ID Tokens** (contain `email`, `cognito:username`) vs **Access Tokens** (contain `username`, `scope`, `cognito:groups`).
*   API Gateway Cognito Authorizer mapping to inject claims into Lambda events.

### ✅ Phase 3: Authorization & RBAC Compute Layer [Complete]
*   Refactored Python & Node.js Lambda functions with **Explicit Allow** logic.
*   Environment variable serialization: `jsonencode()` in Terraform mapped to `json.loads()` / `JSON.parse()` in compute.
*   **Terraform "Flattening Engine"**: Nested `for` expressions combined with `flatten()` to map many-to-many user-group relationships.
*   Debugged Terraform literal type unification, Lambda handler dot-notation crashes, and missing standard library imports.

### 🔄 Phase 4: Telemetry & Token Lifecycle [In Progress]
*   DynamoDB `token-tracking` table for single-use token telemetry.
*   `get_token.py` refactored as an Auth Utility and Telemetry Producer.
*   EventBridge Scheduler (`rate(5 minutes)`) triggering the `unused-token-detector` Lambda.
*   CloudWatch alerting for stale/unused tokens.
*   *Next:* Implementing Conditional DynamoDB writes to prevent race-condition replay attacks.

---

## 💡 Engineering Lessons & Debugged Edge Cases

| Challenge | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Terraform Type Unification Crash** | Mixed strings and lists in a `default = {}` block before the type constraint was applied. | Enforced structural parity (e.g., `env_value = {}`) or moved complex configuration to `locals`. |
| **JWT Base64 Decoding Failure** | JWT spec strips `=` padding; Python `base64.urlsafe_b64decode` strictly requires it. | Added padding fix: `payload += '=' * (-len(payload) % 4)` |
| **Terminal `input()` Truncation** | Interactive line buffers limit paste length and confuse bracketed paste modes. | Refactored script to read from `token.txt` via `file.read().strip()` |
| **Lambda Handler Dot Crash** | `python_rbac_v1.5.lambda_handler` caused Python to interpret `.` as a package separator. | Renamed file to `python_rbac_v1_5.py` and updated the handler string. |
| **Missing `email` in Access Tokens** | Access Tokens intentionally exclude PII per the OAuth2 specification. | Enforced ID Token usage for the API Gateway `Authorization` header. |

---

## ⚙️ How to Deploy & Test

**1. Provision Infrastructure:**
```bash
terraform init
terraform plan
terraform apply -auto-approve
```

**2. Generate & Verify Tokens:**
```bash
python 0.python_codes/easier_get_token_v2.py > token.txt
python 0.python_codes/verify_groups_v1_5.py  # Reads token.txt
```

**3. Test RBAC Endpoints:**
```bash
curl -X GET "https://<api-id>.execute-api.<region>.amazonaws.com/prod/python" \
  -H "Authorization: <ID_TOKEN>"
```

---

## 🗺️ Roadmap & Continuous Evolution

- [ ] Implement DynamoDB `ConditionalCheckFailedException` handling for race-condition protection.
- [ ] Enable WAF logging with CloudWatch Resource Policy and header redaction.
- [ ] Replace EventBridge polling with DynamoDB Streams for real-time token detection.
- [ ] Integrate SOAR playbooks for automated threat response.
- [ ] Add Terraform state locking, CI/CD pipeline, and automated security scanning.

> *This README is a living document. As the architecture evolves and new engineering challenges are solved, this file will be updated to reflect the current system state, security posture, and deployment patterns.*

---
**Built with:** Terraform | AWS Lambda | API Gateway | Cognito | DynamoDB | EventBridge | WAF | Python | Node.js  
**Status:** 🟢 Active Development |