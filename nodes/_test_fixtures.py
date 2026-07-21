"""Shared nginx config fixtures used across this package's node tests.

SAMPLE_CONFIG is a realistic config exercising every capability this package
covers: nested http/server/location blocks, an upstream block with a
load-balancing method and weighted/backup members, listen decomposition
(bare port + default_server, IPv6 + ssl + http2), all four location
modifiers, SSL config, root, access/error logs, set + variable usages
(including a reference embedded in a larger string), rewrite + two forms of
return, and an include. Expected values below were hand-derived from nginx's
own documented directive grammar (an oracle independent of this package's
implementation), not from running the code and reading off its output.
"""

SAMPLE_CONFIG = """\
user  nginx;
worker_processes  auto;

events {
    worker_connections  1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    upstream backend {
        least_conn;
        server 10.0.0.1:8080 weight=3;
        server 10.0.0.2:8080;
        server 10.0.0.3:8080 backup;
    }

    server {
        listen 80 default_server;
        listen [::]:443 ssl http2;
        server_name example.com www.example.com;

        root /var/www/html;
        access_log /var/log/nginx/access.log combined;
        error_log /var/log/nginx/error.log warn;

        ssl_certificate /etc/ssl/certs/example.crt;
        ssl_certificate_key /etc/ssl/private/example.key;
        ssl_protocols TLSv1.2 TLSv1.3;

        set $upstream_name backend;

        location / {
            try_files $uri $uri/ =404;
        }

        location ~* \\.php$ {
            fastcgi_pass 127.0.0.1:9000;
            fastcgi_index index.php;
        }

        location ^~ /api/ {
            proxy_pass http://$upstream_name;
            proxy_set_header Host $host;
        }

        location = /health {
            return 200 "ok";
        }

        if ($request_method = POST) {
            return 405;
        }

        rewrite ^/old/(.*)$ /new/$1 permanent;
        include /etc/nginx/conf.d/extra.conf;
    }
}
"""

# Missing a ";" after "listen 80" — an unterminated directive. nginx itself
# rejects this at startup ("nginx: [emerg] ... directive is not terminated
# by \";\"" is nginx's own message for exactly this class of error).
MALFORMED_CONFIG = (
    "http {\n"
    "  server {\n"
    "    listen 80\n"
    "    location / {\n"
    "      root /var/www;\n"
    "    }\n"
    "  }\n"
)
