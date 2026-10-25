-- CoMitra Database Schema
-- Compatible with MySQL and SQLite

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(191) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'owner', 'partner', 'admin'
    business_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    business_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    machinery VARCHAR(255) NOT NULL,
    total_capacity INTEGER NOT NULL DEFAULT 0,
    occupied_capacity INTEGER NOT NULL DEFAULT 0,
    available_capacity INTEGER NOT NULL DEFAULT 0,
    location VARCHAR(150) NOT NULL,
    quality_rating DECIMAL(3, 2) NOT NULL DEFAULT 4.0,
    delivery_reliability DECIMAL(3, 2) NOT NULL DEFAULT 4.5,
    contact_email VARCHAR(150),
    contact_phone VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'Active', -- 'Active', 'Inactive'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    required_machinery VARCHAR(150) NOT NULL,
    min_quality_rating DECIMAL(3, 2) NOT NULL DEFAULT 4.0,
    delivery_deadline DATE NOT NULL,
    delivery_location VARCHAR(150) NOT NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'Medium', -- 'Low', 'Medium', 'High'
    special_instructions TEXT,
    allocated_quantity INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'Open', -- 'Open', 'Matching', 'Allocated', 'In Production', 'Completed', 'Cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_allocations (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(50) NOT NULL,
    business_id INTEGER NOT NULL,
    allocated_quantity INTEGER NOT NULL,
    produced_quantity INTEGER NOT NULL DEFAULT 0,
    approved_quantity INTEGER NOT NULL DEFAULT 0,
    rejected_quantity INTEGER NOT NULL DEFAULT 0,
    invitation_status VARCHAR(50) NOT NULL DEFAULT 'Accepted', -- 'Pending', 'Accepted', 'Rejected'
    production_status VARCHAR(50) NOT NULL DEFAULT 'Not Started', -- 'Not Started', 'In Progress', 'Quality Check', 'Completed', 'Delayed'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS production_updates (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    allocation_id INTEGER NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    business_id INTEGER NOT NULL,
    units_produced INTEGER NOT NULL,
    cumulative_produced INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quality_checks (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    allocation_id INTEGER NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    business_id INTEGER NOT NULL,
    inspector_name VARCHAR(100) NOT NULL,
    dimensions_verified BOOLEAN NOT NULL DEFAULT 0,
    material_verified BOOLEAN NOT NULL DEFAULT 0,
    surface_finish_checked BOOLEAN NOT NULL DEFAULT 0,
    functional_inspection BOOLEAN NOT NULL DEFAULT 0,
    final_quantity_verified BOOLEAN NOT NULL DEFAULT 0,
    approved_units INTEGER NOT NULL DEFAULT 0,
    rejected_units INTEGER NOT NULL DEFAULT 0,
    overall_status VARCHAR(50) NOT NULL DEFAULT 'Pending', -- 'Pending', 'Passed', 'Failed', 'Needs Correction'
    inspection_notes TEXT,
    inspected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agreements (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    agreement_id VARCHAR(50) UNIQUE NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    contract_terms TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Signed', -- 'Draft', 'Signed', 'Active', 'Fulfilled'
    signed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
