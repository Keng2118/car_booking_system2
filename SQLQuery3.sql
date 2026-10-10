USE CarBooking;
GO

-- 1. ลบ Foreign Key เดิมที่เคยผูกกับ Users
IF OBJECT_ID('FK_Bookings_Users', 'F') IS NOT NULL 
    ALTER TABLE Bookings DROP CONSTRAINT FK_Bookings_Users;
GO

-- 2. ลบตาราง Users แบบรวมทิ้ง
IF OBJECT_ID('dbo.Users', 'U') IS NOT NULL DROP TABLE dbo.Users;
GO

-- 3. สร้าง 4 ตารางแยกตามสิทธิ์
CREATE TABLE Employees (emp_id VARCHAR(50) PRIMARY KEY, pin VARCHAR(50) NOT NULL, name NVARCHAR(100) NOT NULL, department NVARCHAR(100) DEFAULT 'ทั่วไป', phone VARCHAR(20) DEFAULT '-');
CREATE TABLE Supervisors (emp_id VARCHAR(50) PRIMARY KEY, pin VARCHAR(50) NOT NULL, name NVARCHAR(100) NOT NULL, department NVARCHAR(100) DEFAULT 'ทั่วไป', phone VARCHAR(20) DEFAULT '-');
CREATE TABLE Drivers (emp_id VARCHAR(50) PRIMARY KEY, pin VARCHAR(50) NOT NULL, name NVARCHAR(100) NOT NULL, department NVARCHAR(100) DEFAULT 'ทั่วไป', phone VARCHAR(20) DEFAULT '-');
CREATE TABLE Admins (emp_id VARCHAR(50) PRIMARY KEY, pin VARCHAR(50) NOT NULL, name NVARCHAR(100) NOT NULL, department NVARCHAR(100) DEFAULT 'ทั่วไป', phone VARCHAR(20) DEFAULT '-');
GO

-- 4. ใส่ข้อมูลเริ่มต้นเข้าแต่ละตาราง
INSERT INTO Employees (emp_id, pin, name, department, phone) VALUES ('1111', '1234', 'พนักงานทั่วไป', 'IT', '-');
INSERT INTO Supervisors (emp_id, pin, name, department, phone) VALUES ('8888', '1234', 'หัวหน้า A', 'IT', '-');
INSERT INTO Drivers (emp_id, pin, name, department, phone) VALUES ('2221', '1234', 'นาย A (คนขับรถเก๋ง 1)', 'ทั่วไป', '-'), ('2222', '1234', 'นาย B (คนขับรถเก๋ง 2)', 'ทั่วไป', '-'), ('3333', '1234', 'นาย C (คนขับรถตู้ 1)', 'ทั่วไป', '-');
INSERT INTO Admins (emp_id, pin, name, department, phone) VALUES ('9999', '1234', 'ผู้ดูแลระบบ', 'ทั่วไป', '-');
GO

CREATE TRIGGER trg_Check_Booking_EmpID
ON Bookings
AFTER INSERT, UPDATE
AS
BEGIN
    -- ดักจับข้อมูลที่กำลังจะถูกบันทึกลง Bookings
    IF EXISTS (
        SELECT 1 
        FROM inserted i
        WHERE NOT EXISTS (SELECT 1 FROM Employees WHERE emp_id = i.emp_id)
          AND NOT EXISTS (SELECT 1 FROM Supervisors WHERE emp_id = i.emp_id)
          AND NOT EXISTS (SELECT 1 FROM Drivers WHERE emp_id = i.emp_id)
          AND NOT EXISTS (SELECT 1 FROM Admins WHERE emp_id = i.emp_id)
    )
    BEGIN
        -- ถ้าหารหัสไม่เจอในทุกตาราง ให้ยกเลิกการทำงานและแจ้งเตือน
        RAISERROR ('การเชื่อมโยงล้มเหลว: ไม่พบรหัสพนักงานนี้ในตารางพนักงาน, หัวหน้า, คนขับ หรือแอดมิน', 16, 1);
        ROLLBACK TRANSACTION;
    END
END;
GO

USE CarBooking;
GO

-- สร้างตารางมุมมองใหม่ที่แปลงวันที่เป็น วัน-เดือน-ปี (DD-MM-YYYY)
CREATE OR ALTER VIEW v_Bookings_TH AS
SELECT 
    id,
    emp_id,
    name,
    -- แปลงจาก YYYY-MM-DD เป็น DD-MM-YYYY
    CASE 
        WHEN LEN(date) = 10 AND SUBSTRING(date, 5, 1) = '-' 
        THEN SUBSTRING(date, 9, 2) + '-' + SUBSTRING(date, 6, 2) + '-' + SUBSTRING(date, 1, 4)
        ELSE date 
    END AS [วันที่เดินทาง (ว-ด-ป)],
    time AS [เวลาไป],
    estimated_end_time AS [เวลาคาดว่าถึง],
    trip_type AS [ประเภท],
    return_time AS [เวลากลับ],
    pickup AS [จุดรับ],
    dropoff AS [จุดส่ง],
    van_id AS [รถที่ใช้],
    status AS [สถานะ],
    remark AS [หมายเหตุ]
FROM Bookings;
GO

-- ทดสอบดึงข้อมูลขึ้นมาดู
SELECT * FROM v_Bookings_TH;