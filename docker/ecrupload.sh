#!/bin/sh

aws ecr get-login-password \
    --region us-west-2 \
| docker login \
    --username AWS \
    --password-stdin 189091306970.dkr.ecr.us-west-2.amazonaws.com

docker build -t mtgclone_dashboard .

docker tag mtgclone_dashboard 189091306970.dkr.ecr.us-west-2.amazonaws.com/dashboard

docker push 189091306970.dkr.ecr.us-west-2.amazonaws.com/dashboard

docker image rm mtgclone_dashboard 189091306970.dkr.ecr.us-west-2.amazonaws.com/dashboard

