#!/usr/bin/env python3
"""
Team Logo Migration Script - Convert team logo references from GIF to SVG format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Teams
from sqlalchemy.exc import SQLAlchemyError

def check_current_logo_format():
    """Check the current format of team logos in the database"""
    db = SessionLocal()
    try:
        teams = db.query(Teams).all()
        
        if not teams:
            print("❌ No teams found in database")
            return []
        
        gif_teams = []
        svg_teams = []
        other_teams = []
        
        for team in teams:
            if team.logo:
                if team.logo.endswith('.gif'):
                    gif_teams.append(team)
                elif team.logo.endswith('.svg'):
                    svg_teams.append(team)
                else:
                    other_teams.append(team)
            else:
                other_teams.append(team)
        
        print(f"📊 Current logo format analysis:")
        print(f"  - Teams with .gif logos: {len(gif_teams)}")
        print(f"  - Teams with .svg logos: {len(svg_teams)}")
        print(f"  - Teams with other/no logos: {len(other_teams)}")
        
        if gif_teams:
            print(f"\n🔍 Teams needing migration to SVG:")
            for team in gif_teams:
                print(f"  - {team.abbrv}: {team.name} ({team.logo})")
        
        if other_teams:
            print(f"\n⚠️  Teams with missing/unusual logo format:")
            for team in other_teams:
                logo_display = team.logo if team.logo else "No logo"
                print(f"  - {team.abbrv}: {team.name} ({logo_display})")
        
        return gif_teams
        
    except Exception as e:
        print(f"❌ Error checking current logo format: {e}")
        return []
    finally:
        db.close()

def verify_svg_files_exist():
    """Verify that SVG versions of all team logos exist in static/img directory"""
    static_img_dir = os.path.join(os.path.dirname(__file__), 'static', 'img')
    
    if not os.path.exists(static_img_dir):
        print(f"❌ Static image directory not found: {static_img_dir}")
        return False
    
    db = SessionLocal()
    try:
        teams = db.query(Teams).all()
        missing_svg_files = []
        
        for team in teams:
            if team.abbrv:
                expected_svg_file = f"{team.abbrv.lower()}.svg"
                svg_path = os.path.join(static_img_dir, expected_svg_file)
                
                if not os.path.exists(svg_path):
                    missing_svg_files.append((team.abbrv, expected_svg_file))
        
        if missing_svg_files:
            print(f"❌ Missing SVG files:")
            for abbrv, filename in missing_svg_files:
                print(f"  - {abbrv}: {filename}")
            return False
        else:
            print("✅ All required SVG files exist in static/img directory")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying SVG files: {e}")
        return False
    finally:
        db.close()

def migrate_team_logos_to_svg():
    """Migrate all team logo references from .gif to .svg format"""
    db = SessionLocal()
    try:
        # Get teams that need migration (have .gif extensions)
        gif_teams = db.query(Teams).filter(Teams.logo.like('%.gif')).all()
        
        if not gif_teams:
            print("✅ No teams need migration - all logos are already in SVG format")
            return True
        
        print(f"🔄 Migrating {len(gif_teams)} teams from GIF to SVG format...")
        
        updated_count = 0
        for team in gif_teams:
            old_logo = team.logo
            # Replace .gif extension with .svg
            new_logo = team.logo.replace('.gif', '.svg')
            
            team.logo = new_logo
            print(f"  - {team.abbrv}: {old_logo} → {new_logo}")
            updated_count += 1
        
        # Commit all changes
        db.commit()
        print(f"✅ Successfully migrated {updated_count} team logos to SVG format")
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Database error during migration: {e}")
        db.rollback()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def update_teams_with_missing_logos():
    """Update teams that have no logo or incorrect logo format"""
    db = SessionLocal()
    try:
        # Get teams with missing or non-standard logos
        teams_needing_update = db.query(Teams).filter(
            (Teams.logo.is_(None)) | 
            (~Teams.logo.like('%.svg'))
        ).all()
        
        if not teams_needing_update:
            print("✅ All teams have proper SVG logo references")
            return True
        
        print(f"🔄 Updating {len(teams_needing_update)} teams with missing/incorrect logos...")
        
        updated_count = 0
        for team in teams_needing_update:
            if team.abbrv:
                old_logo = team.logo if team.logo else "None"
                new_logo = f"{team.abbrv.lower()}.svg"
                
                team.logo = new_logo
                print(f"  - {team.abbrv}: {old_logo} → {new_logo}")
                updated_count += 1
        
        # Commit all changes
        db.commit()
        print(f"✅ Successfully updated {updated_count} team logo references")
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ Database error during update: {e}")
        db.rollback()
        return False
    except Exception as e:
        print(f"❌ Unexpected error during update: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def show_final_status():
    """Show the final status of all team logos"""
    db = SessionLocal()
    try:
        teams = db.query(Teams).order_by(Teams.team_id).all()
        
        print(f"\n📋 Final team logo status ({len(teams)} teams):")
        print("=" * 60)
        
        for team in teams:
            logo_status = "✅" if team.logo and team.logo.endswith('.svg') else "❌"
            logo_display = team.logo if team.logo else "No logo"
            print(f"{logo_status} {team.abbrv:3} | {team.name:25} | {logo_display}")
        
    except Exception as e:
        print(f"❌ Error showing final status: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🏈 Team Logo Migration Tool")
    print("===========================")
    
    # Step 1: Check current status
    print("\n1️⃣ Checking current logo format...")
    gif_teams = check_current_logo_format()
    
    # Step 2: Verify SVG files exist
    print("\n2️⃣ Verifying SVG files exist...")
    svg_files_ok = verify_svg_files_exist()
    
    if not svg_files_ok:
        print("\n❌ Cannot proceed - missing SVG files")
        print("💡 Run 'python generate_team_logos.py' first to create SVG files")
        sys.exit(1)
    
    if not gif_teams:
        print("\n✅ All teams already use SVG format - no migration needed")
        show_final_status()
        sys.exit(0)
    
    # Step 3: Ask for confirmation
    print(f"\n3️⃣ Ready to migrate {len(gif_teams)} teams from GIF to SVG format")
    print("\nThis will:")
    print("  - Update the database to change .gif extensions to .svg")
    print("  - Ensure all teams have proper SVG logo references")
    print("  - No files will be deleted or modified")
    
    confirm = input("\nProceed with migration? (y/N): ").strip().lower()
    
    if confirm != "y":
        print("Migration cancelled")
        sys.exit(0)
    
    # Step 4: Perform migration
    print("\n4️⃣ Migrating team logos...")
    migration_success = migrate_team_logos_to_svg()
    
    if not migration_success:
        print("❌ Migration failed")
        sys.exit(1)
    
    # Step 5: Update any remaining teams with missing logos
    print("\n5️⃣ Updating teams with missing logos...")
    update_success = update_teams_with_missing_logos()
    
    if not update_success:
        print("❌ Update failed")
        sys.exit(1)
    
    # Step 6: Show final status
    print("\n6️⃣ Migration completed successfully!")
    show_final_status()
    
    print("\n🎉 Team logo migration completed!")
    print("All teams now use SVG format for better scalability and performance.")
