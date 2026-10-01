import asyncio
import logging
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text

from app.core.config import settings
from app.core import security
from app.db.base_class import Base

# Import all models to ensure metadata registration
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor, Department
from app.models.appointment import Appointment
from app.models.pharmacy import Prescription, Inventory
from app.models.billing import Billing
from app.models.emergency import EmergencyCase
from app.models.tracking import LocationTracking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")


async def seed_data():
    logger.info("=== NAVIORA AI SUPABASE DATABASE SEEDING ENGINE ===")
    
    # 1. Create and align tables on Supabase if not present
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        logger.info("Ensuring schema alignment and creating missing database tables on Supabase...")
        await conn.run_sync(Base.metadata.create_all)
        
        # Schema compatibility migrations for doctors table
        await conn.execute(text("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS years_of_experience INTEGER DEFAULT 5;"))
        await conn.execute(text("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS license_number VARCHAR(50);"))
        await conn.execute(text("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS consultation_fee FLOAT DEFAULT 500.0;"))
        await conn.execute(text("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS avg_consultation_time INTEGER DEFAULT 15;"))
        logger.info("Database tables and columns aligned successfully.")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 2. Seed 6 Departments
        departments = [
            {"name": "Cardiology", "floor": 3, "wing": "A", "building": "Main Block"},
            {"name": "Pediatrics", "floor": 4, "wing": "C", "building": "Main Block"},
            {"name": "Orthopedics", "floor": 2, "wing": "B", "building": "Main Block"},
            {"name": "Emergency", "floor": 0, "wing": "Main", "building": "Emergency Ward"},
            {"name": "Pharmacy", "floor": 0, "wing": "Ground", "building": "Main Block"},
            {"name": "Radiology", "floor": 1, "wing": "D", "building": "Diagnostic Block"},
        ]

        dept_objs = {}
        for d in departments:
            res = await db.execute(select(Department).filter(Department.name == d["name"]))
            dept = res.scalars().first()
            if not dept:
                dept = Department(**d, phone="+91-1800-NAVIORA", email=f"{d['name'].lower()}@naviora.ai")
                db.add(dept)
                await db.flush()
                logger.info(f"Added Department: {d['name']}")
            dept_objs[d["name"]] = dept

        # 3. Seed Admin User
        admin_email = "admin@naviora.ai"
        res = await db.execute(select(User).filter(User.email == admin_email))
        admin = res.scalars().first()
        if not admin:
            admin = User(
                email=admin_email,
                phone="+919999900000",
                password_hash=security.get_password_hash("Admin@123"),
                role="admin",
                is_active=True,
                is_verified=True
            )
            db.add(admin)
            logger.info("Added Admin User: admin@naviora.ai / Admin@123")

        # 4. Seed Doctors
        doctors_data = [
            {
                "first_name": "Arvind",
                "last_name": "Sharma",
                "email": "dr.arvind@naviora.ai",
                "phone": "+919876543210",
                "specialization": "Cardiology",
                "department_name": "Cardiology",
                "license_number": "DOC-CARD-001",
                "years_of_experience": 12,
                "consultation_fee": 800.0,
                "avg_consultation_time": 15
            },
            {
                "first_name": "Priya",
                "last_name": "Patel",
                "email": "dr.priya@naviora.ai",
                "phone": "+919876543211",
                "specialization": "Pediatrics",
                "department_name": "Pediatrics",
                "license_number": "DOC-PED-002",
                "years_of_experience": 8,
                "consultation_fee": 700.0,
                "avg_consultation_time": 12
            }
        ]

        for doc_info in doctors_data:
            res = await db.execute(select(User).filter(User.email == doc_info["email"]))
            user = res.scalars().first()
            if not user:
                user = User(
                    email=doc_info["email"],
                    phone=doc_info["phone"],
                    password_hash=security.get_password_hash("Doctor@123"),
                    role="doctor",
                    is_active=True,
                    is_verified=True
                )
                db.add(user)
                await db.flush()

                dept = dept_objs.get(doc_info["department_name"])
                doc = Doctor(
                    user_id=user.id,
                    department_id=dept.id if dept else None,
                    first_name=doc_info["first_name"],
                    last_name=doc_info["last_name"],
                    specialization=doc_info["specialization"],
                    license_number=doc_info["license_number"],
                    years_of_experience=doc_info["years_of_experience"],
                    is_available=True,
                    avg_consultation_time=doc_info["avg_consultation_time"],
                    max_patients_per_day=30,
                    current_patients=0
                )
                if hasattr(doc, 'consultation_fee'):
                    setattr(doc, 'consultation_fee', doc_info["consultation_fee"])
                db.add(doc)
                logger.info(f"Added Doctor: Dr. {doc_info['first_name']} {doc_info['last_name']}")

        # 5. Seed Patient (John Doe)
        patient_email = "patient@naviora.ai"
        res = await db.execute(select(User).filter(User.email == patient_email))
        p_user = res.scalars().first()
        if not p_user:
            p_user = User(
                email=patient_email,
                phone="+919123456789",
                password_hash=security.get_password_hash("Patient@123"),
                role="patient",
                is_active=True,
                is_verified=True
            )
            db.add(p_user)
            await db.flush()

            import datetime
            patient = Patient(
                user_id=p_user.id,
                first_name="John",
                last_name="Doe",
                date_of_birth=datetime.date(1990, 5, 15),
                gender="Male",
                blood_group="O+",
                emergency_contact="+919888877777",
                emergency_contact_name="Jane Doe",
                allergies=["Penicillin"],
                medical_history="No major prior surgeries. Mild hypertension."
            )
            db.add(patient)
            logger.info("Added Patient Profile: John Doe (patient@naviora.ai)")

        # 6. Seed Pharmacy Inventory
        inventory_items = [
            {"name": "Paracetamol 500mg", "category": "Analgesic", "quantity": 1000, "reorder_level": 50, "location": "Shelf A-1"},
            {"name": "Amoxicillin 250mg", "category": "Antibiotic", "quantity": 400, "reorder_level": 20, "location": "Shelf B-2"},
            {"name": "Cetirizine 10mg", "category": "Antihistamine", "quantity": 500, "reorder_level": 30, "location": "Shelf C-3"},
            {"name": "Salbutamol Inhaler", "category": "Respiratory", "quantity": 100, "reorder_level": 10, "location": "Cold Storage"}
        ]
        for item in inventory_items:
            res = await db.execute(select(Inventory).filter(Inventory.name == item["name"]))
            if not res.scalars().first():
                db.add(Inventory(**item))
                logger.info(f"Added Inventory Item: {item['name']}")

        await db.commit()
        logger.info("[SUCCESS] Supabase Database Seeding Completed Cleanly.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
