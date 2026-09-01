# 🛡️ Campus Guardian

### AI-Powered Campus Entry Verification System

Campus Guardian is an AI-powered smart campus security system designed to automate and secure the entry and exit process of educational institutions.

The system uses **Computer Vision, YOLO, OCR, and database verification** to identify vehicles, detect and read vehicle number plates, and verify whether the vehicle is registered with the college.

---

## 🚀 Problem Statement

Traditional college gate-entry systems often depend on manual verification by security guards. This can lead to:

* ⏳ Long verification time during peak hours
* ❌ Human errors in checking vehicle details
* 📝 Manual maintenance of entry records
* 🚨 Difficulty identifying unauthorized vehicles
* 🔍 Limited real-time monitoring and alerts

Campus Guardian aims to replace this manual process with an intelligent and automated verification system.

---

## 💡 Our Solution

Campus Guardian provides an integrated platform that:

1. 🚗 **Detects vehicles** using YOLO-based computer vision.
2. 🔎 **Detects vehicle number plates** from captured images/video.
3. 🔤 **Extracts number plates using OCR**.
4. 🗄️ **Verifies vehicle details** against the college database.
5. 🚨 **Generates alerts** for unauthorized or blocked vehicles.
6. 📊 **Maintains entry logs and verification history** for security monitoring.

---

## ✨ Key Features

### 🚗 Vehicle Detection

Detects different vehicle types such as:

* Car
* Bike
* Scooty
* Activa

The detection pipeline is powered by **YOLO**.

### 🔤 Number Plate Recognition

The system detects the vehicle's number plate and uses **OCR (Optical Character Recognition)** to extract the registration number.

Example:

```text
Detected Plate → MP07AB1234
```

### 🗄️ Vehicle Database Verification

The extracted vehicle number is compared with registered vehicle records.

```text
MP07AB1234
       ↓
Database Verification
       ↓
Registered?
   ↙        ↘
 YES        NO
 ↓           ↓
ALLOW      ALERT
```

### 🚨 Unauthorized Vehicle Alerts

If a vehicle is not registered or appears in the blocklist, the system can generate a security alert for the gate staff.

### 👤 Student & Vehicle Management

Security/admin users can view:

* Student information
* Registered vehicles
* Vehicle owners
* Registration numbers
* Blocklisted vehicles

### 📋 Entry & Verification Logs

The system maintains records of campus entry activity, including:

* Vehicle number
* Vehicle type
* Verification result
* Date & time
* Gate
* Owner information

### 📹 Live Gate Monitoring

The dashboard provides a centralized view of gate activity and verification results.

---

## 🏗️ System Architecture

```text
                 📹 CCTV / Camera
                       │
                       ▼
              ┌─────────────────┐
              │  Vehicle Input  │
              └────────┬────────┘
                       │
                       ▼
                ┌─────────────┐
                │    YOLO     │
                │    Model    │
                └──────┬──────┘
                       │
                Vehicle Detection
                       │
                       ▼
             ┌──────────────────┐
             │ Number Plate     │
             │ Detection        │
             └────────┬─────────┘
                      │
                      ▼
                ┌───────────┐
                │    OCR    │
                └─────┬─────┘
                      │
                Plate Number
                      │
                      ▼
             ┌─────────────────┐
             │ College Database│
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Verification    │
             │ & Rule Engine   │
             └────────┬────────┘
                      │
              ┌───────┴────────┐
              ▼                ▼
          ✅ VERIFIED       🚨 ALERT
              │                │
              └───────┬────────┘
                      ▼
                📊 Dashboard
```

---

## 🧠 AI Pipeline

Campus Guardian uses the following computer vision pipeline:

```text
Input Image / Video
        ↓
Vehicle Detection
        ↓
Number Plate Detection
        ↓
Image Preprocessing
        ↓
OCR
        ↓
Plate Number
        ↓
Database Matching
        ↓
Verification Result
```

### YOLO

YOLO is used for real-time object detection.

Current vehicle classes include:

* `car`
* `bike`
* `scooty`

The model can be further extended with additional vehicle classes.

### OCR

OCR is used to convert the characters present on a vehicle number plate into machine-readable text.

---

## 🛠️ Technology Stack

### Frontend

* React.js
* JavaScript
* HTML5
* CSS3
* Vite
* Chart.js

### Backend

* Node.js
* Express.js
* REST API

### AI / Computer Vision

* Python
* YOLO
* OpenCV
* OCR
* Computer Vision

### Database

* MySQL / SQL Database

### Development Tools

* VS Code
* Git
* GitHub
* Google Colab
* Roboflow
* Label Studio

---

## 📁 Project Structure

```text
Campus-Guardian/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── routes/
│   ├── controllers/
│   ├── models/
│   ├── middleware/
│   ├── server.js
│   └── package.json
│
├── ai/
│   ├── models/
│   ├── datasets/
│   ├── detection/
│   ├── ocr/
│   └── ...
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/
│
├── .gitignore
└── README.md
```

> The exact folder structure may vary depending on the implementation.

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/Campus-Guardian.git
cd Campus-Guardian
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

Start the frontend:

```bash
npm run dev
```

### 3. Install Backend Dependencies

Open another terminal:

```bash
cd backend
npm install
```

Start the backend:

```bash
npm run dev
```

or:

```bash
node server.js
```

### 4. Setup AI Environment

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file inside the backend directory.

Example:

```env
PORT=5000
DATABASE_URL=your_database_connection
JWT_SECRET=your_secret_key
```

⚠️ **Do not upload your `.env` file or API keys to GitHub.**

Add it to `.gitignore`:

```text
.env
node_modules/
venv/
__pycache__/
```

---

## 📊 Dashboard Modules

The system contains different modules for campus security management.

### Security Dashboard

Provides an overview of:

* Total entries
* Verified vehicles
* Unauthorized attempts
* Active alerts
* Gate activity

### Vehicle Management

Allows authorized users to manage:

* Registered vehicles
* Vehicle owners
* Registration numbers
* Blocklisted vehicles

### Current Verification

Displays the latest vehicle verification result.

```text
Vehicle Detected
       ↓
Plate: MP07AB1234
       ↓
Database Match
       ↓
✅ VERIFIED
```

### Recent Alerts

Shows suspicious or unauthorized entry attempts.

### Entry Logs

Maintains an auditable record of campus entries and verification results.

---

## 🔒 Security

Campus Guardian is designed with security and accountability in mind.

Important security considerations include:

* Role-based access
* Authentication
* Database validation
* Verification logs
* Unauthorized vehicle alerts
* Protected environment variables
* Audit history

---

## 🎯 Future Scope

The project can be further enhanced with:

* 👤 Face recognition for student/staff verification
* 📱 Mobile application for security staff
* 📹 Multiple CCTV camera integration
* 🔔 Real-time notifications
* 🧠 Improved AI-based anomaly detection
* 🏫 Multi-gate campus management
* ☁️ Cloud deployment
* 📈 Advanced security analytics
* 🎫 QR/College ID verification
* 🚘 Automatic barrier/gate integration

---

## 🌟 Advantages

### Security

Automated verification can help identify unauthorized vehicles quickly.

### Efficiency

Reduces the time required for manual vehicle verification.

### Accuracy

Computer vision and OCR reduce dependence on manual data entry.

### Monitoring

Provides centralized visibility of campus gate activity.

### Record Keeping

Maintains digital verification and entry history.

---

## 📸 Screenshots

Add screenshots of your application here:

```text
docs/
├── dashboard.png
├── vehicle-management.png
├── verification.png
├── alerts.png
└── entry-logs.png
```

Example:

![Dashboard](docs/dashboard.png)

---

## 👩‍💻 Team

**Campus Guardian Team**

Developed as a college project at:

**Madhav Institute of Technology & Science (MITS), Gwalior**

---

## 📜 Project Status

🚧 **Currently under development**

The project is being developed as an AI-powered smart campus security solution with vehicle detection, number plate recognition, OCR-based verification, database integration, and security monitoring.

---

## ⭐ Support

If you find this project useful, consider giving the repository a ⭐ on GitHub.

---

### 🛡️ Campus Guardian

**Smarter Entry. Safer Campus.**
