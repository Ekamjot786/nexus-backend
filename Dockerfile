FROM python:3.11-slim
RUN apt-get update && apt-get install -y default-libmysqlclient-dev pkg-config gcc && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD exec daphne -b 0.0.0.0 -p ${PORT:-8000} nexus_project.asgi:application
