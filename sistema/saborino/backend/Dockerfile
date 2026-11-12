# Imagem base segura e estável
FROM python:3.12-slim-bookworm

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Configurações para Python em Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copia as dependências para dentro do container
COPY requirements.txt .

# Instala as dependências: só pacotes binários, conferidos pelos hashes do requirements.txt
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.txt

# Cria um usuário sem privilégios para segurança
RUN useradd -r django_user

# Dá permissão para esse usuário na pasta do projeto
RUN chown -R django_user:django_user /app

# Troca para o usuário seguro
USER django_user

# Comando padrão (vamos ajustar isso melhor depois, mas serve por enquanto)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
