# CashBook - Financial Tracking Web Application

## Overview

CashBook is a comprehensive multi-user financial tracking web application built with Flask. It provides a complete solution for monitoring income and expenses with advanced features like role-based access control, reporting capabilities, and receipt management. The application supports multiple users with different permission levels and includes features for categorization, tagging, spending limits, and detailed financial reporting in PDF and Excel formats.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templating with Bootstrap 5 for responsive UI
- **CSS Framework**: Bootstrap 5.3.0 with custom CSS for theming and dark mode support
- **JavaScript**: Vanilla JavaScript for theme management, form interactions, and UI enhancements
- **Progressive Web App**: Designed to work as a PWA with offline capabilities
- **Responsive Design**: Mobile-first approach supporting desktop, tablet, and mobile devices

### Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Database Models**: User, Role, Transaction, Category, Tag, Receipt, SpendingLimit, and AuditLog models
- **Authentication**: Flask-Login for session management with role-based access control
- **File Upload**: Werkzeug for secure file handling with receipt attachments
- **Form Handling**: WTForms for form validation and CSRF protection
- **Middleware**: ProxyFix for handling reverse proxy headers

### Data Storage Solutions
- **Primary Database**: SQLite for development with configurable support for PostgreSQL/MySQL
- **File Storage**: Local filesystem for receipt uploads with configurable upload directory
- **Session Management**: Server-side sessions with configurable secret key
- **Database Features**: Connection pooling, automatic reconnection, and migration support

### Authentication and Authorization
- **User Authentication**: Username/password login with remember me functionality
- **Role-Based Access Control**: Three-tier permission system (Admin, Manager, Viewer)
- **Permission System**: Granular permissions for create, read, update, delete, manage_users, reports, and backup operations
- **Password Security**: Werkzeug password hashing with secure random salt generation
- **Session Security**: CSRF protection and secure session configuration

### Application Features
- **Transaction Management**: Income and expense tracking with categorization and tagging
- **Receipt Management**: File upload support for PDF and image receipts
- **Spending Limits**: Configurable spending limits with alert system
- **Reporting System**: PDF and Excel report generation with customizable date ranges
- **Search and Filtering**: Advanced search capabilities across transactions
- **Audit Logging**: Activity tracking for security and compliance
- **Dashboard Analytics**: Real-time financial statistics and spending alerts

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework with extensions for SQLAlchemy and Login management
- **SQLAlchemy**: Database ORM with support for multiple database backends
- **WTForms**: Form handling and validation library
- **Werkzeug**: WSGI utility library for file uploads and security

### Frontend Dependencies
- **Bootstrap 5.3.0**: CSS framework loaded via CDN for responsive design
- **Font Awesome 6.4.0**: Icon library loaded via CDN for UI icons
- **Custom CSS/JS**: Local static files for theme management and application-specific styling

### Report Generation Dependencies
- **ReportLab**: PDF generation library for creating formatted financial reports
- **OpenPyXL**: Excel file generation library for spreadsheet exports

### Database Configuration
- **Default**: SQLite for development and testing
- **Production**: Configurable support for PostgreSQL or MySQL via DATABASE_URL environment variable
- **Connection Management**: Built-in connection pooling and health checking

### Environment Configuration
- **SESSION_SECRET**: Required environment variable for session encryption
- **DATABASE_URL**: Optional environment variable for production database configuration
- **File Upload**: Configurable upload directory with 16MB file size limit

### Security Features
- **CSRF Protection**: Built-in CSRF token validation for all forms
- **File Upload Security**: Restricted file types and secure filename handling
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection attacks
- **XSS Protection**: Jinja2 template auto-escaping prevents cross-site scripting