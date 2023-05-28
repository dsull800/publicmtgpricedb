aws ecs run-task \
	--cluster mtgclone \
	--count 1 \
	--launch-type "FARGATE" \
	--task-definition mtgclone_dashboard \
	--network-configuration "awsvpcConfiguration={subnets=[subnet-00771b05a42e0a3fd],securityGroups=[sg-09298f0f84d8ead74],assignPublicIp=ENABLED}" \
	--overrides '{"containerOverrides":[{"name":"mtgclone_dashboard"}],"executionRoleArn": "arn:aws:iam::189091306970:role/ecsTaskExecutionRole","taskRoleArn": "arn:aws:iam::189091306970:role/ecsTaskExecutionRole"}'

#--reference-id mtgcloneECStask \