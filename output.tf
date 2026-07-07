# output "api_urls" {
#   value = {
#     for k, v in var.function_code_config : k => "${aws_apigatewayv2_api.example.api_endpoint}/prod/${k}?name="
#   }
# }

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
  value       = "https://${aws_cognito_user_pool_domain.cognito_pool_login_domain.domain}.auth.${data.aws_region.current.region}.amazoncognito.com/login?response_type=code&client_id=${aws_cognito_user_pool_client.lambda_api_cognito_client.id}&redirect_uri=http://localhost"
}