# ------------------------------------------------------------
# Token DynamoDB Table
# ------------------------------------------------------------

resource "aws_dynamodb_table" "token_dynamodb_table" {
  name         = "token_tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "token_id"

  # allow the below attributes (except the one associated with the hash_key) 
  # are defined to be used within the Dynamodb table, in tis case used in the GSI
  attribute {
    name = "issued_at"
    type = "S"
  }

  attribute {
    name = "token_id"
    type = "S"
  }

  attribute {
    name = "used"
    type = "S"
  }

  # This GSI groups all tokens by their 'used' status.
  # This allows the Detection Lambda to quickly find ALL unused tokens 
  # across ALL users, and sort them chronologically by 'issued_at'.
  global_secondary_index {
    name            = local.dynamodb_gsi_name
    projection_type = "ALL"
    key_schema {
      attribute_name = "used"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "issued_at"
      key_type       = "RANGE"
    }

  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "token-tracking"
    Environment = "Lab"
    Managed_by  = "Terraform"
  }
}


# ------------------------------------------------------------
# WAF Logs DynamoDB Table
# ------------------------------------------------------------

resource "aws_dynamodb_table" "waf_events" {
  name         = "waf-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {

    name = "event_id"
    type = "S"

  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "waf-events"
    Environment = "Lab"
    Project     = "Lambda"
  }

}