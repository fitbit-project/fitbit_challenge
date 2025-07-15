# Stage 1: Build the React application
FROM node:18-alpine AS build
WORKDIR /app

# Copy package.json and install dependencies
COPY package.json ./
COPY package-lock.json ./
RUN npm install

# Copy the rest of the application source code
COPY . ./

# Build the application for production
RUN npm run build

# Stage 2: Serve the application from a lightweight web server
FROM nginx:stable-alpine
WORKDIR /usr/share/nginx/html

# Remove the default Nginx content
RUN rm -rf ./*

# Copy the build output from the build stage
COPY --from=build /app/build .

# Expose port 80 to the outside world
EXPOSE 80

# Nginx will be started automatically by the base image
CMD ["nginx", "-g", "daemon off;"]