\# Smart E-Commerce Platform

\## Project Documentation



\---



\## 1. Project Overview



The Smart E-Commerce Platform is a full-stack e-commerce application developed using FastAPI and Django Admin.



The FastAPI backend handles REST APIs, authentication, business logic, cart management, checkout, orders, payments, and notifications.



The Django Admin application provides an administrative interface for managing users, products, orders, payments, notifications, analytics, and reports.



\---



\## 2. Project Objectives



The main objectives of the project are:



\- Develop a secure e-commerce backend.

\- Implement user registration and authentication.

\- Implement product and stock management.

\- Implement shopping cart functionality.

\- Implement checkout and order processing.

\- Integrate Stripe payment processing.

\- Provide order and payment status tracking.

\- Provide notification functionality.

\- Provide an administrative management panel.

\- Provide analytics and reporting.

\- Provide API documentation and testing support.



\---



\## 3. Technology Stack



| Technology | Purpose |

|---|---|

| Python | Programming language |

| FastAPI | Backend REST API framework |

| Django | Administration panel |

| SQLAlchemy | ORM / database interaction |

| SQLite | Database |

| Alembic | Database migrations |

| JWT | Authentication |

| Stripe | Payment processing |

| ReportLab | PDF report generation |

| Postman | API testing |

| OpenAPI / Swagger | API documentation |

| Git / GitHub | Version control |



\---



\## 4. System Architecture



The project consists of two major components:



\### FastAPI Backend



Responsible for:



\- REST APIs

\- Authentication

\- User management

\- Product management

\- Cart management

\- Checkout

\- Orders

\- Payments

\- Notifications

\- Business logic



\### Django Admin



Responsible for:



\- User administration

\- Product administration

\- Order administration

\- Payment administration

\- Notification administration

\- Analytics dashboard

\- Report generation



\### Architecture Flow



```text

&#x20;                   Smart E-Commerce Platform

&#x20;                             |

&#x20;               +-------------+-------------+

&#x20;               |                           |

&#x20;         FastAPI Backend              Django Admin

&#x20;               |                           |

&#x20;       REST APIs \& Logic             Administration

&#x20;               |                           |

&#x20;               +-------------+-------------+

&#x20;                             |

&#x20;                        SQLite Database

&#x20;                             |

&#x20;                   +---------+---------+

&#x20;                   |         |         |

&#x20;                 Users    Products   Orders

&#x20;                                     |

&#x20;                                  Payments

&#x20;                                     |

&#x20;                                   Stripe





5\. User Management



The user management module provides:



User registration

User login

JWT authentication

Access token

Refresh token

Current user information

Role-based access

Admin role

Staff role

Customer role

User activation/deactivation



Protected APIs require authentication using a bearer token.



Django Admin allows administrators to view and manage registered users.





7\. Cart Management



The cart module allows customers to:



* Add products to cart
* View cart
* Update product quantity
* Remove cart items
* Validate cart before checkout
* The cart is associated with the authenticated user.



8\. Order Management



The order management module provides:



* Checkout
* Automatic total calculation
* Order creation
* Order items
* Customer order history
* Admin order management
* Order status tracking
* Payment status tracking



The checkout process validates the cart before creating an order.



9\. Checkout Flow



The checkout process follows this flow:



Customer

&#x20;  |

&#x20;  v

Shopping Cart

&#x20;  |

&#x20;  v

Cart Validation

&#x20;  |

&#x20;  v

Calculate Total

&#x20;  |

&#x20;  v

Create Order

&#x20;  |

&#x20;  v

Create Order Items

&#x20;  |

&#x20;  v

Payment Processing

&#x20;  |

&#x20;  v

Payment Status

&#x20;  |

&#x20;  v

Order Status



10\. Stripe Payment Integration



Stripe is integrated into the backend for payment processing.



The payment module supports:



* Stripe Payment Intent
* Stripe Checkout Session
* Payment status tracking
* Payment database records
* Payment intent ID
* Checkout session ID
* Stripe webhook endpoint



The webhook endpoint allows the backend to receive payment events from Stripe and update payment/order information accordingly.



11\. Notifications



The notification module provides:



* User notifications
* Notification listing
* Read/unread status
* Mark notifications as read



12\. Django Admin



Django Admin provides administrative management for:



* Users
* Products
* Orders
* Order Items
* Payments
* Notifications



Administrators can view and manage application data through the Django Admin interface.



13\. Analytics Dashboard



A custom analytics dashboard was implemented in Django.



The dashboard provides:



* Total Sales
* Displays the number of delivered orders.
* Total Revenue
* Calculates revenue from delivered orders.
* Revenue Trends
* Displays revenue based on order dates.
* Top-Selling Products
* Displays products based on total quantity sold.
* Low Stock Products
* Displays products whose stock level is five or below.



14\. Reports



The reporting module provides downloadable reports.



* CSV Reports
* Orders CSV
* Sales CSV
* Users CSV
* PDF Reports
* Orders PDF
* Sales PDF
* Users PDF



PDF reports are generated using ReportLab.



15\. Database



The project uses SQLite as the database.



Main database entities include:



* Users
* Products
* Cart
* Orders
* Order Items
* Payments
* Notifications



SQLAlchemy is used for database interaction in the FastAPI backend.



16\. Database Migrations



Alembic is used to manage database schema migrations.



The project contains:



alembic/

├── env.py

├── script.py.mako

├── README

└── versions/



Migration files allow database schema changes to be tracked and reproduced.



17\. API Documentation



FastAPI automatically generates OpenAPI documentation.



Swagger UI can be accessed using:



http://127.0.0.1:8000/docs



The project also contains:



openapi.json



which contains the generated API specification.



18\. API Endpoints



Major API areas include:



**Authentication**

/auth/register

/auth/login

/auth/refresh

/auth/me



**Products**

/products/

/products/{product\_id}

/products/category/{category}



**Cart**

/cart/

/cart/{cart\_id}



**Orders**

/orders/

/orders/checkout

/orders/admin/all

/orders/admin/{order\_id}/status



**Payments**

/payment/webhook

Notifications

/notifications/

/notifications/read



19\. Postman Testing



A Postman collection was created for API testing.



The project contains:



postman\_collection.json



The collection can be imported into Postman to test the backend APIs.



API testing includes:



* Authentication
* Products
* Cart
* Orders
* Checkout
* Payments
* Notifications



20\. Project Testing



The application was tested using:



* Swagger UI
* Postman
* Django Admin
* Database verification



The major application flows were verified successfully.



21\. Screenshots



Project screenshots are stored in:



Screen shots/



The screenshots include evidence for:



* Previous project tasks
* FastAPI Swagger
* Postman API testing
* Django Admin
* Analytics dashboard
* Reports
* Report downloads





22\. Project Setup

FastAPI Backend



Activate the virtual environment:



.\\venv\\Scripts\\Activate.ps1



Install dependencies:



pip install -r requirements.txt



Run the FastAPI server:



uvicorn app.main:app --reload



Open Swagger:



http://127.0.0.1:8000/docs

Django Admin



Navigate to the Django Admin project:



cd django\_admin



Activate the virtual environment and run:



python manage.py runserver



Open Django Admin:



http://127.0.0.1:8000/admin/



Analytics:



http://127.0.0.1:8000/admin/analytics/



Reports:



http://127.0.0.1:8000/admin/reports/

23\. Security



Sensitive configuration values are stored in environment variables.



The following files/data are excluded from Git:



* .env
* Virtual environment
* Local database files
* Python cache files



Secret API keys should never be committed to the repository.



24\. Version Control



Git and GitHub are used for source code management.



The project repository contains:



* FastAPI source code
* Django Admin source code
* Alembic migrations
* OpenAPI specification
* Postman collection
* README documentation
* Project documentation



25\. Final Project Status



The major project requirements have been implemented and verified.



* User Management
* Authentication
* Product Management
* Product Image Management
* Cart Management
* Checkout
* Order Management
* Stripe Payment Integration
* Payment Status Tracking
* Notifications
* Django Admin
* Analytics Dashboard
* CSV Reports
* PDF Reports
* Database Migrations
* Swagger/OpenAPI Documentation
* Postman Collection
* Project README
* GitHub Version Control



26\. Future Enhancements



Possible future improvements include:



* Customer-facing frontend
* Advanced admin dashboard UI
* Product search
* Product reviews and ratings
* Email notifications
* Advanced sales filtering
* Pagination and sorting
* Production database such as PostgreSQL
* Cloud image storage
* Automated testing
* Deployment to a cloud platform

s

27\. Conclusion



The Smart E-Commerce Platform provides a complete backend and administration solution for an e-commerce application.



FastAPI handles the core APIs and business logic, while Django Admin provides administrative management, analytics, and reporting.



The project also includes authentication, cart and order processing, Stripe payment integration, database migrations, API documentation, Postman testing, and GitHub version control.

