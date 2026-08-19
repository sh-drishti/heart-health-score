# Build the React app, then serve the static output from nginx. nginx also
# reverse-proxies /api to the api container, which keeps the browser
# same-origin.
#
# Built here rather than on the server on purpose: `vite build` under Node
# needs more memory than a 1GB t3.micro comfortably has.

FROM node:22-alpine AS build
WORKDIR /app

# npm ci from the lockfile so the build is reproducible.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_API_BASE is deliberately left unset: nginx serves the API under the same
# origin, so relative /api/v1 paths are correct and no rebuild is needed to
# point at a different host.
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
