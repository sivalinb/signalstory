FROM python:3.12-slim
WORKDIR /app
COPY requirements*.txt .
ARG REQUIREMENTS=requirements.txt
RUN pip install --no-cache-dir -r ${REQUIREMENTS}
COPY . .
RUN python -c "from scripts.engine_setup import install; install()" && useradd --create-home learner && mkdir -p .runtime && chown -R learner:learner /app
USER learner
EXPOSE 8530
HEALTHCHECK --interval=10s --timeout=3s --start-period=45s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8530/_stcore/health',timeout=2)"
CMD ["python", "-m", "scripts.start"]
