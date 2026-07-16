// Health check script for ECS. Uses Node's http module to avoid
// hostname resolution issues in Fargate awsvpc network mode.
const http = require('http');

const options = {
  socketPath: undefined,
  host: process.env.HOSTNAME || '0.0.0.0',
  port: process.env.PORT || 3000,
  path: '/',
  timeout: 4000,
};

const req = http.request(options, (res) => {
  process.exit(res.statusCode < 400 ? 0 : 1);
});

req.on('error', () => process.exit(1));
req.on('timeout', () => { req.destroy(); process.exit(1); });
req.end();
