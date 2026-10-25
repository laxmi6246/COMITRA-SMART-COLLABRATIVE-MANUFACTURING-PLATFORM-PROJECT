import os
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from database import db
from matching import match_partners_for_order

app = Flask(__name__)
app.config.from_object(Config)

# ----------------- AUTH HELPERS -----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles and session.get('role') != 'admin':
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_global_data():
    notifications = []
    if 'user_id' in session:
        notifications = db.query(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 5"
        )
    
    # Professional Avatars
    avatar_map = {
        'owner': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80',
        'partner': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&q=80',
        'admin': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80',
    }
    role = session.get('role', 'guest')
    user_avatar = avatar_map.get(role, 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80')

    return {
        'current_user': session.get('user_name', 'Guest'),
        'current_role': session.get('role', 'guest'),
        'user_avatar': user_avatar,
        'notifications': notifications,
        'db_engine': db.engine.upper()
    }

# ----------------- AUTH ROUTES -----------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        demo_role = request.form.get('demo_role')

        if demo_role:
            # 1-click Demo Role Selector
            role_map = {
                'owner': 'owner@comitra.com',
                'partner': 'partner@comitra.com',
                'admin': 'admin@comitra.com'
            }
            email = role_map.get(demo_role, 'owner@comitra.com')
            user = db.query_one("SELECT * FROM users WHERE email = %s", (email,))
            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['role'] = user['role']
                session['business_id'] = user['business_id']
                flash(f"Welcome back, {user['name']}! Signed in as {user['role'].title()}.", "success")
                return redirect(url_for('dashboard'))

        # Standard Email & Password
        user = db.query_one("SELECT * FROM users WHERE email = %s", (email,))
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            session['business_id'] = user['business_id']
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. You can also use the 1-Click Demo Buttons below.", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('login'))

# ----------------- DASHBOARD -----------------

@app.route('/dashboard')
@login_required
def dashboard():
    # Metrics
    total_orders = db.query_one("SELECT COUNT(*) as count FROM orders")['count']
    total_businesses = db.query_one("SELECT COUNT(*) as count FROM businesses WHERE status = 'Active'")['count']
    
    cap_data = db.query_one("SELECT SUM(total_capacity) as total, SUM(available_capacity) as avail, SUM(occupied_capacity) as occupied FROM businesses")
    total_cap = cap_data['total'] or 0
    avail_cap = cap_data['avail'] or 0
    occupied_cap = cap_data['occupied'] or 0
    
    alloc_data = db.query_one("SELECT SUM(allocated_quantity) as total_alloc, SUM(produced_quantity) as total_prod, SUM(approved_quantity) as total_appr FROM order_allocations")
    total_allocated = alloc_data['total_alloc'] or 0
    total_produced = alloc_data['total_prod'] or 0
    total_approved = alloc_data['total_appr'] or 0

    recent_orders = db.query("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5")
    recent_allocations = db.query("""
        SELECT a.*, o.product_name, b.name as business_name, o.quantity as order_quantity
        FROM order_allocations a
        JOIN orders o ON a.order_id = o.order_id
        JOIN businesses b ON a.business_id = b.id
        ORDER BY a.created_at DESC LIMIT 5
    """)

    return render_template('dashboard.html',
        total_orders=total_orders,
        total_businesses=total_businesses,
        total_cap=total_cap,
        avail_cap=avail_cap,
        occupied_cap=occupied_cap,
        total_allocated=total_allocated,
        total_produced=total_produced,
        total_approved=total_approved,
        recent_orders=recent_orders,
        recent_allocations=recent_allocations
    )

# ----------------- BUSINESS PROFILES -----------------

@app.route('/businesses', methods=['GET', 'POST'])
@login_required
def businesses():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name')
            category = request.form.get('category')
            machinery = request.form.get('machinery')
            total_cap = int(request.form.get('total_capacity', 0))
            occupied_cap = int(request.form.get('occupied_capacity', 0))
            location = request.form.get('location')
            quality_rating = float(request.form.get('quality_rating', 4.5))
            delivery_reliability = float(request.form.get('delivery_reliability', 4.5))
            email = request.form.get('contact_email')
            phone = request.form.get('contact_phone')

            if total_cap < occupied_cap:
                flash("Occupied capacity cannot exceed total capacity.", "danger")
                return redirect(url_for('businesses'))

            available_cap = total_cap - occupied_cap
            biz_count = db.query_one("SELECT COUNT(*) as count FROM businesses")['count']
            biz_id = f"BIZ-{100 + biz_count + 1}"

            db.execute("""
                INSERT INTO businesses 
                (business_id, name, category, machinery, total_capacity, occupied_capacity, available_capacity, 
                 location, quality_rating, delivery_reliability, contact_email, contact_phone, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active')
            """, (biz_id, name, category, machinery, total_cap, occupied_cap, available_cap, location, quality_rating, delivery_reliability, email, phone))

            flash(f"Business profile '{name}' registered successfully with ID {biz_id}!", "success")
            return redirect(url_for('businesses'))

        elif action == 'toggle_status':
            b_id = request.form.get('id')
            current = db.query_one("SELECT status FROM businesses WHERE id = %s", (b_id,))
            new_status = 'Inactive' if current['status'] == 'Active' else 'Active'
            db.execute("UPDATE businesses SET status = %s WHERE id = %s", (new_status, b_id))
            flash(f"Business status updated to {new_status}.", "info")
            return redirect(url_for('businesses'))

    query_str = request.args.get('q', '').strip()
    if query_str:
        all_businesses = db.query("""
            SELECT * FROM businesses 
            WHERE name LIKE %s OR machinery LIKE %s OR category LIKE %s OR location LIKE %s
            ORDER BY id ASC
        """, (f"%{query_str}%", f"%{query_str}%", f"%{query_str}%", f"%{query_str}%"))
    else:
        all_businesses = db.query("SELECT * FROM businesses ORDER BY id ASC")

    return render_template('businesses.html', businesses=all_businesses, search_query=query_str)

# ----------------- POST AN ORDER -----------------

@app.route('/orders/new', methods=['GET', 'POST'])
@login_required
def post_order():
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        category = request.form.get('category')
        quantity = int(request.form.get('quantity', 0))
        required_machinery = request.form.get('required_machinery')
        min_quality = float(request.form.get('min_quality_rating', 4.0))
        deadline = request.form.get('delivery_deadline')
        location = request.form.get('delivery_location')
        priority = request.form.get('priority', 'Medium')
        instructions = request.form.get('special_instructions', '')

        if quantity <= 0:
            flash("Order quantity must be greater than zero.", "danger")
            return redirect(url_for('post_order'))

        order_count = db.query_one("SELECT COUNT(*) as count FROM orders")['count']
        order_id = f"ORD-2026-{100 + order_count + 1}"

        db.execute("""
            INSERT INTO orders 
            (order_id, user_id, product_name, category, quantity, required_machinery, 
             min_quality_rating, delivery_deadline, delivery_location, priority, special_instructions, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Open')
        """, (order_id, session['user_id'], product_name, category, quantity, required_machinery, min_quality, deadline, location, priority, instructions))

        # Log notification
        db.execute(
            "INSERT INTO notifications (user_id, title, message, event_type) VALUES (%s, %s, %s, %s)",
            (session['user_id'], "New Order Created", f"Order {order_id} ({quantity} units) posted successfully.", "order_posted")
        )

        flash(f"Order {order_id} posted successfully! Click 'Find Partners' to match manufacturers.", "success")
        return redirect(url_for('match_partners', order_id=order_id))

    # Pre-fill live demo defaults
    demo_deadline = (datetime.date.today() + datetime.timedelta(days=10)).strftime('%Y-%m-%d')
    return render_template('post_order.html', demo_deadline=demo_deadline)

# ----------------- ORDERS LIST & DETAIL -----------------

@app.route('/orders')
@login_required
def orders():
    all_orders = db.query("SELECT * FROM orders ORDER BY created_at DESC")
    return render_template('orders.html', orders=all_orders)

@app.route('/orders/<order_id>')
@login_required
def order_detail(order_id):
    order = db.query_one("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('orders'))

    allocations = db.query("""
        SELECT a.*, b.name as business_name, b.machinery, b.quality_rating, b.location
        FROM order_allocations a
        JOIN businesses b ON a.business_id = b.id
        WHERE a.order_id = %s
    """, (order_id,))

    return render_template('order_detail.html', order=order, allocations=allocations)

# ----------------- PARTNER MATCHING ALGORITHM -----------------

@app.route('/find-partners')
@login_required
def find_partners():
    orders = db.query("SELECT * FROM orders ORDER BY created_at DESC")
    selected_order_id = request.args.get('order_id')
    
    if not selected_order_id and orders:
        selected_order_id = orders[0]['order_id']
        
    order = None
    eligible_partners = []
    excluded_partners = []
    
    if selected_order_id:
        order = db.query_one("SELECT * FROM orders WHERE order_id = %s", (selected_order_id,))
        if order:
            businesses = db.query("SELECT * FROM businesses")
            eligible_partners, excluded_partners = match_partners_for_order(order, businesses)
            
    all_businesses = db.query("SELECT * FROM businesses ORDER BY quality_rating DESC")
    return render_template('find_partners.html',
        orders=orders,
        order=order,
        eligible_partners=eligible_partners,
        excluded_partners=excluded_partners,
        businesses=all_businesses
    )

@app.route('/orders/<order_id>/match')
@login_required
def match_partners(order_id):
    order = db.query_one("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('orders'))

    businesses = db.query("SELECT * FROM businesses")
    eligible_partners, excluded_partners = match_partners_for_order(order, businesses)

    return render_template('match_results.html',
        order=order,
        eligible_partners=eligible_partners,
        excluded_partners=excluded_partners
    )

# ----------------- ORDER ALLOCATION MODULE -----------------

@app.route('/orders/<order_id>/allocate', methods=['GET', 'POST'])
@login_required
def allocate_order(order_id):
    order = db.query_one("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('orders'))

    businesses = db.query("SELECT * FROM businesses")
    eligible_partners, _ = match_partners_for_order(order, businesses)

    # Calculate existing allocations for this order so their capacity is available for re-allocation
    existing_allocs = {a['business_id']: a['allocated_quantity'] for a in db.query("SELECT * FROM order_allocations WHERE order_id = %s", (order_id,))}

    # Adjust available capacity display in eligible partners to include this order's current share
    for p in eligible_partners:
        b_id = p['business']['id']
        p['business']['effective_available'] = p['business']['available_capacity'] + existing_allocs.get(b_id, 0)
        p['current_allocation'] = existing_allocs.get(b_id, 0)

    if request.method == 'POST':
        total_allocated = 0
        allocations_to_save = []

        # Check all businesses
        for b in businesses:
            b_id = b['id']
            qty_str = request.form.get(f"qty_{b_id}", '0').strip()
            qty = int(qty_str) if qty_str.isdigit() else 0
            
            if qty > 0:
                eff_avail = b['available_capacity'] + existing_allocs.get(b_id, 0)
                if qty > eff_avail:
                    flash(f"Cannot allocate {qty} units to {b['name']}. Available capacity limit is {eff_avail} units.", "danger")
                    return redirect(url_for('allocate_order', order_id=order_id))
                
                total_allocated += qty
                allocations_to_save.append((b_id, qty))

        if total_allocated != order['quantity']:
            diff = order['quantity'] - total_allocated
            if diff > 0:
                flash(f"Total allocated quantity ({total_allocated}) is less than order requirement ({order['quantity']}). Remaining unallocated: {diff} units. Please adjust allocations.", "warning")
            else:
                flash(f"Total allocated quantity ({total_allocated}) exceeds order requirement ({order['quantity']}) by {abs(diff)} units.", "danger")
            return redirect(url_for('allocate_order', order_id=order_id))

        # Revert existing occupied capacity for this order before applying new split
        prev_allocs = db.query("SELECT * FROM order_allocations WHERE order_id = %s", (order_id,))
        for pa in prev_allocs:
            db.execute("""
                UPDATE businesses 
                SET occupied_capacity = occupied_capacity - %s, available_capacity = available_capacity + %s
                WHERE id = %s
            """, (pa['allocated_quantity'], pa['allocated_quantity'], pa['business_id']))
        db.execute("DELETE FROM order_allocations WHERE order_id = %s", (order_id,))

        # Save allocations and deduct capacity
        for b_id, qty in allocations_to_save:
            alloc_id = db.execute("""
                INSERT INTO order_allocations 
                (order_id, business_id, allocated_quantity, produced_quantity, approved_quantity, rejected_quantity, invitation_status, production_status)
                VALUES (%s, %s, %s, 0, 0, 0, 'Accepted', 'Not Started')
            """, (order_id, b_id, qty))

            db.execute("""
                UPDATE businesses 
                SET occupied_capacity = occupied_capacity + %s, available_capacity = available_capacity - %s
                WHERE id = %s
            """, (qty, qty, b_id))

            # Initialize quality check record
            db.execute("""
                INSERT INTO quality_checks 
                (allocation_id, order_id, business_id, inspector_name, overall_status)
                VALUES (%s, %s, %s, 'Kiran Reddy (Lead QA)', 'Pending')
            """, (alloc_id, order_id, b_id))

        # Update order status
        db.execute("UPDATE orders SET allocated_quantity = %s, status = 'Allocated' WHERE order_id = %s", (total_allocated, order_id))

        # Ensure legal agreement exists
        existing_agr = db.query_one("SELECT * FROM agreements WHERE order_id = %s", (order_id,))
        if not existing_agr:
            agr_count = db.query_one("SELECT COUNT(*) as count FROM agreements")['count']
            agr_id = f"AGR-2026-{100 + agr_count + 1}"
            db.execute("""
                INSERT INTO agreements (agreement_id, order_id, title, contract_terms, status)
                VALUES (%s, %s, %s, %s, 'Signed')
            """, (agr_id, order_id, f"Collaborative Manufacturing Contract for {order['product_name']}", "Mutual non-disclosure, IP protection, delivery commitment within 10 days, and ISO-9001 quality warranty terms."))

        # Notification
        db.execute(
            "INSERT INTO notifications (user_id, title, message, event_type) VALUES (%s, %s, %s, %s)",
            (session.get('user_id', 1), "Order Allocated Successfully", f"{total_allocated} units of {order['product_name']} distributed across {len(allocations_to_save)} manufacturing partners.", "order_allocated")
        )

        flash(f"Order successfully allocated to {len(allocations_to_save)} partners! Production tracking initiated.", "success")
        return redirect(url_for('production'))

    return render_template('allocate.html', order=order, eligible_partners=eligible_partners)

# ----------------- PRODUCTION TRACKING -----------------

@app.route('/production')
@login_required
def production():
    # Fetch orders that are allocated or in production
    active_orders = db.query("SELECT * FROM orders WHERE status IN ('Allocated', 'In Production', 'Completed') ORDER BY created_at DESC")
    
    orders_with_data = []
    for ord_obj in active_orders:
        allocations = db.query("""
            SELECT a.*, b.name as business_name, b.machinery, b.quality_rating, b.location
            FROM order_allocations a
            JOIN businesses b ON a.business_id = b.id
            WHERE a.order_id = %s
        """, (ord_obj['order_id'],))

        total_produced = sum(a['produced_quantity'] for a in allocations)
        total_approved = sum(a['approved_quantity'] for a in allocations)
        total_required = ord_obj['quantity']
        progress_pct = round((total_produced / total_required * 100), 1) if total_required > 0 else 0

        orders_with_data.append({
            'order': ord_obj,
            'allocations': allocations,
            'total_produced': total_produced,
            'total_approved': total_approved,
            'pending_quantity': max(0, total_required - total_produced),
            'progress_pct': min(100.0, progress_pct)
        })

    # Recent updates feed
    recent_updates = db.query("""
        SELECT p.*, b.name as business_name, o.product_name
        FROM production_updates p
        JOIN businesses b ON p.business_id = b.id
        JOIN orders o ON p.order_id = o.order_id
        ORDER BY p.created_at DESC LIMIT 6
    """)

    return render_template('production.html', orders_data=orders_with_data, recent_updates=recent_updates)

@app.route('/production/update', methods=['POST'])
@login_required
def update_production():
    alloc_id = request.form.get('allocation_id')
    units_produced = int(request.form.get('units_produced', 0))
    status = request.form.get('production_status', 'In Progress')
    notes = request.form.get('notes', '')

    alloc = db.query_one("SELECT * FROM order_allocations WHERE id = %s", (alloc_id,))
    if not alloc:
        flash("Allocation not found.", "danger")
        return redirect(url_for('production'))

    if units_produced > alloc['allocated_quantity']:
        flash(f"Reported quantity ({units_produced}) cannot exceed assigned quota ({alloc['allocated_quantity']}).", "danger")
        return redirect(url_for('production'))

    # Update allocation
    db.execute("""
        UPDATE order_allocations 
        SET produced_quantity = %s, production_status = %s, notes = %s
        WHERE id = %s
    """, (units_produced, status, notes, alloc_id))

    # Insert update record
    db.execute("""
        INSERT INTO production_updates 
        (allocation_id, order_id, business_id, units_produced, cumulative_produced, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (alloc_id, alloc['order_id'], alloc['business_id'], units_produced, units_produced, status, notes))

    # Check overall order progress
    order_id = alloc['order_id']
    all_allocs = db.query("SELECT * FROM order_allocations WHERE order_id = %s", (order_id,))
    total_prod = sum(a['produced_quantity'] for a in all_allocs)
    order_obj = db.query_one("SELECT quantity FROM orders WHERE order_id = %s", (order_id,))

    new_order_status = 'In Production'
    if total_prod >= order_obj['quantity']:
        new_order_status = 'Completed'

    db.execute("UPDATE orders SET status = %s WHERE order_id = %s", (new_order_status, order_id))

    flash(f"Production progress recorded: {units_produced} units logged. Order status updated to '{new_order_status}'.", "success")
    return redirect(url_for('production'))

# ----------------- QUALITY MANAGEMENT -----------------

@app.route('/quality', methods=['GET', 'POST'])
@login_required
def quality():
    if request.method == 'POST':
        check_id = request.form.get('check_id')
        inspector = request.form.get('inspector_name', session.get('user_name', 'Inspector'))
        dim = 1 if request.form.get('dimensions_verified') else 0
        mat = 1 if request.form.get('material_verified') else 0
        surf = 1 if request.form.get('surface_finish_checked') else 0
        func = 1 if request.form.get('functional_inspection') else 0
        qty_ver = 1 if request.form.get('final_quantity_verified') else 0
        
        approved_units = int(request.form.get('approved_units', 0))
        rejected_units = int(request.form.get('rejected_units', 0))
        notes = request.form.get('inspection_notes', '')

        # All 5 checklist items must pass for 'Passed'
        overall_status = 'Passed' if (dim and mat and surf and func and qty_ver and rejected_units == 0) else 'Failed'
        if approved_units > 0 and rejected_units > 0:
            overall_status = 'Needs Correction'

        db.execute("""
            UPDATE quality_checks 
            SET inspector_name = %s, dimensions_verified = %s, material_verified = %s,
                surface_finish_checked = %s, functional_inspection = %s, final_quantity_verified = %s,
                approved_units = %s, rejected_units = %s, overall_status = %s, inspection_notes = %s,
                inspected_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (inspector, dim, mat, surf, func, qty_ver, approved_units, rejected_units, overall_status, notes, check_id))

        # Update parent allocation approved quantity
        qc = db.query_one("SELECT allocation_id FROM quality_checks WHERE id = %s", (check_id,))
        if qc:
            db.execute("""
                UPDATE order_allocations 
                SET approved_quantity = %s, rejected_quantity = %s
                WHERE id = %s
            """, (approved_units, rejected_units, qc['allocation_id']))

        flash(f"Quality inspection recorded. Overall status: {overall_status}.", "success")
        return redirect(url_for('quality'))

    checks = db.query("""
        SELECT q.*, o.product_name, b.name as business_name, a.allocated_quantity, a.produced_quantity
        FROM quality_checks q
        JOIN order_allocations a ON q.allocation_id = a.id
        JOIN orders o ON q.order_id = o.order_id
        JOIN businesses b ON q.business_id = b.id
        ORDER BY q.id DESC
    """)

    return render_template('quality.html', checks=checks)

# ----------------- AGREEMENTS MODULE -----------------

@app.route('/agreements')
@login_required
def agreements():
    agrs = db.query("""
        SELECT a.*, o.product_name, o.quantity, o.delivery_deadline
        FROM agreements a
        JOIN orders o ON a.order_id = o.order_id
        ORDER BY a.id DESC
    """)
    return render_template('agreements.html', agreements=agrs)

@app.route('/agreements/<agreement_id>')
@login_required
def agreement_view(agreement_id):
    agreement = db.query_one("SELECT * FROM agreements WHERE agreement_id = %s", (agreement_id,))
    if not agreement:
        flash("Agreement not found.", "danger")
        return redirect(url_for('agreements'))

    order = db.query_one("SELECT * FROM orders WHERE order_id = %s", (agreement['order_id'],))
    allocations = db.query("""
        SELECT a.*, b.name as business_name, b.location, b.contact_email, b.contact_phone
        FROM order_allocations a
        JOIN businesses b ON a.business_id = b.id
        WHERE a.order_id = %s
    """, (agreement['order_id'],))

    return render_template('agreement_view.html', agreement=agreement, order=order, allocations=allocations)

# ----------------- ANALYTICS -----------------

@app.route('/analytics')
@login_required
def analytics():
    # Order Status Distribution
    status_counts = db.query("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
    
    # Partner Capacity Utilization
    businesses = db.query("SELECT name, total_capacity, occupied_capacity, available_capacity FROM businesses WHERE status = 'Active'")
    
    # Quality Yield
    quality_stats = db.query("SELECT overall_status, COUNT(*) as count FROM quality_checks GROUP BY overall_status")

    return render_template('analytics.html',
        status_counts=status_counts,
        businesses=businesses,
        quality_stats=quality_stats
    )

# ----------------- SETTINGS & RESET -----------------

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/settings/reset', methods=['POST'])
@login_required
@role_required('admin')
def reset_data():
    from seed import seed_database
    seed_database()
    flash("Database successfully reset to standard live demonstration dataset!", "success")
    return redirect(url_for('dashboard'))

# ----------------- MAIN RUNNER -----------------

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n=========================================================")
    print(f"  CoMitra – Smart Collaborative Manufacturing Platform")
    print(f"  Live Server running on: http://localhost:{port}")
    print(f"  Database Engine: {db.engine.upper()}")
    print(f"=========================================================\n")
    app.run(host='0.0.0.0', port=port, debug=True)
