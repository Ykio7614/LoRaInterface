FROM python:3.11

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/ClientReciever.py"]
