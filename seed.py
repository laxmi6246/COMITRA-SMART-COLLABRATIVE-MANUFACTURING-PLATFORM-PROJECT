import os
import datetime
from werkzeug.security import generate_password_hash
from database import db

def seed_database():
    print("[CoMitra Seed] Initializing database schema...")
    db.init_db()

    # Clear existing demo data
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM quality_checks")
    db.execute("DELETE FROM production_updates")
    db.execute("DELETE FROM order_allocations")
    db.execute("DELETE FROM agreements")
    db.execute("DELETE FROM orders")
    db.execute("DELETE FROM businesses")
    db.execute("DELETE FROM users")

    print("[CoMitra Seed] Inserting Demo Users...")
    hashed_pwd = generate_password_hash("demo1234")
    
    # 1. Users
    users = [
        ("owner@comitra.com", hashed_pwd, "Rajesh Sharma (Order Owner)", "owner", None),
        ("partner@comitra.com", hashed_pwd, "Kiran Reddy (Partner - Precision Metal Works)", "partner", 1),
        ("admin@comitra.com", hashed_pwd, "Prof. V. Ramanathan (System Admin)", "admin", None),
    ]
    for u in users:
        db.execute(
            "INSERT INTO users (email, password_hash, name, role, business_id) VALUES (%s, %s, %s, %s, %s)",
            u
        )

    print("[CoMitra Seed] Inserting Manufacturing Businesses with Generous Buffers...")
    # Baseline businesses in Hyderabad / Secunderabad
    businesses = [
        (
            "BIZ-101",
            "Precision Metal Works",
            "CNC Machining & Precision Tooling",
            "5-Axis CNC Milling & Turning Center",
            2500,
            900,  # 500 baseline occupied + 400 allocated to demo order
            1600, # 1,600 available buffer
            "Balanagar Industrial Estate, Hyderabad",
            4.8,
            4.9,
            "contact@precisionmetal.in",
            "+91 98490 11223",
            "Active"
        ),
        (
            "BIZ-102",
            "Apex Manufacturing Solutions",
            "Precision Metal & Aerospace Components",
            "High-Speed CNC Lathe & Milling Machines",
            2000,
            850,  # 500 baseline occupied + 350 allocated to demo order
            1150, # 1,150 available buffer
            "Jeedimetla Phase III, Hyderabad",
            4.6,
            4.7,
            "info@apexmanufacturing.in",
            "+91 98490 22334",
            "Active"
        ),
        (
            "BIZ-103",
            "Unity Engineering Works",
            "Industrial Components Fabrication",
            "CNC Vertical Machining Center",
            1800,
            750,  # 500 baseline occupied + 250 allocated to demo order
            1050, # 1,050 available buffer
            "Sanathnagar Industrial Area, Hyderabad",
            4.5,
            4.6,
            "works@unityengineering.in",
            "+91 98490 33445",
            "Active"
        ),
        (
            "BIZ-104",
            "Rapid Plastic Products",
            "Polymer & Molded Components",
            "Injection Moulding Presses (150T - 400T)",
            3000,
            500,
            2500,
            "Cherlapally IDA, Secunderabad",
            4.7,
            4.8,
            "orders@rapidplastics.in",
            "+91 98490 44556",
            "Active"
        )
    ]
    for b in businesses:
        db.execute(
            """INSERT INTO businesses 
            (business_id, name, category, machinery, total_capacity, occupied_capacity, available_capacity, 
             location, quality_rating, delivery_reliability, contact_email, contact_phone, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            b
        )

    # Fetch inserted business IDs
    b_rows = db.query("SELECT id, business_id FROM businesses ORDER BY id ASC")
    b_map = {row['business_id']: row['id'] for row in b_rows}

    print("[CoMitra Seed] Inserting Live Demonstration Order (Pre-Allocated & In Production)...")
    deadline_date = (datetime.date.today() + datetime.timedelta(days=10)).strftime('%Y-%m-%d')
    db.execute(
        """INSERT INTO orders 
        (order_id, user_id, product_name, category, quantity, required_machinery, 
         min_quality_rating, delivery_deadline, delivery_location, priority, special_instructions, allocated_quantity, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            "ORD-2026-001",
            1,
            "Metal Gear Components",
            "Metal Components",
            1000,
            "CNC Machine",
            4.0,
            deadline_date,
            "Cherlapally Industrial Area, Hyderabad",
            "High",
            "High-precision hardened helical gears (DIN 7 grade). Surface roughness Ra <= 0.8 um. Material: 20MnCr5 Case Hardened Alloy Steel.",
            1000,
            "In Production"
        )
    )

    print("[CoMitra Seed] Inserting Pre-Configured Allocations (400 + 350 + 250 = 1,000)...")
    # Precision Metal Works (400 units, 100 produced)
    alloc1_id = db.execute("""
        INSERT INTO order_allocations 
        (order_id, business_id, allocated_quantity, produced_quantity, approved_quantity, rejected_quantity, invitation_status, production_status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, 'Accepted', 'In Progress', 'Completed initial roughing and CNC helical milling batch.')
    """, ("ORD-2026-001", b_map['BIZ-101'], 400, 100, 100, 0))

    # Apex Manufacturing (350 units)
    alloc2_id = db.execute("""
        INSERT INTO order_allocations 
        (order_id, business_id, allocated_quantity, produced_quantity, approved_quantity, rejected_quantity, invitation_status, production_status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, 'Accepted', 'Not Started', 'Tooling setup and CAD program verification underway.')
    """, ("ORD-2026-001", b_map['BIZ-102'], 350, 0, 0, 0))

    # Unity Engineering (250 units)
    alloc3_id = db.execute("""
        INSERT INTO order_allocations 
        (order_id, business_id, allocated_quantity, produced_quantity, approved_quantity, rejected_quantity, invitation_status, production_status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, 'Accepted', 'Not Started', 'Raw material billet inspection completed.')
    """, ("ORD-2026-001", b_map['BIZ-103'], 250, 0, 0, 0))

    print("[CoMitra Seed] Inserting Production Update Audit Logs...")
    db.execute("""
        INSERT INTO production_updates 
        (allocation_id, order_id, business_id, units_produced, cumulative_produced, status, notes)
        VALUES (%s, %s, %s, %s, %s, 'In Progress', 'Shift A: Precision 5-Axis milling completed for first batch of 100 units.')
    """, (alloc1_id, "ORD-2026-001", b_map['BIZ-101'], 100, 100))

    print("[CoMitra Seed] Inserting Quality Inspection Checklist (Passed Check)...")
    db.execute("""
        INSERT INTO quality_checks 
        (allocation_id, order_id, business_id, inspector_name, dimensions_verified, material_verified, 
         surface_finish_checked, functional_inspection, final_quantity_verified, approved_units, rejected_units, overall_status, inspection_notes)
        VALUES (%s, %s, %s, %s, 1, 1, 1, 1, 1, 100, 0, 'Passed', 'CMM laser inspection passed within +/- 5 um. Case hardening 60 HRC verified.')
    """, (alloc1_id, "ORD-2026-001", b_map['BIZ-101'], "Kiran Reddy (Lead QA)"))

    print("[CoMitra Seed] Inserting Multi-Party Collaborative Agreement...")
    db.execute("""
        INSERT INTO agreements 
        (agreement_id, order_id, title, contract_terms, status)
        VALUES (%s, %s, %s, %s, 'Signed')
    """, (
        "AGR-2026-101",
        "ORD-2026-001",
        "Collaborative Manufacturing Contract for Metal Gear Components",
        "Mutual non-disclosure, IP protection, delivery commitment within 10 days, and ISO-9001 quality warranty terms."
    ))

    print("[CoMitra Seed] Inserting Live Activity Notifications...")
    notifications = [
        (1, "Quality Inspection Passed", "100 units of Metal Gear Components from Precision Metal Works verified & passed 5-point QA.", "qc_passed"),
        (1, "Production Progress Update", "Precision Metal Works reported 100 units produced. Overall progress: 10%.", "production_updated"),
        (1, "Multi-Party Contract Signed", "Agreement AGR-2026-101 executed with Precision, Apex, and Unity.", "agreement_signed"),
        (1, "Order Allocated Successfully", "1,000 units distributed: Precision (400), Apex (350), Unity (250).", "order_allocated"),
        (1, "New Order Published", "Order ORD-2026-001 (1,000 units of Metal Gear Components) posted.", "order_posted")
    ]
    for n in notifications:
        db.execute(
            "INSERT INTO notifications (user_id, title, message, event_type) VALUES (%s, %s, %s, %s)",
            n
        )

    print("[CoMitra Seed] All Demonstration Data Seeded & Live Ready!")

if __name__ == '__main__':
    seed_database()
