
# LaborConnect – Skilled Worker Hiring System

## Project Overview

LaborConnect is a web-based skilled worker hiring and service booking system. It connects customers with skilled workers, allowing customers to find services and submit booking requests through an online platform.

The system provides separate dashboards and functionalities for Customers, Skilled Workers (Laborers), and Administrators.

## Main User Roles

### 1. Customer
- Register and log in to the system.
- Search and browse available skilled worker services.
- Filter services based on categories and locations.
- Submit service booking requests.
- View and manage booking requests.
- Submit ratings and reviews for completed services.

### 2. Skilled Worker (Laborer)
- Register and log in as a skilled worker.
- Manage worker profile and service information.
- View customer booking requests.
- Manage booking statuses.
- View customer ratings and reviews.

### 3. Administrator
- Access the administrator dashboard.
- Manage and monitor system information through the admin interface.

## Technologies Used

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python (Flask)
- **Database:** MySQL
- **Template Engine:** Jinja2

## Project Structure

```text
LaborConnect/
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/
│   ├── admin pages
│   ├── customer pages
│   ├── laborer pages
│   └── authentication pages
│
├── app.py
├── config.py
├── database.py
├── create_admin.py
├── requirements.txt
├── smtp_test.py
└── .gitignore
```

## Installation and Setup

### Prerequisites
- Python
- MySQL Server
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/HC-Silva-2003/LaborConnect.git
```

### 2. Navigate to the Project Folder

```bash
cd LaborConnect
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv
```

### 4. Activate the Virtual Environment

Windows:

```bash
.venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a local `.env` file in the project root directory.

Add your own database configuration:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=laborconnect_db
DB_PORT=3306
SECRET_KEY=your_secret_key
```

Use your own local MySQL credentials. Do not upload the `.env` file to GitHub.

### 7. Run the Application

```bash
flask --app app run --debug
```

Open the local URL displayed in the terminal in your web browser.

**Note:** Configure the MySQL database and required tables before running the application.

## Repository

GitHub: https://github.com/HC-Silva-2003/LaborConnect

## Project Information

**Project Name:** LaborConnect  
**Student:** R.L.H. Chathurya Silva  
**Registration Number:** 24IT0531  
**Institute:** Institute of Technology, University of Moratuwa

---

Developed as an academic project.
