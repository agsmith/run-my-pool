---
# RunMyPool Application Instructions

## Overview
RunMyPool is a web application (runmypool.net) for managing and participating in various sports pool leagues, launching with a classic NFL Survivor Pool format. The platform is designed for extensibility, security, and usability, supporting both public and private leagues, multiple pool types, and robust admin controls.

## Key Features
- **Classic Survivor Pool**: Users create entries and make unique team picks for each week of the NFL season. Picks lock at 1pm ET each week; entry creation/deletion locks at 1pm ET on the first Sunday of the NFL season. Winning picks are outlined in green, losing picks in red.
- **Customizable Pool Types**: Supports future formats (e.g., weekly losing teams, autopicks, Superbowl Block, Pick'em, Confidence Pool).
- **Autopick**: If enabled, users who forget to pick will have the available team with the best odds selected automatically.
- **Admin Portal**: League and site admins have access to advanced management tools.
- **Notifications**: Email and in-app notifications for deadlines, results, and admin actions.
- **Leaderboard & Statistics**: Real-time stats and leaderboards for each league.
- **Message Board**: For advertising picks for sale (not for conversations).
- **Mobile Friendly**: Responsive web design and mobile app planned.

## User Roles & Permissions
- **Regular User**: Can join/create unlimited leagues, manage their entries, and participate in pools.
- **League Admin**: User who creates a league; manages league settings and members.
- **Site Super-Admin**: (Assigned/revoked by the owner) Full access to all leagues, users, and site settings.

## Authentication & Security
- **Methods**: Email/password (min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special), OAuth (Google, Facebook, Apple).
- **Verification**: Email verification and multi-factor authentication required.

## League & Entry Management
- **Multiple Leagues**: Users can join or create unlimited leagues.
- **Entry Management**: Entries can be edited or deleted before the lock time. Users can transfer entries between accounts (admin only).
- **League Types**: Public (open to all) and private (invite-only).
- **No limit**: On number of leagues per user.

## Game Data
- **NFL Data**: Sourced via API (no historical data required).
- **Other Sports**: Support planned for future.

## Customization & Future Pool Types
- **Next Pool Types**: Superbowl Block (with Stripe payment integration), Pick'em, Confidence Pool.
- **Superbowl Block**: 100-square grid, users purchase squares, random assignment, Stripe for payments.

## Notifications
- **Channels**: Email and in-app for deadlines, results, admin actions.

## UI/UX
- **Design**: Simple, clean, modern, usability-focused.
- **Mobile**: Responsive web and mobile app planned.

## Tech Stack
- **Frontend**: Next.js
- **Backend**: FastAPI
- **Database**: MySQL
- **Hosting**: AWS ECS

## Admin Portal Features
- **League Management**:
    - View/Search/Create/Modify/Delete Leagues
    - Set league name, lock time/date, settings, description
- **User Management**:
    - Reset password (force change on next login)
    - Update email
    - Delete user (with warning: permanent deletion of user and entries)
    - Assign/revoke admin access
- **Entry Management**:
    - Transfer entries (admin only)
    - Delete entries
- **Audit Logs**: All admin actions are logged and searchable.
- **Data Export/Reporting**: League admins can export data and generate reports.

## Other Features
- **Leaderboard & Statistics**: For each league.
- **Message Board**: For advertising picks for sale only.
- **Audit Logs**: Searchable logs of all admin actions.
- **Data Export/Reporting**: For league admins.

## Security & Compliance
- **Password Policy**: Enforced complexity.
- **MFA & Email Verification**: Required for all users.
- **Audit Logging**: All sensitive actions logged.

-----------------------------------------

# Application Description
This is a webapp name RunMyPool that will have an fqdn of runmypool.net.  

It is web application that will be a management portal for users to compete in a Survivor Pool league created by a League administrator. It will launch as a classic Survivor Pool format where users create entries and each entry contains picks for each week of the NFL season.  Each team picked must be unique across the entry.  Pick selection will be locked each week at 1pm ET such that users cannot modify their weekly pick after that time. Entry creation will be locked at 1pm ET on the first Sunday of the NFL season such that Entries cannot be created or deleted after that time.  When pick that is locked contains a team that has won the game it will be oulined in green.  When pick that is locked contains a team that has lost the game it will be oulined in red.  

The application should be developed in a way that allows customization, such as allowing the format to be weekly losing teams rather than winning teams.  And allowing autopicks for entrys that forgot to make a select for the week.  Also allow future types of pools to be supported such as the Superbowl Block pools which is a grid of 100 squares that users can purchase and the grid will be randomly assigned corrdinate numbers.

There will be an Admin section that will only be accessible by League administrators and it will have functionality for: 
League Management (
    View Leagues (
        Search Leagues
    ), 
    Create League (
        League Name, 
        Lock Time and Date, 
        League Settings, 
        League Description
    ), 
    Modify League (
        Select League to Modify
    ), 
    Delete League (
        Select League to Delete
    )
), 
User Management (
    Reset User Password (
        Username, 
        Force user to change password on next login
    ), 
    Update User Email (
        Username, 
        New Email Address
    ), 
    Delete User (
        Warning that this will permanently delete user and entries, 
        Username
    ), 
    Assign Administor Access (
        Username, 
        confirm user should have admin access
    )
), 
Entry Management (
    Transfer Entries (
        Entry ID, 
        From User, 
        To User
    ), 
    Delete Entries (
        Entry Id, 
        Username
    ), 
    Correct Pick (
        Username, 
        Week Num, 
        Team Abbreviation, 
        Reason for Correction)
    )
),
Audit Log ( 
    Seach Audit Log (
        userid,
        date from, 
        date to,
        action contains text fuzzy Search
    )
)

There shall be an audit log that will recored all activities in the database.

There shall be an account page that lets a user change their password (new password, confirm password)

All inputs should be validated against injection attacks
The entire application should be protected agains OWASP Top 10 vulnerabilities

# General Conventions
- all ids should be in uuid format. 
- api names should use kebab-case with lower case characters
- variable names should use python style naming conventions

# Domain Objects
- A user may be an administrator of zero or more leagues
- A user may be a member of zero of more leagues
- A user shall have 0 or more entries
- An entry shall have 18 Picks.  One for each week 1-18
- An entry may only select a team once such that if a team has already been selected in the  entry, it cannot be selected again
- A Pick can only select 1 team.
- A Pick is owned by an Entry
- An Entry is owned by a User

# API flows
## Landing Page
### /
Its main landing page will be a home page that describes the application as customizable, affordable and scalable.  It is focused on Office football pool management.  There will be some stock images that are center around football survivor pools. On the main landing page there will be a login button in the top right of the screen. 

## User Flows
### /login
Clicking that login button will take the user to a login screen with an option for Create New Account and Forgot Password.  The page will validate that password is within size range constraints and that email is in a proper format.  When a user logs in the username and password will be validated on the backend database using owasp best practices for securing and validating user credentials.  A cookie will be stored in the users browser which is a concatenation of userid:session-token. This session token will be stored in the database and validated for each user action.

### /forgot-password
If a user clicks Forgot Password on the login screen they will be taken to the forgot-password page that will contain a form containing email field and a submit button.  The page will validate email is in a proper format and send a password reset email to the user if the email exists in the system. The user will receive an email with a secure reset link that expires after a set time period.

### /create-account
When a user clicks Create New Account, they are taken to a create-account page that contains a form for email, password and confirm password with a Submit button.  The page will validate that password and confirm password match and that email is in a proper format.

### /update-user
reset user password

### /delete-user

## League Flows
### /create-league
### /update-league/{league-id}
### /delete-league/{league-id}
### /join-league/{league-id}
### /invite-league

## Entry Flows
### /create-entry
### /update-entry/{entry-id}
### /delete-entry/{entry-id}
### /delete-entry/last

## Pick Flows
### /create-Pick
### /update-Pick/(pick-id)
### /delete Pick/{pick-id}

## Schedule Flows
### /schedule/{week_num}

## Infra Flows
### /health





# Tech Stack
- Next.js
- CSS
- Python
- FastAPI
- pytest
- MySQL
- Docker
- github action ci/cd

# Front End
# User Interface
Picks should be represented visually as circles.  

Picks without team selection should contain the week number.  

When a user click the pick circle, an overlay should be presented that show the matchups for the week in a visually appealing way.  

Teams that have already been selected in the entry should not be selectable again and the team logo should be grayed out.

Only one team should be selectable at a time.

There is a submit button on the overlay that will save the users pick for that particular week in the entry.

After a pick selection has been made, pick circles should show an svg image of the nfl logo corresponding to the selected team.
The styling should be very minimialist and consistent across all pages,  There should be a look that the application has been professionally developed.

# Backend 
See API Flows above

# Database
generate ddl and ctl for database using sqlalchemy.  Get NFL schedules, odds and game results and keep data up-to-date

# Infrastructure
AWS ECR, ECS, RDS, Route 53, ELB, Terraform,  Infra already exists.  build should create docker image and push to ECR and refresh ecs tasks

# Security
- Secure agaings OWASP Top 10 attack 

# Testing
generate comprehensive unit tests using pytest

# Runtime Environments
- Developemnt is on localhost
- Production is on AWS ECR, ECS, RDS, Route 53, ELB


