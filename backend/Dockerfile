FROM python:3.13-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Start the Flask app with Gunicorn (4 workers) on port 7860
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7860", "app:superkart_api"]
