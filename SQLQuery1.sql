ALTER TABLE Users ADD phone VARCHAR(20) DEFAULT '-';
GO

UPDATE Users SET phone = '-' WHERE phone IS NULL;
GO