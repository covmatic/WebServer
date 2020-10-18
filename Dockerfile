FROM python:3.7-buster

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENV flaskhost=0.0.0.0

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]