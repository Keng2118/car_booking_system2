USE CarBooking;
GO

-- ==========================================
-- 1. ลบตารางเก่าทิ้ง 
-- ==========================================
IF OBJECT_ID('dbo.Bookings', 'U') IS NOT NULL DROP TABLE dbo.Bookings;
IF OBJECT_ID('dbo.Users', 'U') IS NOT NULL DROP TABLE dbo.Users;
GO -- <--- สั่งให้ลบให้เสร็จก่อน

-- ==========================================
-- 2. สร้างตาราง Users (เวอร์ชันใหม่ มีแผนก)
-- ==========================================
CREATE TABLE Users (
    emp_id VARCHAR(50) PRIMARY KEY,
    pin VARCHAR(50) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    department NVARCHAR(100) DEFAULT 'ทั่วไป'
);
GO -- <--- สั่งให้สร้างตารางนี้ให้เสร็จก่อน

-- ==========================================
-- 3. สร้างตาราง Bookings
-- ==========================================
CREATE TABLE Bookings (
    id VARCHAR(50) PRIMARY KEY, 
    date DATE NOT NULL,         
    trip_type NVARCHAR(50) DEFAULT 'ขาไป',
    time VARCHAR(10),           
    return_time VARCHAR(10),    
    estimated_end_time VARCHAR(10), 
    emp_id VARCHAR(50) NOT NULL, 
    name NVARCHAR(100),         
    van_id NVARCHAR(50) DEFAULT 'รถเก๋ง 1',
    pickup NVARCHAR(255),       
    dropoff NVARCHAR(255),      
    status NVARCHAR(100) DEFAULT '🟡 รอหัวหน้าอนุมัติ', 
    remark NVARCHAR(MAX),       
    parent_id VARCHAR(50),
    created_at DATETIME DEFAULT GETDATE(), 
    
    CONSTRAINT FK_Bookings_Users FOREIGN KEY (emp_id) REFERENCES Users(emp_id)
);
GO -- <--- สั่งให้สร้างตารางนี้ให้เสร็จก่อน

-- ==========================================
-- 4. ใส่ข้อมูลเริ่มต้น (ตอนนี้ SQL รู้จักคอลัมน์ department แน่นอนแล้ว)
-- ==========================================
INSERT INTO Users (emp_id, pin, name, role, department)
VALUES 
    ('1111', '1234', 'พนักงานทั่วไป', 'employee', 'IT'),
    ('8888', '1234', 'หัวหน้า A', 'supervisor', 'IT'),
    ('2221', '1234', 'นาย A (คนขับรถเก๋ง 1)', 'driver', 'ทั่วไป'),
    ('2222', '1234', 'นาย B (คนขับรถเก๋ง 2)', 'driver', 'ทั่วไป'),
    ('3333', '1234', 'นาย C (คนขับรถตู้ 1)', 'driver', 'ทั่วไป'),
    ('9999', '1234', 'ผู้ดูแลระบบ', 'admin', 'ทั่วไป');
GO