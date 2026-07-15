variable "managed_policy_arn" {
  description = "A list of ARN's to be used by the role."
  type        = list(string)

  default = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  ]
}

# The following variable (along with the fucntions )
variable "custom_policy" {
  description = "Map to create custom policies, including description and file path."
  type = map(object({
    file_path   = string
    description = optional(string)
  }))

  default = {
    lambda-invoke-bedrock = {
      file_path   = "0.policies/lambda_to_bedrock_invoke.json"
      description = "Policy allowing lambda to invoke bedrock."
    }
    lambda-to-dynamodb = {
      file_path   = "0.policies/lambda_to_dynamodb_put.json"
      description = "Policy allowing lambda to put objects in DynamoDB."
    }
  }
}

# special locals for environmental variables to be used in lambda function /
# acts as table that will be searched using the values in the 'env_value' section in the 'function_code_config' variable.
locals {
  env_variables = {
    "DYNAMODB_TABLE_NAME" = aws_dynamodb_table.token_dynamodb_table.name
    # "SNS_TOPIC_ARN" = aws_sns_topic.simple_lambda_message.arn
  }
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
      path        = "0.function_code/2.rbac_functions"
      source      = "python_rbac_v1_5.py"
      file_name   = "python_rbac_v1_5"
      output      = "python_rbac_v1_5.zip"
      output_path = "0.function_code/2.rbac_functions/zip_files"

      # function config
      description   = "RBAC Python lambda function."
      filename      = null
      function_name = "python1_function"
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
      path        = "0.function_code/2.rbac_functions"
      source      = "node_rbac_v1_5.js"
      file_name   = "node_rbac_v1_5"
      output      = "node_rbac_v1_5.zip"
      output_path = "0.function_code/2.rbac_functions/zip_files"

      # function config
      description   = "RBAC Node lambda function."
      filename      = null
      function_name = "node1_function"
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