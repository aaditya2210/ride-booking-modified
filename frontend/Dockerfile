FROM node:18-alpine as build

WORKDIR /app

COPY frontend/package.json .
RUN npm install --legacy-peer-deps

COPY frontend/ .
ENV REACT_APP_API_URL=http://localhost:8080
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY frontend/nginx-frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
