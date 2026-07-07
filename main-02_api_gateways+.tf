# -------------------------------------------------------------------
# API Gateway, REST API + 
# -------------------------------------------------------------------

# API Gateway ----------------------------------------
resource "aws_api_gateway_rest_api" "j_rest_api" {
  name        = "sleepy-api"
  description = "terraform built REST API for Lambda integration."

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "sleepy-api-rest-api"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

# API Gateway Resource ----------------------------------------
resource "aws_api_gateway_resource" "rest_api_resource" {
  for_each = var.function_code_config

  parent_id   = aws_api_gateway_rest_api.j_rest_api.root_resource_id
  path_part   = each.key
  rest_api_id = aws_api_gateway_rest_api.j_rest_api.id
}

# Method ----------------------------------------
resource "aws_api_gateway_method" "rest_api_method" {
  for_each = var.function_code_config

  authorizer_id = aws_api_gateway_authorizer.cognito_apigw_lambda_authorizor.id
  authorization = "COGNITO_USER_POOLS"
  http_method   = "GET"
  resource_id   = aws_api_gateway_resource.rest_api_resource[each.key].id
  rest_api_id   = aws_api_gateway_rest_api.j_rest_api.id
}

# Integrations ----------------------------------------
resource "aws_api_gateway_integration" "rest_api_int" {
  for_each = var.function_code_config

  http_method             = aws_api_gateway_method.rest_api_method[each.key].http_method
  resource_id             = aws_api_gateway_resource.rest_api_resource[each.key].id
  rest_api_id             = aws_api_gateway_rest_api.j_rest_api.id
  integration_http_method = "POST" # note that Lambda invokation always require a POST method in the integration layer, usually abstracted away and corrected in Console and with APIv2 resources
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.jae_app_lambda[each.key].invoke_arn
}

# deployment+ stage ----------------------------------------
resource "aws_api_gateway_deployment" "lambda_api_deployment" {
  rest_api_id = aws_api_gateway_rest_api.j_rest_api.id

  triggers = {
    # Force a new deployment when any specified resource changes
    redeployment = sha1(jsonencode([
      [for x in aws_api_gateway_resource.rest_api_resource : x.id],
      [for x in aws_api_gateway_method.rest_api_method : x.id],
      [for x in aws_api_gateway_integration.rest_api_int : x.id],
      aws_api_gateway_authorizer.cognito_apigw_lambda_authorizor.id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.lambda_api_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.j_rest_api.id
  stage_name    = "prod"
}

# Lambda Permissions ----------------------------------------
resource "aws_lambda_permission" "rest_api_lambda" {
  for_each = var.function_code_config

  statement_id  = each.value.statement_id
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.jae_app_lambda[each.key].function_name
  principal     = "apigateway.amazonaws.com"

  # More: http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-control-access-using-iam-policies-to-invoke-api.html
  source_arn = "arn:${data.aws_partition.current.partition}:execute-api:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.j_rest_api.id}/*/*"
}

# -------------------------------------------------------------------
# Autherizers and Authorization 
# -------------------------------------------------------------------

resource "aws_api_gateway_authorizer" "cognito_apigw_lambda_authorizor" {
  name          = "cognito-api-lambda-authorizer"
  rest_api_id   = aws_api_gateway_rest_api.j_rest_api.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [aws_cognito_user_pool.lambda_api_cognito_user_pool.arn]

}
