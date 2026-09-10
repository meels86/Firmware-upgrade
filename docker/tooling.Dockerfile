# Optional: build and push this image to your GitLab Container Registry to
# speed up pipeline runs by skipping the apt-get install step in every job.
#
#   docker build -t "${CI_REGISTRY_IMAGE}/tooling:latest" -f docker/tooling.Dockerfile .
#   docker push "${CI_REGISTRY_IMAGE}/tooling:latest"
#
# Then in ci/common.yml, point `.base.image` at this image and drop the
# `apt-get`/`pip install` lines from its before_script.
FROM python:3.12-slim

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
       openssh-client sshpass smbclient snmp jq curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir boto3
