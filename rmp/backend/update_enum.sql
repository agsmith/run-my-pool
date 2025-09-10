-- Update the users table to use uppercase enum values
USE RMP;
ALTER TABLE users MODIFY COLUMN role ENUM('USER', 'POOL_ADMIN', 'SUPER_ADMIN') DEFAULT 'USER';
