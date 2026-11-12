FROM node:24-slim@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553

WORKDIR /app
RUN chown node:node /app

# Usuário sem privilégio, que já vem na imagem do Node
USER node

# Versões exatas do package-lock.json, sem rodar scripts de instalação dos pacotes
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Só o que o servidor de desenvolvimento usa
COPY --chown=node:node index.html vite.config.js ./
COPY --chown=node:node public ./public
COPY --chown=node:node src ./src

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
