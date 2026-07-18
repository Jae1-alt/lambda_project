# -------------------------------------------------------------------
# Cognito User Pool
# -------------------------------------------------------------------
resource "aws_cognito_user_pool" "lambda_api_cognito_user_pool" {
  name   = "jae-lambda-user-pool"
  region = data.aws_region.current.region

  mfa_configuration = "ON"
  software_token_mfa_configuration {
    enabled = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # this argument tells cognito user pools to automaticlly trigger the verification workflow
  # for users who self-sign-up; i.e. send email to OTP for sign-up etc.
  auto_verified_attributes = ["email"]

  # defines what other aliases, besides "username" can be used to for user sign-in
  alias_attributes = ["email"]

  # this is the schema for user attributes (outlined by OIDC), they are defualts and you can make custom attributes
  # defined because the project required requires user email
  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = true
    required            = true
  }

  password_policy {
    minimum_length    = 8
    require_symbols   = true
    require_numbers   = true
    require_lowercase = true
    require_uppercase = true
  }

  # this config block sets whether only admins can add new user profiles
  admin_create_user_config {
    allow_admin_create_user_only = "true"
  }

  tags = {
    Name        = "lambda-cognito-user-pool"
    Environment = "Test"
    Managed_by  = "Terraform"
  }

}

# App Client ---------------------------------------------
resource "aws_cognito_user_pool_client" "lambda_api_cognito_client" {
  name            = "jae-lambda-client"
  user_pool_id    = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
  region          = data.aws_region.current.region
  generate_secret = false
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true
  callback_urls                        = ["http://localhost/callback"]
  # logout_urls                          = ["https://localhost/logout"]
  supported_identity_providers = ["COGNITO"]

  # token lifetimes and settings
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "hours"
  }
  access_token_validity  = 10
  id_token_validity      = 10
  refresh_token_validity = 1

}


# Cognito Users -----------------------------------------
resource "aws_cognito_user" "lambda_api_cognito_user" {
  for_each = var.lambda_cognito_users

  user_pool_id = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
  username     = var.lambda_cognito_users[each.key].user_name
  password     = var.lambda_cognito_users[each.key].password

  region = data.aws_region.current.region

  # this stes the specific user email and also lets cognito_user auto-verify the email
  attributes = {
    email          = var.lambda_cognito_users[each.key].email
    email_verified = "true"
  }

  message_action = "SUPPRESS"

}

# Cogntio User Groups and Users in Groups -------------------

resource "aws_cognito_user_group" "lambda_cognito_group" {
  for_each = toset(var.lambda_cognito_group)

  user_pool_id = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
  name         = each.key
}

resource "aws_cognito_user_in_group" "example" {
  for_each = local.user_group_map

  user_pool_id = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
  group_name   = aws_cognito_user_group.lambda_cognito_group[each.value.group].name
  username     = aws_cognito_user.lambda_api_cognito_user[each.value.username].username
}

# Cognito User Pool Domain for Login Page -------------------

resource "aws_cognito_user_pool_domain" "cognito_pool_login_domain" {
  # this 'domain' will be the prefix for the FQDN, it must be unique
  domain       = "jae-lambda-portal-876"
  user_pool_id = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
}

# # Manages login branding settings (for login page) for a user pool style and associates it with an app client.
# resource "aws_cognito_managed_login_branding" "cognito_login_page_style" {
#   client_id                   = aws_cognito_user_pool_client.lambda_api_cognito_client.id
#   user_pool_id                = aws_cognito_user_pool.lambda_api_cognito_user_pool.id
#   use_cognito_provided_values = true
# }
