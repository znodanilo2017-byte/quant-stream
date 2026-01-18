FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc
# specific requirements for processor if you haven't made a file, 
# but usually we assume a requirements.txt exists. 
# Let's assume you copy the one from dashboard or create one.
# For safety, let's just install inline to be sure:
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
COPY model_v2.pkl .
CMD ["python", "-u", "main.py"]
