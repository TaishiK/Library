# Library Management System

This project is a Library Management System built using Flask, SQLAlchemy, and PostgreSQL. It provides functionalities for managing books, users, and lending records.

## Project Structure

- **app.py**: The entry point of the application, where the Flask app is created and routes/API endpoints are defined.
- **models.py**: Defines the database models using SQLAlchemy to structure the database tables.
- **book_utils.py**: Contains utility functions related to book management.
- **lent_utils.py**: Contains utility functions related to lending operations.
- **ldap_utils.py**: Contains utility functions for retrieving LDAP user information.
- **requirements.txt**: Lists the dependencies required for the project.
- **Dockerfile**: Contains the configuration to run the application in a Docker container.
- **docker-compose.yml**: Defines multiple Docker containers and manages the services of the application.
- **.env.example**: Provides examples of environment variables needed for application configuration.
- **migrations/**: Directory for storing database migration files (placeholder).
- **static/**: Directory for static files, including thumbnail images and CSS files.
- **templates/**: Directory for HTML template files, containing layouts for various pages of the application.
- **tests/**: Directory containing test code to validate the functionality of the application.
- **README.md**: Documentation that provides an overview and usage instructions for the project.

## Getting Started

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd library
   ```

2. **Set up the environment**:
   - Create a `.env` file based on the `.env.example` file and configure your environment variables.

3. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Run the application**:
   - You can run the application using Docker:
     ```
     docker-compose up
     ```
   - Or run it locally:
     ```
     python app.py
     ```

5. **Access the application**:
   - Open your web browser and go to `http://localhost:5000`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.