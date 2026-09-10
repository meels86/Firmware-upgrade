#!/usr/bin/env python3
"""Download a single object from S3. Kept separate from the bash wrapper so
credentials/args never pass through a shell heredoc."""
import sys

import boto3


def main() -> None:
    bucket, key, dest = sys.argv[1:4]
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, dest)


if __name__ == "__main__":
    main()
