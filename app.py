from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os
import calendar
from datetime import datetime
from functools import wraps
import urllib
from sqlalchemy import create_engine, text

app = Flask(__name__)
app.secret_key = 'your_secret_key'

server = '.'       
database = 'CarBooking'    
driver = 'ODBC Driver 17 for SQL Server' 

params = urllib.parse.quote_plus(f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;Encrypt=no;")
db_url = f"mssql+pyodbc:///?odbc_connect={params}"
engine = create_engine(db_url)

# ฟังก์ชันรวมร่าง 4 ตารางเข้าด้วยกันเพื่อใช้อ่านข้อมูลรวดเดียว
VIEW_USERS = """
    SELECT emp_id, pin, name, 'employee' AS role, department, phone FROM Employees
    UNION ALL
    SELECT emp_id, pin, name, 'supervisor' AS role, department, phone FROM Supervisors
    UNION ALL
    SELECT emp_id, pin, name, 'driver' AS role, department, phone FROM Drivers
    UNION ALL
    SELECT emp_id, pin, name, 'admin' AS role, department, phone FROM Admins
"""

@app.template_filter('format_date')
def format_date(date_str):
    try:
        d = datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
        return d.strftime('%d-%m-%Y')
    except:
        return str(date_str)

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'emp_id' not in session or session.get('role') != required_role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def clean_dataframe(df):
    if df.empty:
        return df
    df = df.fillna('')
    df = df.astype(str)
    df = df.replace({'nan': '', 'None': '', '<NA>': '', 'NaT': ''})
    return df

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_id = str(request.form.get('emp_id', '')).strip()
        pin = str(request.form.get('pin', '')).strip()
        
        query = text(f"SELECT * FROM ({VIEW_USERS}) AS AllUsers WHERE emp_id = :emp_id AND pin = :pin")
        with engine.connect() as conn:
            user = conn.execute(query, {"emp_id": emp_id, "pin": pin}).mappings().fetchone()
        
        if user:
            session['emp_id'] = user['emp_id']
            session['role'] = user['role']
            session['name'] = user['name']
            
            if session['role'] == 'employee': return redirect(url_for('employee'))
            elif session['role'] == 'driver': return redirect(url_for('driver'))
            elif session['role'] == 'admin': return redirect(url_for('admin'))
            elif session['role'] == 'supervisor': return redirect(url_for('supervisor'))
        else:
            flash('รหัสพนักงาน หรือ รหัส PIN ไม่ถูกต้อง', 'danger')
            
    return render_template('login.html')

@app.route('/employee', methods=['GET', 'POST'])
@role_required('employee')
def employee():
    # เรียกเฉพาะตาราง Drivers
    drivers = pd.read_sql("SELECT emp_id, name, 'driver' AS role FROM Drivers", engine).to_dict('records')
    
    if request.method == 'POST':
        booking_id = request.form.get('booking_id', '').strip()
        parent_id = request.form.get('parent_id', '').strip()
        
        with engine.begin() as conn:
            if booking_id:
                query = text("""
                    UPDATE Bookings 
                    SET date=:date, trip_type=:trip_type, time=:time, return_time=:return_time, 
                        estimated_end_time=:estimated_end_time, van_id=:van_id, pickup=:pickup, 
                        dropoff=:dropoff, remark=:remark, status='🟡 รอหัวหน้าอนุมัติ'
                    WHERE id=:id
                """)
                conn.execute(query, {
                    "date": request.form.get('date', ''),
                    "trip_type": request.form.get('trip_type', 'ขาไป'),
                    "time": request.form.get('time', ''),
                    "return_time": request.form.get('return_time', ''),
                    "estimated_end_time": request.form.get('estimated_end_time', ''),
                    "van_id": request.form.get('van_id', 'รถเก๋ง 1'),
                    "pickup": request.form.get('pickup', ''),
                    "dropoff": request.form.get('dropoff', ''),
                    "remark": request.form.get('remark', ''),
                    "id": booking_id
                })
            else:
                query = text("""
                    INSERT INTO Bookings (id, date, trip_type, time, return_time, estimated_end_time, emp_id, name, van_id, pickup, dropoff, status, remark, parent_id)
                    VALUES (:id, :date, :trip_type, :time, :return_time, :estimated_end_time, :emp_id, :name, :van_id, :pickup, :dropoff, '🟡 รอหัวหน้าอนุมัติ', :remark, :parent_id)
                """)
                conn.execute(query, {
                    "id": datetime.now().strftime("%d%m%Y%H%M%S"),
                    "date": request.form.get('date', ''),
                    "trip_type": request.form.get('trip_type', 'ขาไป'),
                    "time": request.form.get('time', ''),
                    "return_time": request.form.get('return_time', ''),
                    "estimated_end_time": request.form.get('estimated_end_time', ''),
                    "emp_id": session.get('emp_id', ''),
                    "name": session.get('name', ''),
                    "van_id": request.form.get('van_id', 'รถเก๋ง 1'),
                    "pickup": request.form.get('pickup', ''),
                    "dropoff": request.form.get('dropoff', ''),
                    "remark": request.form.get('remark', ''),
                    "parent_id": parent_id if parent_id else None
                })
        return redirect(url_for('employee', selected_date=request.form.get('date')))

    selected_month_input = request.args.get('selected_month', '').strip()
    if selected_month_input and '-' in selected_month_input:
        try:
            year, month = selected_month_input.split('-')
            now = datetime.now()
            if int(year) == now.year and int(month) == now.month:
                selected_date = now.strftime("%Y-%m-%d")
            else:
                selected_date = f"{year}-{month}-01"
        except:
            selected_date = datetime.now().strftime("%Y-%m-%d")
    else:
        selected_date = request.args.get('selected_date', datetime.now().strftime("%Y-%m-%d")).strip()
        if not selected_date:
            selected_date = datetime.now().strftime("%Y-%m-%d")
            
    selected_month_display = selected_date[:7] 

    bookings = pd.read_sql("SELECT * FROM Bookings", engine)

    if not bookings.empty:
        bookings = clean_dataframe(bookings)
        id_to_name = bookings.set_index('id')['name'].to_dict()
        bookings['parent_name'] = bookings['parent_id'].map(id_to_name).fillna('')
        merged = bookings
    else:
        merged = pd.DataFrame(columns=['id', 'date', 'trip_type', 'time', 'return_time', 'estimated_end_time', 'emp_id', 'name', 'van_id', 'pickup', 'dropoff', 'status', 'remark', 'parent_id', 'parent_name'])

    daily_bookings = merged[merged['date'] == selected_date]

    vans_schedule = {'รถเก๋ง 1': [], 'รถเก๋ง 2': [], 'รถตู้ 1': []}
    for van_id in vans_schedule.keys():
        van_trips = daily_bookings[daily_bookings['van_id'] == van_id]
        main_trips = van_trips[(van_trips['parent_id'] == '')]
        
        for _, trip in main_trips.iterrows():
            trip_dict = trip.to_dict()
            joiners = van_trips[van_trips['parent_id'] == trip['id']].to_dict('records')
            trip_dict['joiners'] = joiners
            vans_schedule[van_id].append(trip_dict)

    selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
    current_year = selected_date_obj.year
    current_month = selected_date_obj.month
    thai_months = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
    month_name = thai_months[current_month - 1]
    
    c = calendar.TextCalendar(calendar.SUNDAY)
    cal_matrix = c.monthdayscalendar(current_year, current_month)
    
    month_bookings = merged[
        (merged['date'].str.startswith(f"{current_year}-{current_month:02d}")) & 
        (~merged['status'].str.contains('ปฏิเสธ', na=False))
    ]
    
    van_calendars = {'รถเก๋ง 1': {}, 'รถเก๋ง 2': {}, 'รถตู้ 1': {}}
    for van_id in van_calendars.keys():
        v_trips = month_bookings[(month_bookings['van_id'] == van_id) & (month_bookings['parent_id'] == '')]
        for d in range(1, 32):
            date_str = f"{current_year}-{current_month:02d}-{d:02d}"
            day_trips = v_trips[v_trips['date'] == date_str]
            van_calendars[van_id][d] = 'free' if day_trips.empty else 'booked'

    my_bookings_df = merged[merged['emp_id'] == str(session.get('emp_id'))]
    my_bookings = my_bookings_df.iloc[::-1].to_dict('records')
    
    return render_template('employee.html', 
                           bookings=my_bookings, 
                           drivers=drivers, 
                           selected_date=selected_date, 
                           vans_schedule=vans_schedule,
                           cal_matrix=cal_matrix, 
                           van_calendars=van_calendars, 
                           current_month=current_month, 
                           current_year=current_year, 
                           month_name=month_name,
                           selected_month_display=selected_month_display)

@app.route('/delete/<booking_id>')
@role_required('employee')
def delete_booking(booking_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM Bookings WHERE id = :id OR parent_id = :id"), {"id": booking_id})
    return redirect(request.referrer or url_for('employee'))

@app.route('/supervisor', methods=['GET', 'POST'])
@role_required('supervisor')
def supervisor():
    with engine.begin() as conn:
        sup_data = conn.execute(text("SELECT department FROM Supervisors WHERE emp_id = :emp_id"), {"emp_id": session.get('emp_id')}).mappings().fetchone()
        sup_dept = sup_data['department'] if sup_data and sup_data['department'] else 'ทั่วไป'

        if request.method == 'POST':
            action = request.form.get('action')
            b_id = str(request.form.get('booking_id', ''))
            
            if action == 'approve':
                conn.execute(text("UPDATE Bookings SET status = :status WHERE id = :id"), {"status": "🟠 รอแอดมินอนุมัติ", "id": b_id})
                flash('อนุมัติคำขอเรียบร้อยแล้ว ส่งต่อให้แอดมิน', 'success')
            elif action == 'reject':
                reason = request.form.get('reason', '')
                conn.execute(text("UPDATE Bookings SET status = :status WHERE id = :id"), {"status": f'🔴 ปฏิเสธ (หัวหน้า: {reason})', "id": b_id})
                flash('ปฏิเสธคำขอเรียบร้อยแล้ว', 'danger')
            elif action == 'undo':
                conn.execute(text("UPDATE Bookings SET status = :status WHERE id = :id"), {"status": "🟡 รอหัวหน้าอนุมัติ", "id": b_id})
                flash('↩️ ยกเลิกการตัดสินใจ ดึงคำขอกลับมาพิจารณาใหม่แล้ว', 'warning')
            return redirect(url_for('supervisor'))

    query = f"""
        SELECT b.*, u.department 
        FROM Bookings b
        LEFT JOIN ({VIEW_USERS}) u ON b.emp_id = u.emp_id
    """
    bookings = pd.read_sql(query, engine)
    
    if not bookings.empty:
        bookings = clean_dataframe(bookings)
        my_dept_bookings = bookings[bookings['department'] == sup_dept]
        
        pending_df = my_dept_bookings[my_dept_bookings['status'].str.contains('รอหัวหน้าอนุมัติ', na=False)]
        pending_bookings = pending_df.to_dict('records')
        
        history_df = my_dept_bookings[~my_dept_bookings['status'].str.contains('รอหัวหน้าอนุมัติ', na=False)]
        history_bookings = history_df.sort_values(by=['date', 'time'], ascending=[False, False]).to_dict('records')
    else:
        pending_bookings, history_bookings = [], []

    # ดึงข้อมูลคนขับรถมาจับคู่กับคิวรถ เพื่อส่งไปหน้า supervisor.html
    drivers_df = pd.read_sql("SELECT emp_id, name, phone FROM Drivers", engine)
    drivers_df = clean_dataframe(drivers_df)
    
    driver_mapping = {
        'รถเก๋ง 1': {'name': 'ยังไม่ระบุ', 'phone': '-'},
        'รถเก๋ง 2': {'name': 'ยังไม่ระบุ', 'phone': '-'},
        'รถตู้ 1':  {'name': 'ยังไม่ระบุ', 'phone': '-'}
    }
    
    for _, d in drivers_df.iterrows():
        if str(d['emp_id']) == '2221': driver_mapping['รถเก๋ง 1'] = {'name': d['name'], 'phone': d['phone']}
        elif str(d['emp_id']) == '2222': driver_mapping['รถเก๋ง 2'] = {'name': d['name'], 'phone': d['phone']}
        elif str(d['emp_id']) == '3333': driver_mapping['รถตู้ 1'] = {'name': d['name'], 'phone': d['phone']}

    return render_template('supervisor.html', 
                           pending_bookings=pending_bookings, 
                           history_bookings=history_bookings, 
                           sup_dept=sup_dept,
                           driver_mapping=driver_mapping)


@app.route('/admin', methods=['GET', 'POST'])
@role_required('admin')
def admin():
    if request.method == 'POST':
        action = request.form.get('action')
        b_id = str(request.form.get('booking_id', ''))
        
        # เปิดการเชื่อมต่อฐานข้อมูลด้วย conn
        with engine.begin() as conn:
            if action == 'approve':
                conn.execute(text("UPDATE Bookings SET status = :status WHERE id = :id"), {"status": "🟢 อนุมัติแล้ว", "id": b_id})
                flash('อนุมัติและจัดรถเรียบร้อยแล้ว', 'success')
            elif action == 'reject':
                reason = request.form.get('reason', '')
                conn.execute(text("UPDATE Bookings SET status = :status WHERE id = :id"), {"status": f"🔴 ปฏิเสธ (แอดมิน: {reason})", "id": b_id})
                flash('ปฏิเสธคำขอเรียบร้อยแล้ว', 'danger')
            elif action == 'reset':
                conn.execute(text("UPDATE Bookings SET status = :status WHERE id = :id"), {"status": "🟡 รอหัวหน้าอนุมัติ", "id": b_id})
                flash('↩️ ดึงเรื่องกลับไปสถานะเริ่มต้นเรียบร้อยแล้ว', 'warning')
            elif action == 'change_van':
                new_van = request.form.get('new_van', 'รถเก๋ง 1')
                conn.execute(text("UPDATE Bookings SET van_id = :van WHERE id = :id"), {"van": new_van, "id": b_id})
                flash(f'เปลี่ยนรถเป็น {new_van} เรียบร้อยแล้ว', 'info')
                
        return redirect(url_for('admin'))
        
    selected_year = int(request.args.get('year', datetime.now().year))
    selected_month = int(request.args.get('month', datetime.now().month))
    num_days = calendar.monthrange(selected_year, selected_month)[1]
    
    query = f"""
        SELECT b.*, u.department 
        FROM Bookings b
        LEFT JOIN ({VIEW_USERS}) u ON b.emp_id = u.emp_id
        ORDER BY b.date ASC, b.time ASC
    """
    bookings = pd.read_sql(query, engine)
    
    monthly_schedule = []
    for day in range(1, num_days + 1):
        date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
        day_trips = []
        if not bookings.empty:
            bookings_clean = clean_dataframe(bookings)
            matched = bookings_clean[(bookings_clean['date'] == date_str) & (~bookings_clean['status'].str.contains('ปฏิเสธ', na=False))]
            day_trips = matched.to_dict('records')
            
        monthly_schedule.append({
            'date': date_str,
            'day': day,
            'geeng1': [t for t in day_trips if t.get('van_id') == 'รถเก๋ง 1'],
            'geeng2': [t for t in day_trips if t.get('van_id') == 'รถเก๋ง 2'],
            'tu1': [t for t in day_trips if t.get('van_id') == 'รถตู้ 1']
        })

    if not bookings.empty:
        bookings = clean_dataframe(bookings)
        pending_bookings = bookings[bookings['status'].str.contains('รอ', na=False)].to_dict('records')
        history_bookings = bookings[~bookings['status'].str.contains('รอ', na=False)].to_dict('records')
    else:
        pending_bookings, history_bookings = [], []
        
    # ดึงข้อมูลคนขับรถมาจับคู่กับคิวรถ
    drivers_df = pd.read_sql("SELECT emp_id, name, phone FROM Drivers", engine)
    drivers_df = clean_dataframe(drivers_df)
    
    driver_mapping = {
        'รถเก๋ง 1': {'name': 'ยังไม่ระบุ', 'phone': '-'},
        'รถเก๋ง 2': {'name': 'ยังไม่ระบุ', 'phone': '-'},
        'รถตู้ 1':  {'name': 'ยังไม่ระบุ', 'phone': '-'}
    }
    
    for _, d in drivers_df.iterrows():
        if str(d['emp_id']) == '2221': driver_mapping['รถเก๋ง 1'] = {'name': d['name'], 'phone': d['phone']}
        elif str(d['emp_id']) == '2222': driver_mapping['รถเก๋ง 2'] = {'name': d['name'], 'phone': d['phone']}
        elif str(d['emp_id']) == '3333': driver_mapping['รถตู้ 1'] = {'name': d['name'], 'phone': d['phone']}

    return render_template('admin.html', 
                           pending_bookings=pending_bookings, 
                           history_bookings=history_bookings,
                           monthly_schedule=monthly_schedule, 
                           selected_year=selected_year, 
                           selected_month=selected_month,
                           driver_mapping=driver_mapping)

@app.route('/admin_summary')
@role_required('admin')
def admin_summary():
    # ดึงข้อมูลการจองทั้งหมดที่ไม่ได้ถูกปฏิเสธ
    query = f"""
        SELECT b.*, u.department 
        FROM Bookings b
        LEFT JOIN ({VIEW_USERS}) u ON b.emp_id = u.emp_id
        ORDER BY b.date DESC, b.time ASC
    """
    bookings_df = pd.read_sql(query, engine)
    
    # ดึงข้อมูลคนขับรถ
    drivers_df = pd.read_sql("SELECT emp_id, name, phone FROM Drivers", engine)
    drivers_df = clean_dataframe(drivers_df)
    
    driver_mapping = {
        'รถเก๋ง 1': {'order': 'คนขับคนที่ 1 (รถเก๋ง 1)', 'name': 'ยังไม่ระบุ', 'phone': '-'},
        'รถเก๋ง 2': {'order': 'คนขับคนที่ 2 (รถเก๋ง 2)', 'name': 'ยังไม่ระบุ', 'phone': '-'},
        'รถตู้ 1':  {'order': 'คนขับคนที่ 3 (รถตู้ 1)',  'name': 'ยังไม่ระบุ', 'phone': '-'}
    }
    
    for _, d in drivers_df.iterrows():
        if str(d['emp_id']) == '2221':
            driver_mapping['รถเก๋ง 1']['name'] = d['name']
            driver_mapping['รถเก๋ง 1']['phone'] = d['phone']
        elif str(d['emp_id']) == '2222':
            driver_mapping['รถเก๋ง 2']['name'] = d['name']
            driver_mapping['รถเก๋ง 2']['phone'] = d['phone']
        elif str(d['emp_id']) == '3333':
            driver_mapping['รถตู้ 1']['name'] = d['name']
            driver_mapping['รถตู้ 1']['phone'] = d['phone']

    schedule_data = []
    if not bookings_df.empty:
        bookings_df = clean_dataframe(bookings_df)
        # กรองเอาเฉพาะรายการที่ไม่ได้ถูกปฏิเสธ
        valid_trips = bookings_df[~bookings_df['status'].str.contains('ปฏิเสธ', na=False)].to_dict('records')
        
        for t in valid_trips:
            van = t.get('van_id', 'รถเก๋ง 1')
            d_info = driver_mapping.get(van, {'order': van, 'name': 'ไม่ระบุ', 'phone': '-'})
            t['driver_order'] = d_info['order']
            t['driver_name'] = d_info['name']
            t['driver_phone'] = d_info['phone']
            schedule_data.append(t)

    return render_template('admin_summary.html', schedule_data=schedule_data)

@app.route('/manage_users', methods=['GET', 'POST'])
@role_required('admin')
def manage_users():
    if request.method == 'POST':
        action = request.form.get('action')
        emp_id = request.form.get('emp_id', '').strip()
        pin = request.form.get('pin', '').strip()
        name = request.form.get('name', '').strip()
        department = request.form.get('department', 'ทั่วไป').strip()
        phone = request.form.get('phone', '-').strip()
        if not phone:
            phone = '-'
        role = request.form.get('role', 'employee').strip()

        table_map = {
            'employee': 'Employees',
            'supervisor': 'Supervisors',
            'driver': 'Drivers',
            'admin': 'Admins'
        }
        target_table = table_map.get(role, 'Employees')

        with engine.begin() as conn:
            if action in ['add_user', 'edit_user']:
                # ลบข้อมูลเดิมออกจากทุกตารางก่อน (เผื่อมีการย้ายตำแหน่ง/สิทธิ์)
                for tbl in ['Employees', 'Supervisors', 'Drivers', 'Admins']:
                    conn.execute(text(f"DELETE FROM {tbl} WHERE emp_id = :emp_id"), {"emp_id": emp_id})
                
                # เพิ่มข้อมูลพร้อมเบอร์โทรลงในตารางตามสิทธิ์
                conn.execute(text(f"""
                    INSERT INTO {target_table} (emp_id, pin, name, department, phone)
                    VALUES (:emp_id, :pin, :name, :department, :phone)
                """), {
                    "emp_id": emp_id,
                    "pin": pin,
                    "name": name,
                    "department": department,
                    "phone": phone
                })
                flash(f'บันทึกข้อมูลของ {name} (เบอร์โทร: {phone}) เรียบร้อยแล้ว', 'success')

            elif action == 'delete_user':
                for tbl in ['Employees', 'Supervisors', 'Drivers', 'Admins']:
                    conn.execute(text(f"DELETE FROM {tbl} WHERE emp_id = :emp_id"), {"emp_id": emp_id})
                flash('ลบข้อมูลพนักงานเรียบร้อยแล้ว', 'danger')

        return redirect(url_for('manage_users'))

    users_df = pd.read_sql(f"SELECT * FROM ({VIEW_USERS}) u ORDER BY role, emp_id", engine)
    all_users = clean_dataframe(users_df).to_dict('records') if not users_df.empty else []
    return render_template('manage_users.html', all_users=all_users)

@app.route('/driver')
@role_required('driver')
def driver():
    emp_id = str(session.get('emp_id'))
    # จับคู่รหัสพนักงานขับรถกับรถที่รับผิดชอบ
    van_map = {'2221': 'รถเก๋ง 1', '2222': 'รถเก๋ง 2', '3333': 'รถตู้ 1'}
    assigned_van = van_map.get(emp_id, 'รถตู้ 1')
    
    # ดึงข้อมูลการจอง พร้อมเชื่อมเอา แผนก และ เบอร์โทร ของผู้จองมาจาก VIEW_USERS
    query = f"""
        SELECT b.*, u.department, u.phone 
        FROM Bookings b
        LEFT JOIN ({VIEW_USERS}) u ON b.emp_id = u.emp_id
        ORDER BY b.date ASC, b.time ASC
    """
    bookings = pd.read_sql(query, engine)
    
    manifest = []
    if not bookings.empty:
        bookings = clean_dataframe(bookings)
        # ใช้ .str.contains('อนุมัติแล้ว') เพื่อป้องกันบั๊กอีโมจิ ??
        approved = bookings[(bookings['van_id'] == assigned_van) & (bookings['status'].str.contains('อนุมัติแล้ว', na=False))]
        
        if not approved.empty:
            # แยกผู้จองหลัก กับ ผู้ขอติดรถ (Joiners) ถ้าในระบบมีการเก็บ parent_id หรือรหัสอ้างอิง
            if 'parent_id' in approved.columns:
                main_trips = approved[approved['parent_id'].isna() | (approved['parent_id'] == '') | (approved['parent_id'] == 'None')].to_dict('records')
                for m in main_trips:
                    joiners = approved[approved['parent_id'] == str(m['id'])].to_dict('records')
                    m['joiners'] = joiners
                    manifest.append(m)
            else:
                for m in approved.to_dict('records'):
                    m['joiners'] = []
                    manifest.append(m)
                    
    return render_template('driver.html', manifest=manifest, assigned_van=assigned_van)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)