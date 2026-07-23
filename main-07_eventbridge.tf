# -------------------------------------------------------------------
# EventBridge Schedule
#
# Every 5 minutes check for Cognito tokens that
# were issued but never used.
# -------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "unused_token_check" {

  name                = "unused-token-check"
  description         = "Checks for unused Cognito tokens every 5 minutes."
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"

  tags = {
    Name        = "Unused Token Schedule"
    Environment = "Test"
    Project     = "Lambda"
    Managed_by  = "Terraform"
  }

}

# -------------------------------------------------------------------
# EventBridge Target
# -------------------------------------------------------------------

resource "aws_cloudwatch_event_target" "unused_token_target" {
  for_each = var.token_detector_function_config

  rule = aws_cloudwatch_event_rule.unused_token_check.name
  arn  = aws_lambda_function.jae_detection_lambda[each.key].arn

}

# -------------------------------------------------------------------
# Allow EventBridge to Invoke Lambda
# -------------------------------------------------------------------

resource "aws_lambda_permission" "allow_eventbridge" {
  for_each = var.token_detector_function_config

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.jae_detection_lambda[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.unused_token_check.arn

}