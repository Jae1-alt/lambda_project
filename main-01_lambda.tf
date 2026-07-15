# -------------------------------------------------------------------
# Applicaiton Lambda Code Package 
# -------------------------------------------------------------------

# This a unique data resource, converts the code file to a zip file because the AWS API endpoint for 'CreateFunction' expects either /
# Base64-encoded Zip file, and S3 Bucket reference pointing to a .zip file, or a container Image URL.
# Now using a 'for_each' function to iterate over each file outlined in the var.function_code variable
# to create multiple data resources. jae_app_lambda
data "archive_file" "app_lambda_code" {
  for_each = var.function_code_config

  type        = "zip"
  source_file = "${path.module}/${each.value.path}/${each.value.source}"
  output_path = "${path.module}/${each.value.output_path}/${each.value.output}"
}

# -------------------------------------------------------------------
# Application (AuthZ) Lambda Function + 
# -------------------------------------------------------------------
resource "aws_lambda_function" "jae_app_lambda" {
  for_each = var.function_code_config

  filename      = data.archive_file.app_lambda_code[each.key].output_path
  function_name = (each.value.function_name)
  role          = aws_iam_role.lambda_execution_role.arn
  handler       = "${each.value.file_name}.${each.value.handler}" # this is the lambda hanlder that is defined in the code used in the python function
  code_sha256   = data.archive_file.app_lambda_code[each.key].output_base64sha256

  architectures = [each.value.architecture]
  runtime       = (each.value.runtime)

  description = (each.value.description)

  environment {
    # Combines resource-specific vars from the function_code_config variables
    # with global env_variables local values, right-side (locals, takes precedence).
    # Loops through the merged map to convert all data types strictly to strings,
    # as AWS Lambda environment variables do not accept raw primitives/objects.
    # Lists/maps are converted to JSON strings; booleans/numbers become plain strings.
    variables = {
      for k, v in merge(each.value.env_value, local.env_variables) : k => (
        can(tolist(v)) || can(tomap(v)) ? jsonencode(v) : tostring(v)
      )
    }
  }

  tags = {
    Name        = "${each.value.function_name}-lambda-function"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}
