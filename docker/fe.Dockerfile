FROM node:18-alpine

WORKDIR /app

COPY 2-junsu-community-fe/package*.json ./
RUN npm ci --omit=dev

COPY 2-junsu-community-fe/ ./

EXPOSE 3000

ENV PORT=3000
ENV BACKEND_TARGET=http://be:8000

CMD ["npm", "start"]
