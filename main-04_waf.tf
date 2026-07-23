# -------------------------------------------------------------------
# AWS WAF + 
# -------------------------------------------------------------------
resource "aws_wafv2_web_acl" "api_waf" {
  name  = "aws-waf-logs-api-1"
  scope = "REGIONAL"
  default_action {
    allow {}
  }

  rule {
    name     = "AWSCommonRules"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    # XSS = "AWSManagedRulesCommonRuleSet" (already added)
    # SQL = "AWSManagedRulesSQLiRuleSet"

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "XSScommonRules"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "api-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Name        = "api-waf"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}

# WAF Rule Attachments ---------------------------------------------------------

resource "aws_wafv2_web_acl_rule" "rate_limit_web_acl_rule" {
  name        = "rate-limit-rule"
  priority    = 2
  web_acl_arn = aws_wafv2_web_acl.api_waf.arn

  action {
    block {}
  }

  statement {
    rate_based_statement {
      limit                 = 10
      aggregate_key_type    = "IP"
      evaluation_window_sec = 300
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "rate-limit"
    sampled_requests_enabled   = true
  }
}

# Attach WAF API Gateway ----------------------------------------

# for the resource_arn in the below WAF Web ACL association the format should be:
# "arn:partition:apigateway:region::/restapis/api-id/stages/stage-name"
# Doc: https://docs.aws.amazon.com/waf/latest/APIReference/API_AssociateWebACL.html

resource "aws_wafv2_web_acl_association" "api_assoc" {
  resource_arn = "arn:aws:apigateway:${data.aws_region.current.region}::/restapis/${aws_api_gateway_rest_api.j_rest_api.id}/stages/${aws_api_gateway_stage.prod.stage_name}"
  web_acl_arn  = aws_wafv2_web_acl.api_waf.arn

  depends_on = [
    aws_api_gateway_stage.prod
  ]
}

# also note that waf acl - api association can only be done with a rest api
# Doc: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_web_acl_association

# WAF Logging Configuration ------------------------------------------

resource "aws_wafv2_web_acl_logging_configuration" "logging" {

  log_destination_configs = [
    aws_cloudwatch_log_group.waf_logs.arn
  ]

  resource_arn = aws_wafv2_web_acl.api_waf.arn
}