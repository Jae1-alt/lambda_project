# ------------------------------------------------
# IAM and Policies
# ------------------------------------------------
variable "managed_policy_arn" {
  description = "A list of ARN's to be used by the role."
  type        = list(string)

  default = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

# Custom Policy for inital AuthZ Lmabda functions (python and node) 
variable "custom_policy" {
  description = "Map to create custom policies, description and file path."
  type = map(object({
    file_path   = string
    description = optional(string)
  }))

  default = {
    lambda-to-dynamodb = {
      file_path   = "0.policies/lambda_to_dynamodb_put.json"
      description = "Policy allowing lambda access to manipulate objects in DynamoDB."
    }
  }
}

# Custom Policy for detection Lmabda function 
variable "custom_detect_policy" {
  description = "Map to create custom policies for detection lambda: description and file path."
  type = map(object({
    file_path   = string
    description = optional(string)
  }))

  default = {
    lambda-to-dynamodb-detect = {
      file_path   = "0.policies/lambda_to_dynamodb.json"
      description = "Policy allowing lambda access to manipulate objects in DynamoDB."
    }

    lambda-invoke-bedrock = {
      file_path   = "0.policies/lambda_to_bedrock_invoke.json"
      description = "Policy allowing lambda to invoke bedrock."
    }
  }
}

# Custom Policy for waf_bedrock_analyzer Lmabda function 
variable "custom_waf_bedrock_analyzer_policy" {
  description = "Map to create custom policies for detection lambda: description and file path."
  type = map(object({
    file_path   = string
    description = optional(string)
  }))

  default = {
    lambda-to-dynamodb-detect = {
      file_path   = "0.policies/lambda_to_dynamodb.json"
      description = "Policy allowing lambda access to manipulate objects in DynamoDB."
    }

    lambda-invoke-bedrock = {
      file_path   = "0.policies/lambda_to_bedrock_invoke.json"
      description = "Policy allowing lambda to invoke bedrock."
    }

    waf-access = {
      file_path   = "0.policies/cw_waf_log_access.json"
      description = "Policy allowing lambda to access waf logs in cloudwatch."
    }
  }
}

# special locals for environmental variables to be used in lambda functions
# where applicable, it will be mereged with the env_value in each lambda config variable, to create Lambda Environmental Variables.
locals {
  env_variables = {
    "DYNAMODB_TABLE_NAME" = aws_dynamodb_table.token_dynamodb_table.name
    "GSI_NAME"            = local.dynamodb_gsi_name
    # "SNS_TOPIC_ARN" = aws_sns_topic.simple_lambda_message.arn
  }

  # security practice, separating environmetal varibales created for the detection lambda
  env_variables_detector = {
    "DYNAMODB_TABLE_NAME" = aws_dynamodb_table.token_dynamodb_table.name
    "GSI_NAME"            = local.dynamodb_gsi_name
    "EXPIRATION_MINUTES"  = "10"
    "BEDROCK_MODEL_ID"    = local.bedrock_model_id
  }

  env_variables_waf_analyzer = {
    "DYNAMODB_TABLE" = aws_dynamodb_table.waf_events.name
    "WAF_LOG_GROUP"  = aws_cloudwatch_log_group.waf_logs.name
    "LOOKBACK_MINUTES" = "10"
    "BEDROCK_MODEL_ID" = local.bedrock_model_id
  }

  # name of the GSI in bedrock
  dynamodb_gsi_name = "Detector_index"

  # model inference ID for LLM model used in Bedrock (passed to python and IAM policy)
  bedrock_model_id = "us.anthropic.claude-opus-4-6-v1"

}

variable "function_code_config" {
  description = "Lmabda function setting with some API config settings."
  type = map(object({
    path        = string
    source      = string
    file_name   = string
    output      = string
    output_path = string

    # function config
    description   = optional(string)
    filename      = string
    function_name = string
    handler       = string
    architecture  = optional(string)
    runtime       = optional(string)

    # environment variables
    env_value = optional(any, {})

    # for API permissions
    statement_id = optional(string)
  }))

  default = {
    python = {
      # code info for fucntion
      path        = "0.function_code/0.combined_functions"
      source      = "python_lambda_v2.py"
      file_name   = "python_lambda_v2"
      output      = "python_lambda_v2.zip"
      output_path = "0.function_code/0.combined_functions/zip_files"

      # function config
      description   = "RBAC Python lambda function."
      filename      = null
      function_name = "python-function-1"
      handler       = "lambda_handler"
      architecture  = "x86_64"
      runtime       = "python3.14"

      # environmental variables
      env_value = {
        # api gateway resourse path
        # place values in lists becuase the function to create the lambda environmental vairbales
        # uses jsonencode to allow for proper passing of values to AWS
        EXPECTED_RESOURCE = "/python"
        ALLOWED_GROUPS    = ["admin", "student"]
      }

      # for API permissions
      statement_id = "AllowAPIGatewayInvokePython"
    }
    node = {
      # code info for fucntion
      path        = "0.function_code/0.combined_functions"
      source      = "node_lambda_v1.js"
      file_name   = "node_lambda_v1"
      output      = "node_lambda_v1.zip"
      output_path = "0.function_code/0.combined_functions/zip_files"

      # function config
      description   = "RBAC Node lambda function."
      filename      = null
      function_name = "node-function-1"
      handler       = "handler"
      architecture  = "x86_64"
      runtime       = "nodejs24.x"

      # environmental variables
      env_value = {
        # api gateway resourse path
        # place values in lists becuase the function to create the lambda environmental vairbales
        # uses jsonencode which will allow for the safe passage of the list in to the python code
        EXPECTED_RESOURCE = "/node"
        ALLOWED_GROUPS    = ["admin"]
      }
      # for this default in the varibale, both blocks must have the same value arguments and types
      # using .tfvars solve this.
      # update, .tfvars doesn't solve this.

      # for API permissions
      statement_id = "AllowAPIGatewayInvokeNode"
    }
  }
}

# varibale for detection lambda
variable "token_detector_function_config" {
  description = "Lmabda function setting with some API config settings."
  type = map(object({
    path        = string
    source      = string
    file_name   = string
    output      = string
    output_path = string

    # function config
    description   = optional(string)
    filename      = string
    function_name = string
    handler       = string
    architecture  = optional(string)
    runtime       = optional(string)
    timeout       = optional(any)

    # environment variables
    env_value = optional(any, {})
  }))

  default = {
    detector = {
      # code info for fucntion
      path        = "0.function_code/0.combined_functions"
      source      = "detection_v3"
      file_name   = "detection_v3"
      output      = "detection_v3.zip"
      output_path = "0.function_code/0.combined_functions/zip_files"

      # function config
      description   = "Python lambda function for Token detection (and adjustment) on DynamoDB table, plus prompt in .txt file."
      filename      = null
      function_name = "token-detection-function-1"
      handler       = "lambda_handler"
      architecture  = "x86_64"
      runtime       = "python3.14"
      timeout       = 60

      # environmental variables
      env_value = {
        EXPIRATION_MINUTES = "10"
      }
    }
  }
}

# varibale for waf bedrock analyzer lambda
variable "waf_analyzer_function_config" {
  description = "Lmabda function config settings."
  type = map(object({
    path        = string
    source      = string
    file_name   = string
    output      = string
    output_path = string

    # function config
    description   = optional(string)
    filename      = string
    function_name = string
    handler       = string
    architecture  = optional(string)
    runtime       = optional(string)
    timeout       = optional(any)

    # environment variables
    env_value = optional(any, {})

  }))

  default = {
    waf-bedrock-analyzer = {
      # code info for fucntion
      path        = "0.function_code/0.combined_functions"
      source      = "waf_bedrock_analyzer"
      file_name   = "waf_bedrock_analyzer_v2"
      output      = "waf_bedrock_analyzer.zip"
      output_path = "0.function_code/0.combined_functions/zip_files"

      # function config
      description   = "Python lambda function for waf log analysis with bedrock on DynamoDB table, plus prompt in .txt file."
      filename      = null
      function_name = "waf-bedrock-analyzer-function-1"
      handler       = "lambda_handler"
      architecture  = "x86_64"
      runtime       = "python3.14"
      timeout       = 60

      # environmental variables
      env_value = {
        EXPIRATION_MINUTES = "10"
      }
    }
  }
}