# ==============================================================================
# RunMyPool — Application Load Balancer
#
# Single ALB handling both frontend and backend:
#   - Port 80  → HTTP redirect to HTTPS
#   - Port 443 → HTTPS (TLS terminated at ALB)
#     - /api/* and /docs* → backend target group (port 8000)
#     - /*              → frontend target group (port 3000)
# ==============================================================================

locals {
  cert_arn = "arn:aws:acm:us-east-1:739444271939:certificate/d5fbd3ce-bfa8-4ca8-b6ba-0384b8674bd8"
}

# ──────────────────────────────────────────────────────────────────────────────
# ALB
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_lb" "main" {
  name               = "run-my-pool-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  enable_deletion_protection = false

  tags = {
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Target Groups
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_lb_target_group" "backend" {
  name        = "runmypool-backend-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }

  tags = {
    Project = "runmypool"
  }
}

resource "aws_lb_target_group" "frontend" {
  name        = "runmypool-frontend-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200,301,302"
  }

  tags = {
    Project = "runmypool"
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Listeners
# ──────────────────────────────────────────────────────────────────────────────

# HTTP → HTTPS redirect
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS — default to frontend, route /api/* to backend
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = local.cert_arn

  # Default: frontend
  default_action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.frontend.arn
        weight = 1
      }

    }
  }

  lifecycle {
    # AWS reports the forward target in both the legacy target_group_arn field
    # and the forward block, which otherwise creates perpetual plan drift.
    ignore_changes = [default_action]
  }
}

# Route API paths to backend — split across two rules (ALB limit: 5 values per condition)
resource "aws_lb_listener_rule" "backend_api_1" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  condition {
    path_pattern {
      values = ["/api/*", "/auth/*", "/pools/*", "/entries/*", "/picks/*"]
    }
  }

  action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.backend.arn
        weight = 1
      }

    }
  }
}

resource "aws_lb_listener_rule" "backend_api_2" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 11

  condition {
    path_pattern {
      # Keep frontend pages such as /admin/league/{id} on the frontend target.
      # Every backend admin route is namespaced under /admin/pools/.
      values = ["/users/*", "/admin/pools/*", "/schedule/*", "/teams/*", "/rules/*"]
    }
  }

  action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.backend.arn
        weight = 1
      }

    }
  }
}

resource "aws_lb_listener_rule" "backend_api_3" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 12

  condition {
    path_pattern {
      values = ["/messages/*", "/audit/*", "/health", "/docs", "/openapi.json"]
    }
  }

  action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.backend.arn
        weight = 1
      }

    }
  }
}

resource "aws_lb_listener_rule" "backend_api_4" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 14

  condition {
    path_pattern {
      values = ["/billing/*"]
    }
  }

  action {
    type = "forward"

    forward {
      target_group {
        arn    = aws_lb_target_group.backend.arn
        weight = 1
      }

    }
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Route 53
# ──────────────────────────────────────────────────────────────────────────────

resource "aws_route53_zone" "main" {
  name = "runmypool.net"

  tags = {
    Project = "runmypool"
  }
}

# runmypool.net → ALB
resource "aws_route53_record" "apex" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "runmypool.net"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = false
  }
}

# www.runmypool.net → ALB
resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.runmypool.net"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = false
  }
}
