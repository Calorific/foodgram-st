FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip3 install --upgrade pip && pip3 install -r requirements.txt

COPY . .

CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0:8000" ]
