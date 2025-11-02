FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

EXPOSE 9000
ENV PYTHONUNBUFFERED=1

# Запуск Flask backend
CMD ["python", "-m", "app"]
