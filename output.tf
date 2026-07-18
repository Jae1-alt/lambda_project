output "rest_api_urls" {
  description = "Specific API Gateway stage URL's; associated with specific Lambda function."
  value = {
    for k, v in var.function_code_config : k => "${aws_api_gateway_stage.prod.invoke_url}/${k}?name="
  }
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
}

output "cognito_user_pool_client_id" {
  description = "Client ID for the created Cognito User Pool"
  value       = aws_cognito_user_pool_client.lambda_api_cognito_client.id
}

output "cognito_user_login_url" {
  description = "Login URL for Cognito Users"
  value       = "https://${aws_cognito_user_pool_domain.cognito_pool_login_domain.domain}.auth.${data.aws_region.current.region}://{aws_cognito_user_pool_client.lambda_api_cognito_client.id}&response_type=code&scope=email+openid+profile&redirect_uri=${urlencode(one(aws_cognito_user_pool_client.lambda_api_cognito_client.callback_urls))}"
  # value       = "https://${aws_cognito_user_pool_domain.cognito_pool_login_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/login?response_type=code&client_id=${aws_cognito_user_pool_client.lambda_api_cognito_client.id}&redirect_uri=http://localhost"
}

output "dynamodb_table_name" {
  description = "Name of the created DynamoDB Table"
  value       = aws_dynamodb_table.token_dynamodb_table.name
}