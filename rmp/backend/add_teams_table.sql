-- Migration: Add Teams Table and Update Picks
-- This adds a teams reference table and updates picks to use team_id

-- Create teams table
CREATE TABLE teams (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    abbrv VARCHAR(10) NOT NULL UNIQUE,
    logo VARCHAR(255)
);

-- Add team_id column to picks table (keeping existing team column for backward compatibility)
ALTER TABLE picks ADD COLUMN team_id INT;
ALTER TABLE picks ADD FOREIGN KEY (team_id) REFERENCES teams(id);

-- Insert NFL teams data
INSERT INTO teams (id, name, abbrv, logo) VALUES
(1, 'Atlanta Falcons', 'ATL', '/static/img/atl.gif'),
(2, 'Buffalo Bills', 'BUF', '/static/img/buf.gif'),
(3, 'Chicago Bears', 'CHI', '/static/img/chi.gif'),
(4, 'Cincinnati Bengals', 'CIN', '/static/img/cin.gif'),
(5, 'Cleveland Browns', 'CLE', '/static/img/cle.gif'),
(6, 'Dallas Cowboys', 'DAL', '/static/img/dal.gif'),
(7, 'Denver Broncos', 'DEN', '/static/img/den.gif'),
(8, 'Detroit Lions', 'DET', '/static/img/det.gif'),
(9, 'Green Bay Packers', 'GB', '/static/img/gb.gif'),
(10, 'Tennessee Titans', 'TEN', '/static/img/ten.gif'),
(11, 'Indianapolis Colts', 'IND', '/static/img/ind.gif'),
(12, 'Kansas City Chiefs', 'KC', '/static/img/kc.gif'),
(13, 'Las Vegas Raiders', 'LV', '/static/img/lv.gif'),
(14, 'Los Angeles Rams', 'LAR', '/static/img/lar.gif'),
(15, 'Miami Dolphins', 'MIA', '/static/img/mia.gif'),
(16, 'Minnesota Vikings', 'MIN', '/static/img/min.gif'),
(17, 'New England Patriots', 'NE', '/static/img/ne.gif'),
(18, 'New Orleans Saints', 'NO', '/static/img/no.gif'),
(19, 'New York Giants', 'NYG', '/static/img/nyg.gif'),
(20, 'New York Jets', 'NYJ', '/static/img/nyj.gif'),
(21, 'Philadelphia Eagles', 'PHI', '/static/img/phi.gif'),
(22, 'Arizona Cardinals', 'ARI', '/static/img/ari.gif'),
(23, 'Pittsburgh Steelers', 'PIT', '/static/img/pit.gif'),
(24, 'Los Angeles Chargers', 'LAC', '/static/img/lac.gif'),
(25, 'San Francisco 49ers', 'SF', '/static/img/sf.gif'),
(26, 'Seattle Seahawks', 'SEA', '/static/img/sea.gif'),
(27, 'Tampa Bay Buccaneers', 'TB', '/static/img/tb.gif'),
(28, 'Washington Commanders', 'WSH', '/static/img/wsh.gif'),
(29, 'Carolina Panthers', 'CAR', '/static/img/car.gif'),
(30, 'Jacksonville Jaguars', 'JAX', '/static/img/jax.gif'),
(33, 'Baltimore Ravens', 'BAL', '/static/img/bal.gif'),
(34, 'Houston Texans', 'HOU', '/static/img/hou.gif'),
(98, 'Losing Team', 'LT', '/static/img/red_x.svg'),
(99, 'No Team', 'NT', '/static/img/green_plus.svg');

-- Update existing picks to use team_id based on team abbreviation
-- This assumes your current picks use the team abbreviation in the 'team' column
UPDATE picks p 
SET team_id = (
    SELECT t.id 
    FROM teams t 
    WHERE t.abbrv = p.team
) 
WHERE p.team IS NOT NULL;

-- Create index for better performance
CREATE INDEX idx_teams_abbrv ON teams(abbrv);
CREATE INDEX idx_picks_team_id ON picks(team_id);
