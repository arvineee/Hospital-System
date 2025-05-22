Hospital Management System

A comprehensive web application developed using Django, HTML, CSS, and Bootstrap to streamline hospital operations. This system provides functionality for staff and patient management, laboratory operations, medical histories, prescriptions, billing, and inventory control.

Features

Authentication System: Secure login and role-based access control for staff members.

Staff Registration: Add, view, and manage hospital staff profiles.

Patient Registration: Register new patients with personal and medical details.

Laboratory Module: Record and track lab tests with all required parameters.

Patient History & Diagnosis: Maintain detailed medical histories and diagnoses.

Prescription Management: Create and view prescriptions for patients.

Drug Inventory: Add new drugs, update stock levels, and monitor inventory.

Patient Admission & Discharge: Discharge and readmit patients without re-registration.

Auto Bill Receipt Generator: Automatically generate billing receipts based on services rendered.

Scalable Architecture: Designed for easy extension with more features planned.


Technologies Used

Backend: Django Web Framework (Python)

Frontend: HTML5, CSS3, Bootstrap 5

Database: Easily configurable to PostgreSQL or MySQL

Templates: Django Templating Language


Installation

1. Clone the repository

git clone https://github.com/arvineee/Hospital-System.git
cd Hospital-System


2. Create and activate a virtual environment

python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate


3. Install dependencies

pip install -r requirements.txt


4. Apply database migrations

python manage.py migrate


5. Create a superuser (admin account)

python manage.py createsuperuser


6. Run the development server

python manage.py runserver


7. Access the application

Open your browser and navigate to http://127.0.0.1:8000/.


Usage

1. Create superuser and Log in with your staff credentials.


2. Navigate to the dashboard to access modules: Staff, Patients, Lab, Inventory, Billing.


3. Register new staff or patients via their respective sections.


4. Record lab tests and view results in the Lab module.


5. Manage drug inventory: add new drugs or update stock.


6. Discharge/Readmit patients seamlessly from the Patients module.


7. Generate invoices automatically after patient services.



Roadmap & Future Features

Appointment scheduling and calendar integration

Report generation and analytics dashboard

Patient portal for appointment and record viewing

Integration with external pharmacy and insurance APIs

Mobile-responsive enhancements and PWA support


Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository


2. Create a feature branch (git checkout -b feature/YourFeature)


3. Commit your changes (git commit -m "Add YourFeature")


4. Push to the branch (git push origin feature/YourFeature)


5. Open a Pull Request



License

This project is licensed under the MIT License. See the LICENSE file for details.

Contact

For questions or feedback, open an issue or reach out to kiruifelix03@gmail.com

