# -------------------------------------------------------------------
# Roles and Policy Document for Application Lambda 
# -------------------------------------------------------------------

# role for authZ lambda  functions
resource "aws_iam_role" "lambda_execution_role" {
  name               = "lambda-soar-project-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Name        = "atuhz-lambda-role"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

# role for detection lambda function 
resource "aws_iam_role" "lambda_detection_role" {
  name               = "lambda-soar-detction-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Name        = "lambda-detection-role"
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

# -------------------------------------------------------------------
# Custom Policy & Role Attachment for intial AuthZ Lambda
# -------------------------------------------------------------------

# These resources use the 'var.custom_policy' variable to dynamically create
# custom policies based on the 'json' files they reference
resource "aws_iam_policy" "custom_policy" {
  for_each = var.custom_policy

  name        = "${each.key}-json-policy"
  description = each.value.description

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

  tags = {
    Name        = "${each.key}-policy"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

resource "aws_iam_role_policy_attachment" "attach_custom_policy" {
  for_each = var.custom_policy

  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.custom_policy[each.key].arn
}

# -------------------------------------------------------------------
# Custom Policy & Role Attachements for Detection Role
# -------------------------------------------------------------------

resource "aws_iam_policy" "custom_detection_policy" {
  for_each = var.custom_detect_policy

  name        = "${each.key}-json-policy"
  description = each.value.description

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

  tags = {
    Name        = "${each.key}-policy"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

resource "aws_iam_role_policy_attachment" "attach_custom_detection_policy" {
  for_each = var.custom_detect_policy

  role       = aws_iam_role.lambda_detection_role.name
  policy_arn = aws_iam_policy.custom_detection_policy[each.key].arn
}