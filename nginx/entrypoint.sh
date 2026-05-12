#!/bin/sh
set -e

# 开发环境自签名证书
if [ ! -f /etc/nginx/ssl/fullchain.pem ]; then
    mkdir -p /etc/nginx/ssl
    apk add --no-cache openssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/privkey.pem \
        -out /etc/nginx/ssl/fullchain.pem \
        -subj "/CN=know-flow.dev"
    echo "已生成自签名开发证书"
fi

exec nginx -g "daemon off;"
