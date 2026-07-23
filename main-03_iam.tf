# -------------------------------------------------------------------
# Roles and Policy Document for Application Lambda 
# -------------------------------------------------------------------

# role for authZ lambda  functions
resource "aws_iam_role" "lambda_execution_role" {
  name               = "lambda-authz-project-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Name        = "authz-lambda-role"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

# role for detection lambda function 
resource "aws_iam_role" "lambda_detection_role" {
  name               = "lambda-soar-detection-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Name        = "lambda-detection-role"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

# role for waf-bedrock-analyzer lambda function 
resource "aws_iam_role" "lambda_waf_bedrock_analyzer_role" {
  name               = "lambda-waf-bedrock-analyzer-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Name        = "lambda waf-bedrock-analyzer role"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

# basically will be the inline json polciy code that describes who can assume the role.
# note that this is a data lookup and not a resource because it isn't created in AWS /
# this data source just functions to render the json code to be used by the aws_iam_role resource.
data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# -------------------------------------------------------------------
# AWS Managed Policy & Role Attachment
# -------------------------------------------------------------------

# creates iam role attachments for each ARN in the policy_arn input variable
# each ARN corresponds to an exisitng AWS Managed Policy
resource "aws_iam_role_policy_attachment" "attach_managed_policy" {
  for_each = toset(var.managed_policy_arn)

  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = each.value
}

# attaches the managed policy to the detection role (may have to use different managed roles if needed)
resource "aws_iam_role_policy_attachment" "attach_managed_detection_policy" {
  for_each = toset(var.managed_policy_arn)

  role       = aws_iam_role.lambda_detection_role.name
  policy_arn = each.value
}

# attaches the managed policy to the waf-bedrock-analyzer role (may have to use different managed roles if needed)
resource "aws_iam_role_policy_attachment" "attach_managed_waf_bedrock_policy" {
  for_each = toset(var.managed_policy_arn)

  role       = aws_iam_role.lambda_waf_bedrock_analyzer_role.name
  policy_arn = each.value
}

# -------------------------------------------------------------------
# Custom Policy & Role Attachment for intial AuthZ Lambda
# -------------------------------------------------------------------

# These resources use the 'var.custom_policy' variable to dynamically create
# custom inline policies based on the 'json' files they reference
resource "aws_iam_role_policy" "custom_execution_policy" {
  for_each = var.custom_policy

  name = "${each.key}-json-policy"
  role = aws_iam_role.lambda_execution_role.id

  # The templatefile function reads the external file (referenced in this case). 
  # Passing an empty map {} satisfies the function signature while allowing 
  # future interpolation if dynamic variables are later added to the template. extracted code, using proper interpolation.
  policy = templatefile(
    "${path.module}/${each.value.file_path}",
    {
      region             = data.aws_region.current.region
      account_id         = data.aws_caller_identity.current.account_id
      dynamodb_table_arn = aws_dynamodb_table.token_dynamodb_table.arn
    }
  )
}


# -------------------------------------------------------------------
# Custom Policy & Role Attachements for Detection Role
# -------------------------------------------------------------------

resource "aws_iam_role_policy" "custom_detection_policy" {
  for_each = var.custom_detect_policy

  name = "${each.key}-json-policy"
  role = aws_iam_role.lambda_detection_role.id

  # The templatefile function reads the external file (referenced in this case). 
  # Passing an empty map {} satisfies the function signature while allowing 
  # future interpolation if dynamic variables are later added to the template. extracted code, using proper interpolation.
  policy = templatefile(
    "${path.module}/${each.value.file_path}",
    {
      region             = data.aws_region.current.region
      account_id         = data.aws_caller_identity.current.account_id
      dynamodb_table_arn = aws_dynamodb_table.token_dynamodb_table.arn
      bedrock_model_id   = local.bedrock_model_id
    }
  )
}

# -------------------------------------------------------------------
# Custom Policy & Role Attachements for waf-bedrock-analyzer Role
# -------------------------------------------------------------------

resource "aws_iam_role_policy" "custom_waf_bedrock_analyzer_policy" {
  for_each = var.custom_waf_bedrock_analyzer_policy

  name = "${each.key}-json-policy"
  role = aws_iam_role.lambda_waf_bedrock_analyzer_role.id

  policy = templatefile(
    "${path.module}/${each.value.file_path}",
    {
      region                 = data.aws_region.current.region
      account_id             = data.aws_caller_identity.current.account_id
      dynamodb_table_arn     = aws_dynamodb_table.waf_events.arn
      bedrock_model_id       = local.bedrock_model_id
      waf_cloudwatch_log_arn = aws_cloudwatch_log_group.waf_logs.arn
    }
  )
}
