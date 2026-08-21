# Allow the backend ECS agent to inject the configured Stripe credentials into
# the container. Keep this separate from the role's legacy, manually-managed
# SecretsManagerAccess policy so live-secret access remains explicit and
# follows the Terraform Stripe configuration.
data "aws_iam_policy_document" "backend_stripe_secrets" {
  statement {
    sid    = "ReadConfiguredStripeSecrets"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue",
    ]

    resources = compact([
      var.stripe_secret_key_secret_arn,
      var.stripe_webhook_secret_arn,
    ])
  }
}

resource "aws_iam_role_policy" "backend_stripe_secrets" {
  name = "runmypool-backend-stripe-secrets"
  role = element(reverse(split("/", var.execution_role_arn)), 0)

  policy = data.aws_iam_policy_document.backend_stripe_secrets.json
}
