FROM node:22-alpine AS build

WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Browser-facing API base URL (host port mapping of the backend service).
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build && npm prune --omit=dev

FROM node:22-alpine

WORKDIR /srv/oscar-ui
COPY --from=build /src/build ./build
COPY --from=build /src/node_modules ./node_modules
COPY --from=build /src/package.json ./

ENV PORT=3000
EXPOSE 3000
CMD ["node", "build"]
