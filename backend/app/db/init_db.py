import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.doctor import Department, Doctor
from app.models.user import User
from app.models.pharmacy import Inventory
from app.models.lab_service import LabService
from app.core import security

logger = logging.getLogger(__name__)

async def init_db(db: AsyncSession) -> None:
    """
    Final Production Seeding Engine.
    Ensures all 15 clinical tables are aligned with the enterprise specification.
    """
    # 1. Create Core Departments
    departments = [
        {"name": "Cardiology", "floor": 3, "wing": "A", "building": "Main"},
        {"name": "Pediatrics", "floor": 4, "wing": "C", "building": "Main"},
        {"name": "Orthopedics", "floor": 2, "wing": "B", "building": "Main"},
        {"name": "Emergency", "floor": 0, "wing": "Main", "building": "ER Block"},
        {"name": "Pharmacy", "floor": 0, "wing": "Exit", "building": "Main"}
    ]

    for d in departments:
        res = await db.execute(select(Department).filter(Department.name == d["name"]))
        if not res.scalars().first():
            db.add(Department(**d, phone="+91-111", email=f"{d['name'].lower()}@naviora.ai"))

    # 2. Seed Master Inventory (Pharmacy Module)
    inventory_items = [
        {"name": "Paracetamol 500mg", "category": "Analgesic", "quantity": 1000, "reorder_level": 50, "location": "Shelf A-1"},
        {"name": "Amoxicillin 250mg", "category": "Antibiotic", "quantity": 400, "reorder_level": 20, "location": "Shelf B-2"},
        {"name": "Salbutamol Inhaler", "category": "Respiratory", "quantity": 100, "reorder_level": 10, "location": "Cold Storage"}
    ]

    for item in inventory_items:
        res = await db.execute(select(Inventory).filter(Inventory.name == item["name"]))
        if not res.scalars().first():
            db.add(Inventory(**item))

    # 3. Establish Admin & Staff Stubs
    admin_email = "admin@naviora.ai"
    res = await db.execute(select(User).filter(User.email == admin_email))
    if not res.scalars().first():
        admin = User(
            email=admin_email,
            phone="+910000000000",
            password_hash=security.get_password_hash("NavioraSecure2026!"),
            role="admin",
            is_active=True,
            is_verified=True
        )
        db.add(admin)

    # 4. Seed Lab Services
    lab_tests = [
        {"name": "Complete Blood Count (CBC)", "category": "Hematology", "price": 450.0, "description": "Measures different features of blood"},
        {"name": "Lipid Profile", "category": "Biochemistry", "price": 800.0, "description": "Measures cholesterol levels"},
        {"name": "Fasting Blood Sugar (FBS)", "category": "Biochemistry", "price": 150.0, "description": "Glucose level in blood"},
        {"name": "HbA1c", "category": "Biochemistry", "price": 500.0, "description": "Average blood sugar level"},
        {"name": "Thyroid Profile (T3, T4, TSH)", "category": "Endocrinology", "price": 600.0, "description": "Thyroid function test"},
        {"name": "Liver Function Test (LFT)", "category": "Biochemistry", "price": 750.0, "description": "Measures liver health"},
        {"name": "Kidney Function Test (KFT)", "category": "Biochemistry", "price": 700.0, "description": "Measures kidney health"},
        {"name": "Urine Routine & Microscopy", "category": "Clinical Pathology", "price": 200.0, "description": "Urine analysis"},
        {"name": "X-Ray Chest PA View", "category": "Radiology", "price": 400.0, "description": "Chest X-Ray"},
        {"name": "ECG", "category": "Cardiology", "price": 300.0, "description": "Electrocardiogram"},
        {"name": "Ultrasound Whole Abdomen", "category": "Radiology", "price": 1200.0, "description": "Abdominal ultrasound"},
        {"name": "MRI Brain", "category": "Radiology", "price": 6500.0, "description": "Magnetic Resonance Imaging of Brain"},
        {"name": "CT Scan Head", "category": "Radiology", "price": 3500.0, "description": "Computed Tomography of Head"},
        {"name": "Vitamin D (25-OH)", "category": "Biochemistry", "price": 1500.0, "description": "Vitamin D level"},
        {"name": "Vitamin B12", "category": "Biochemistry", "price": 1000.0, "description": "Vitamin B12 level"},
        {"name": "CRP (C-Reactive Protein)", "category": "Serology", "price": 450.0, "description": "Inflammation marker"},
        {"name": "D-Dimer", "category": "Hematology", "price": 1100.0, "description": "Blood clot marker"},
        {"name": "Serum Ferritin", "category": "Biochemistry", "price": 650.0, "description": "Iron stores in body"},
        {"name": "Serum Calcium", "category": "Biochemistry", "price": 250.0, "description": "Calcium level in blood"},
        {"name": "RT-PCR for COVID-19", "category": "Microbiology", "price": 800.0, "description": "COVID-19 test"}
    ]

    for test in lab_tests:
        res = await db.execute(select(LabService).filter(LabService.name == test["name"]))
        if not res.scalars().first():
            db.add(LabService(**test))

    await db.commit()
    logger.info("Enterprise Clinical Environment Ready.")
