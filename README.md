# Hospital Management Dashboard

This project is a Streamlit-based Hospital Management Dashboard designed to manage hospital operations efficiently while ensuring compliance with GDPR requirements. The application provides functionalities for managing patient records, appointments, staff information, and more.

## Features

- **User Authentication**: Secure login system with role-based access control (RBAC).
- **Patient Management**: View, add, and anonymize patient records.
- **Appointment Scheduling**: Manage appointments with patients.
- **Staff Management**: Maintain staff records and roles.
- **Dashboard**: Visual representation of system status and user activity.
- **GDPR Compliance**: Tools for data retention and user consent management.

## Project Structure

```
hospital-management-dashboard
├── src
│   ├── main.py               # Entry point for the Streamlit application
│   ├── app.py                # Main application logic and user authentication
│   ├── config.py             # Configuration settings
│   ├── database
│   │   ├── __init__.py       # Initializes the database module
│   │   ├── connection.py      # Manages database connections
│   │   └── models.py         # Defines database schema
│   ├── pages
│   │   ├── __init__.py       # Initializes the pages module
│   │   ├── dashboard.py       # Main dashboard view
│   │   ├── patients.py        # Patient records management
│   │   ├── appointments.py     # Appointment management
│   │   └── staff.py           # Staff records management
│   ├── utils
│   │   ├── __init__.py       # Initializes the utilities module
│   │   ├── auth.py           # User authentication functions
│   │   ├── encryption.py      # Data encryption and anonymization
│   │   └── gdpr.py           # GDPR compliance functions
│   └── components
│       ├── __init__.py       # Initializes the components module
│       └── charts.py         # Functions for generating visualizations
├── requirements.txt           # Project dependencies
├── .env.example               # Example environment variables
└── README.md                  # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd hospital-management-dashboard
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up the environment variables by copying `.env.example` to `.env` and filling in the necessary details.

4. Run the application:
   ```
   streamlit run src/main.py
   ```

## Usage

- Access the application through the web browser at the provided local URL.
- Log in using your credentials to access different functionalities based on your role.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.