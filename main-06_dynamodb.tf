resource "aws_dynamodb_table" "token-dynamodb-table" {
  name         = "token_tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "token_id"

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "token_id"
    type = "S"
  }

  attribute {
    name = "issued_at"
    type = "S"
  }

  attribute {
    name = "used"
    type = "S"
  }

  global_secondary_index {
    name            = "token_secondary_index"
    projection_type = "ALL"
    key_schema {
      attribute_name = "username"
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "used"
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "token_id"
      key_type       = "RANGE"
    }
  }

  tags = {
    Name        = "token-tracking"
    Environment = "Test"
    Managed_by  = "Terraform"
  }
}
