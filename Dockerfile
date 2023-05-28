FROM --platform=linux/amd64 python:3.11.1-slim
# FROM --platform=linux/arm64/v8 python:3.11.1-slim
COPY requirements.txt /tmp/
WORKDIR /project
RUN mkdir /project/runtime_data
# ENV PATH="$PATH:/project"
# ENV PATH="$PATH:$(pwd)"
COPY ./app /project/app
COPY ./creds /project/creds
COPY ./scripts /project/scripts
COPY ./config.py config.py
COPY ./dashapp.py dashapp.py
COPY .env.production .env
RUN pip install --no-deps -r /tmp/requirements.txt
# RUN cd project
ENTRYPOINT [ "waitress-serve", "--listen", "0.0.0.0:80", "--url-scheme", "https", "--call", "dashapp:run_app" ]
# CMD [ "waitress-serve", "--call dashapp:run_app"]
