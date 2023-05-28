mtgstocksclone.com

./docker/ECRupload.sh to build and upload docker image to ECR

./docker/ECStaskstart.sh to start app using latest image on ECR

call python app scripts using python app/*.py --args or scraping scripts scraping/*.py

flask --app app/dashboard.py run --debugger
to run locally

flask db init
flask db migrate -m 'init'
flask db upgrade

stripe listen --forward-to 127.0.0.1:5000/stripe_webhook/

waitress-serve --listen 127.0.0.1:5000 --call 'dashapp:run_app'

docker run -v $HOME/.aws:/.aws --rm -it --entrypoint bash <IMAGE>

docker run -v $HOME/.aws:/.aws <IMAGE>