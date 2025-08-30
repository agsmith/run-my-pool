#!/usr/bin/env python3
"""
Generate SVG team logos for all NFL teams
"""

# NFL team data with colors and abbreviations
teams = [
    {"abbr": "ari", "name": "Arizona Cardinals", "primary": "#97233f", "secondary": "#ffffff"},
    {"abbr": "atl", "name": "Atlanta Falcons", "primary": "#a71930", "secondary": "#000000"},
    {"abbr": "bal", "name": "Baltimore Ravens", "primary": "#241773", "secondary": "#9e7c0c"},
    {"abbr": "buf", "name": "Buffalo Bills", "primary": "#00338d", "secondary": "#c60c30"},
    {"abbr": "car", "name": "Carolina Panthers", "primary": "#0085ca", "secondary": "#101820"},
    {"abbr": "chi", "name": "Chicago Bears", "primary": "#0b162a", "secondary": "#c83803"},
    {"abbr": "cin", "name": "Cincinnati Bengals", "primary": "#fb4f14", "secondary": "#000000"},
    {"abbr": "cle", "name": "Cleveland Browns", "primary": "#311d00", "secondary": "#ff3c00"},
    {"abbr": "den", "name": "Denver Broncos", "primary": "#fb4f14", "secondary": "#002244"},
    {"abbr": "det", "name": "Detroit Lions", "primary": "#0076b6", "secondary": "#b0b7bc"},
    {"abbr": "hou", "name": "Houston Texans", "primary": "#03202f", "secondary": "#a71930"},
    {"abbr": "ind", "name": "Indianapolis Colts", "primary": "#002c5f", "secondary": "#a2aaad"},
    {"abbr": "jac", "name": "Jacksonville Jaguars", "primary": "#006778", "secondary": "#9f792c"},
    {"abbr": "kc", "name": "Kansas City Chiefs", "primary": "#e31837", "secondary": "#ffb81c"},
    {"abbr": "lac", "name": "Los Angeles Chargers", "primary": "#0080c6", "secondary": "#ffc20e"},
    {"abbr": "lar", "name": "Los Angeles Rams", "primary": "#003594", "secondary": "#ffa300"},
    {"abbr": "lv", "name": "Las Vegas Raiders", "primary": "#000000", "secondary": "#a5acaf"},
    {"abbr": "mia", "name": "Miami Dolphins", "primary": "#008e97", "secondary": "#fc4c02"},
    {"abbr": "min", "name": "Minnesota Vikings", "primary": "#4f2683", "secondary": "#ffc62f"},
    {"abbr": "no", "name": "New Orleans Saints", "primary": "#d3bc8d", "secondary": "#101820"},
    {"abbr": "nyg", "name": "New York Giants", "primary": "#0b2265", "secondary": "#a71930"},
    {"abbr": "nyj", "name": "New York Jets", "primary": "#125740", "secondary": "#000000"},
    {"abbr": "phi", "name": "Philadelphia Eagles", "primary": "#004c54", "secondary": "#a5acaf"},
    {"abbr": "pit", "name": "Pittsburgh Steelers", "primary": "#ffb612", "secondary": "#101820"},
    {"abbr": "sea", "name": "Seattle Seahawks", "primary": "#002244", "secondary": "#69be28"},
    {"abbr": "sf", "name": "San Francisco 49ers", "primary": "#aa0000", "secondary": "#b3995d"},
    {"abbr": "tb", "name": "Tampa Bay Buccaneers", "primary": "#d50a0a", "secondary": "#ff7900"},
    {"abbr": "ten", "name": "Tennessee Titans", "primary": "#0c2340", "secondary": "#4b92db"},
    {"abbr": "wsh", "name": "Washington Commanders", "primary": "#773141", "secondary": "#ffb612"}
]

svg_template = '''<!-- {name} Logo -->
<svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
  <circle cx="20" cy="20" r="18" fill="{primary}" stroke="{secondary}" stroke-width="2"/>
  <text x="20" y="26" font-family="Arial, sans-serif" font-size="{font_size}" font-weight="bold" 
        fill="#ffffff" text-anchor="middle" dominant-baseline="middle">{abbr_upper}</text>
</svg>'''

import os

# Create the static/img directory path
img_dir = "/Users/asmith986/work/Development/runmypool/static/img"

for team in teams:
    # Determine font size based on abbreviation length
    font_size = "8" if len(team["abbr"]) > 2 else "10"
    
    svg_content = svg_template.format(
        name=team["name"],
        primary=team["primary"],
        secondary=team["secondary"],
        abbr_upper=team["abbr"].upper(),
        font_size=font_size
    )
    
    # Write the SVG file
    file_path = os.path.join(img_dir, f"{team['abbr']}.svg")
    with open(file_path, 'w') as f:
        f.write(svg_content)
    
    print(f"Created {team['abbr']}.svg")

print(f"\nGenerated {len(teams)} team logo SVG files!")
