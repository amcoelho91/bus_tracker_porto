FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./

# If you don't have package-lock.json yet, npm will create it the first time.
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]