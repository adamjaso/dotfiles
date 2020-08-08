#!/bin/bash
KEY=$1
CRT=$2
[[ ! -f "$KEY" ]] && echo "key not found" && exit 1
[[ ! -f "$CRT" ]] && echo "crt not found" && exit 1
KEYMD5=$(openssl rsa -noout -modulus -in $KEY | openssl md5 | awk '{print$2}')
CRTMD5=$(openssl x509 -noout -modulus -in $CRT | openssl md5 | awk '{print$2}')
echo "Key: $KEYMD5"
echo "Crt: $CRTMD5"
[[ "$KEYMD5" == "$CRTMD5" ]] && (echo "yes" ; exit 0) || (echo "no" ; exit 1)
