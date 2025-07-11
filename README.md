
# Hospital Management System

A modern, comprehensive web application built with Django, HTML5, CSS3, and Bootstrap 5 to streamline and digitize hospital operations. This system empowers healthcare facilities with robust modules for staff, patient, pharmacy, laboratory, billing, and inventory management—all in one secure platform.

---

## 🚀 Key Features

- **Authentication & Role-Based Access**: Secure login for staff with granular permissions.
- **Staff Management**: Register, view, and manage hospital staff profiles.
- **Patient Registration & History**: Register new patients, maintain detailed medical histories, and manage admissions/discharges (including seamless re-admission without duplicate billing).
- **Laboratory Module**: Record, track, and report on lab tests with all required parameters.
- **Prescription & Drug Inventory**: Create/view prescriptions, add/update drugs, monitor stock, and receive out-of-stock alerts.
- **Professional OTC Pharmacy Sales**: Sell over-the-counter drugs, track sales, and generate daily OTC sales reports.
- **Billing & Receipts**: Accurate, automated billing for all services (consultation, drugs, labs, ultrasound, etc.), with downloadable PDF receipts stored for future access.
- **Dashboard**: Modern, actionable dashboards for pharmacy, billing, and more—see stock, prescriptions, OTC sales, and outstanding bills at a glance.
- **Scalable & Extensible**: Modular design for easy extension and integration with future features.

---

## 🛠️ Technologies Used

- **Backend**: Django Web Framework (Python)
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Database**: SQLite (default), easily configurable to PostgreSQL or MySQL
- **Templating**: Django Templating Language

---

## ⚡ Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/arvineee/Hospital-System.git
   cd Hospital-System
   ```
2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```
5. **Create a superuser (admin account)**
   ```bash
   python manage.py createsuperuser
   ```
6. **Run the development server**
   ```bash
   python manage.py runserver
   ```
7. **Access the application**
   - Open your browser and go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 💡 Usage Guide

1. Log in with your staff credentials (create a superuser if needed).
2. Use the dashboard to access modules: Staff, Patients, Lab, Pharmacy, Inventory, Billing.
3. Register new staff or patients, record lab tests, manage drug inventory, and process admissions/discharges.
4. Sell OTC drugs and view sales history from the pharmacy dashboard.
5. Generate and download billing receipts for all patient services.

---

## 🗺️ Roadmap & Planned Features

- Appointment scheduling and calendar integration
- Advanced report generation and analytics dashboard
- Patient portal for appointment and record viewing
- Integration with external pharmacy and insurance APIs
- Mobile-responsive enhancements and PWA support

---

## 🤝 Contributing

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m "Add YourFeature"`)
4. Push to your branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## 📬 Contact

For questions, feedback, or support, open an issue or email: kiruifelix03@gmail.com

