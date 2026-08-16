-- MySQL ALTER TABLE statement to change winning_team_id from VARCHAR to INT
-- Run this on your MySQL database to update the schedule table schema

-- First, let's check the current structure of the table
-- DESCRIBE schedule;

-- Step 1: Update any existing data that might not be compatible
-- (Convert any non-numeric values to NULL or appropriate team IDs)
UPDATE schedule 
SET winning_team_id = NULL 
WHERE winning_team_id IS NOT NULL 
  AND winning_team_id NOT REGEXP '^[0-9]+$';

-- Step 2: Alter the column type from VARCHAR to INT
ALTER TABLE schedule 
MODIFY COLUMN winning_team_id INT NULL;

-- Optional: Add a foreign key constraint if you have a teams table
-- (Uncomment the line below if you want to add referential integrity)
-- ALTER TABLE schedule ADD CONSTRAINT fk_schedule_winning_team FOREIGN KEY (winning_team_id) REFERENCES teams(id);

-- Verify the change was successful
DESCRIBE schedule;
