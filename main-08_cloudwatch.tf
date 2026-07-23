# ------------------------------------------------------------
# Lambda Log Groups
# ------------------------------------------------------------

resource "aws_cloudwatch_log_group" "app_lambda_logs" {
  for_each = var.function_code_config

  name = "/aws/lambda/${(each.value.function_name)}"

  retention_in_days = 7

  tags = {
    Name        = "${(each.value.function_name)} Lambda Logs"
    Environment = "Lab"
    Project     = "Lambda"
  }

}

resource "aws_cloudwatch_log_group" "detector_lambda_logs" {
  for_each = var.token_detector_function_config

  name = "/aws/lambda/${(each.value.function_name)}"

  retention_in_days = 7

  tags = {
    Name        = "${(each.value.function_name)} Lambda Logs"
    Environment = "Lab"
    Project     = "Lambda"
  }

}

resource "aws_cloudwatch_log_group" "waf_analyzer_lambda_logs" {
  for_each = var.waf_analyzer_function_config

  name = "/aws/lambda/${(each.value.function_name)}"

  retention_in_days = 7

  tags = {
    Name        = "${(each.value.function_name)} Lambda Logs"
    Environment = "Lab"
    Project     = "Lambda"
  }

}

# ------------------------------------------------------------
# WAF Log Group
# ------------------------------------------------------------

resource "aws_cloudwatch_log_group" "waf_logs" {

  name = aws_wafv2_web_acl.api_waf.name

  retention_in_days = 7

  tags = {
    Name        = "WAF Logs"
    Environment = "Lab"
    Project     = "Lambda"
  }

}