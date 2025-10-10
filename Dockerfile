FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema (para playwright e lxml)
RUN apt-get update && apt-get install -y \
  curl git build-essential libxml2-dev libxslt-dev chromium \
  && rm -rf /var/lib/apt/lists/*

# Copia os arquivos
COPY pyproject.toml uv.lock ./
COPY src ./src

# Instala o uv e dependências do projeto
RUN pip install uv
RUN uv pip install --system --no-cache-dir .

# Instala browsers do Playwright
RUN playwright install --with-deps chromium

EXPOSE 3000

CMD ["uvicorn", "trends.main:app", "--host", "0.0.0.0", "--port", "3000", "--reload", "--reload-dir", "."]
