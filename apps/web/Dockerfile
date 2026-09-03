FROM node:22-alpine AS dependencies

WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --force

FROM node:22-alpine AS build

WORKDIR /app

ARG API_PROXY_TARGET=http://127.0.0.1:8000
ENV API_PROXY_TARGET=${API_PROXY_TARGET}

COPY --from=dependencies /app/node_modules ./node_modules
COPY apps/web/ ./
RUN npm run build

FROM node:22-alpine

WORKDIR /app

ENV NODE_ENV=production

COPY --from=build /app ./

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
