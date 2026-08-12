resource "aws_ses_domain_identity" "runmypool" {
  domain = "runmypool.net"
}

resource "aws_route53_record" "ses_verification" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "_amazonses.runmypool.net"
  type    = "TXT"
  ttl     = 300
  records = [aws_ses_domain_identity.runmypool.verification_token]
}

resource "aws_ses_domain_identity_verification" "runmypool" {
  domain = aws_ses_domain_identity.runmypool.id

  depends_on = [aws_route53_record.ses_verification]
}

resource "aws_ses_domain_dkim" "runmypool" {
  domain = aws_ses_domain_identity.runmypool.domain
}

resource "aws_route53_record" "ses_dkim" {
  count   = 3
  zone_id = aws_route53_zone.main.zone_id
  name    = "${aws_ses_domain_dkim.runmypool.dkim_tokens[count.index]}._domainkey.runmypool.net"
  type    = "CNAME"
  ttl     = 300
  records = ["${aws_ses_domain_dkim.runmypool.dkim_tokens[count.index]}.dkim.amazonses.com"]
}

resource "aws_ses_domain_mail_from" "runmypool" {
  domain           = aws_ses_domain_identity.runmypool.domain
  mail_from_domain = "mail.runmypool.net"
}

resource "aws_route53_record" "ses_mail_from_mx" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "mail.runmypool.net"
  type    = "MX"
  ttl     = 300
  records = ["10 feedback-smtp.${var.aws_region}.amazonses.com"]
}

resource "aws_route53_record" "ses_mail_from_spf" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "mail.runmypool.net"
  type    = "TXT"
  ttl     = 300
  records = ["v=spf1 include:amazonses.com -all"]
}

resource "aws_route53_record" "dmarc" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "_dmarc.runmypool.net"
  type    = "TXT"
  ttl     = 300
  records = ["v=DMARC1; p=none; adkim=s; aspf=s"]
}

resource "aws_iam_role_policy" "backend_ses_send" {
  name = "runmypool-ses-send"
  role = "ecs_task_role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ses:SendEmail"]
      Resource = aws_ses_domain_identity.runmypool.arn
      Condition = {
        StringEquals = {
          "ses:FromAddress" = "accounts@runmypool.net"
        }
      }
    }]
  })
}
