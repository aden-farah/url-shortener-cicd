# URL Shortener

A simple URL shortener built with FastAPI, PostgreSQL and Docker.

The goal of this project is to learn more about backend development, databases, containers and eventually deploying an application to Azure.

## Current Features

The project currently includes:

- FastAPI backend
- PostgreSQL database
- Docker Compose for running the application and database
- SQLAlchemy for database communication
- Generate short codes for long URLs
- Redirect short URLs to the original URL
- Click counter for shortened links
- Store created links in PostgreSQL
- Persistent database storage using Docker volumes
- Basic frontend using HTML, CSS and Jinja2
- Health endpoint for checking if the application is running

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Docker
- Docker Compose
- HTML / CSS
- Jinja2

## Current Status

The main functionality of the URL shortener is working locally.

Users can create a shortened URL, use the generated short link and be redirected to the original website. The links are stored in PostgreSQL and remain available after restarting the containers.

The project is still in development and I am continuing to improve it while learning more about deployment and CI/CD.

## Planned Improvements

Some of the next things I want to add are:

- Create a production-ready Docker image
- Add GitHub Actions for CI/CD
- Push the Docker image to a container registry
- Deploy the application to Microsoft Azure
- Use Azure Monitor / Application Insights for monitoring
- Improve error handling and validation
- Add more testing
- Improve the frontend
- Add basic security improvements
- Add a custom domain if the application is deployed publicly

## Why I Built This

I started this project to get more hands-on experience with how a backend application works together with a database and Docker.

I also wanted to build something that I could later take further with cloud deployment, CI/CD and monitoring instead of only running it locally.

## Project Status

🚧 Work in progress

The core application works locally, but deployment, CI/CD, monitoring and some improvements are still planned.
