#!/usr/bin/env python3
import os
import sys
import boto3


def main():
    if len(sys.argv[1:]) != 3:
        sys.exit('Usage: {} HTTP_METHOD S3_BUCKET S3_FILENAME'
                 .format(os.path.basename(sys.argv[0])))
        return
    http_method, s3_bucket, s3_filename = sys.argv[1:]
    url = boto3.client('s3').generate_presigned_url(
        Params={'Bucket': s3_bucket, 'Key': s3_filename},
        ClientMethod='{}_object'.format(http_method.lower()),
        HttpMethod=http_method.upper(),
        ExpiresIn=3600)
    print(url)


if __name__ == '__main__':
    main()
