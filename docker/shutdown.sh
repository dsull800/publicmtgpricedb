aws sagemaker delete-endpoint --endpoint-name mtgclonepred 
task_data=$(aws ecs list-tasks --cluster mtgclone)
#echo $task_data
echo ${task_data:78:32}
aws ecs stop-task --cluster mtgclone --task ${task_data:78:32}
#aws ecs stop-task --cluster mtgclone --task mtgclone_dashboard