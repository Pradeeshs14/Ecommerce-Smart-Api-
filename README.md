# @'

# \# Smart E-Commerce Platform

# 

# A full-stack e-commerce platform built using FastAPI and Django Admin.

# 

# \## Project Overview

# 

# This project provides a complete e-commerce backend with user authentication, product management, cart management, checkout, order processing, Stripe payment integration, notifications, analytics, and report generation.

# 

# The project is divided into:

# 

# \- FastAPI — Backend APIs and business logic

# \- Django Admin — Administration and management panel

# \- SQLite — Database

# \- SQLAlchemy — ORM

# \- Alembic — Database migrations

# \- Stripe — Payment integration

# \- ReportLab — PDF report generation

# \- Postman — API testing

# \- OpenAPI / Swagger — API documentation

# 

# \## Features

# 

# \### User Management

# 

# \- User registration and login

# \- JWT bearer authentication

# \- Access token and refresh token

# \- Current user information

# \- Role-based users

# \- Admin, staff and customer roles

# \- User activation/deactivation

# 

# \### Product Management

# 

# \- Create products

# \- View products

# \- Update products

# \- Delete products

# \- Category-based product filtering

# \- Stock management

# \- Product image upload through Django Admin

# \- Product image preview

# 

# \### Cart Management

# 

# \- Add products to cart

# \- View cart

# \- Update cart quantity

# \- Remove cart items

# \- Cart validation during checkout

# 

# \### Order Management

# 

# \- Checkout

# \- Automatic total calculation

# \- Order creation

# \- Order items

# \- Customer order history

# \- Admin order management

# \- Order status tracking

# 

# \### Payment

# 

# \- Stripe Payment Intent

# \- Stripe Checkout Session

# \- Payment status tracking

# \- Payment database records

# \- Stripe webhook endpoint

# 

# \### Notifications

# 

# \- View user notifications

# \- Mark notifications as read

# 

# \### Analytics Dashboard

# 

# The Django Admin dashboard provides:

# 

# \- Total sales

# \- Total revenue

# \- Revenue trends

# \- Top-selling products

# \- Low-stock product alerts

# 

# \### Reports

# 

# Reports can be exported in:

# 

# \- Orders CSV

# \- Orders PDF

# \- Sales CSV

# \- Sales PDF

# \- Users CSV

# \- Users PDF

# 

# \## API Documentation

# 

# Start the FastAPI server:

# 

# ```bash

# uvicorn app.main:app --reload

