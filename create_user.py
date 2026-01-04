#!/usr/bin/env python3
"""
CLI script to create new users
Usage: python create_user.py create --phone 01234567890 --telegram_id 123456789
"""

import argparse
from app import app
from models import db, User


def create_user(mobile: str, telegram_id: str, name: str = None):
    """Create a new user"""
    with app.app_context():
        # Basic validation
        if not mobile or not telegram_id:
            print("Error: Phone and Telegram ID are required")
            return False

        # Validate mobile format
        if not mobile.isdigit() or len(mobile) < 10:
            print("Error: Invalid phone number format (should be digits only, minimum 10 digits)")
            return False

        # Validate telegram_id format
        if not telegram_id.isdigit():
            print("Error: Invalid Telegram ID format (should be digits only)")
            return False

        # Warning for bot IDs (usually very long)
        if len(telegram_id) > 12:
            print("Warning: This Telegram ID looks like a Bot ID (too long)")
            print("   Make sure you're using your personal Telegram ID, not a bot's ID")
            print("   Get your ID from @userinfobot")
            response = input("   Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled")
                return False

        # Check if user already exists
        existing_user = User.query.filter(
            (User.mobile == mobile) | (User.telegram_id == telegram_id)
        ).first()

        if existing_user:
            if existing_user.mobile == mobile:
                print(f"Error: Phone number {mobile} already exists")
            if existing_user.telegram_id == telegram_id:
                print(f"Error: Telegram ID {telegram_id} already exists")
            print(f"\nTip: Use 'python create_user.py delete --phone {mobile}' to delete the existing user first")
            return False

        # Create new user
        new_user = User(
            mobile=mobile,
            telegram_id=telegram_id,
            name=name
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"User created successfully!")
            print(f"   Phone: {mobile}")
            print(f"   Telegram ID: {telegram_id}")
            print(f"   User ID: {new_user.id}")
            print(f"\nNext steps:")
            print(f"   1. Make sure you started a chat with the bot (use: python bot_info.py)")
            print(f"   2. Run the app: python app.py")
            print(f"   3. Login at: http://localhost:5000")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {e}")
            return False


def list_users():
    """List all users"""
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found")
            return

        print(f"\n{'ID':<5} {'Mobile':<15} {'Name':<20} {'Telegram ID':<15} {'Created At':<20}")
        print("-" * 80)
        for user in users:
            name = user.name or '-'
            created = user.create_time.strftime('%Y-%m-%d %H:%M:%S') if user.create_time else '-'
            print(f"{user.id:<5} {user.mobile:<15} {name:<20} {user.telegram_id or '-':<15} {created:<20}")


def delete_user(user_id: int = None, mobile: str = None):
    """Delete a user by ID or mobile number"""
    with app.app_context():
        if user_id:
            user = User.query.get(user_id)
            if not user:
                print(f"Error: User with ID {user_id} not found")
                return False
        elif mobile:
            user = User.query.filter_by(mobile=mobile).first()
            if not user:
                print(f"Error: User with phone {mobile} not found")
                return False
        else:
            print("Error: Please provide either --id or --phone")
            return False

        try:
            db.session.delete(user)
            db.session.commit()
            print(f"User deleted successfully!")
            print(f"   Phone: {user.mobile}")
            print(f"   Telegram ID: {user.telegram_id}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting user: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='User management for Non Real Assistant')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create user command
    create_parser = subparsers.add_parser('create', help='Create a new user')
    create_parser.add_argument('--phone', required=True, help='User phone number')
    create_parser.add_argument('--telegram_id', required=True, help='User Telegram ID')
    create_parser.add_argument('--name', help='User name (optional)')

    # List users command
    subparsers.add_parser('list', help='List all users')

    # Delete user command
    delete_parser = subparsers.add_parser('delete', help='Delete a user')
    delete_group = delete_parser.add_mutually_exclusive_group(required=True)
    delete_group.add_argument('--id', type=int, help='User ID to delete')
    delete_group.add_argument('--phone', help='User phone number to delete')

    args = parser.parse_args()

    if args.command == 'create':
        create_user(args.phone, args.telegram_id, getattr(args, 'name', None))
    elif args.command == 'list':
        list_users()
    elif args.command == 'delete':
        delete_user(user_id=args.id, mobile=args.phone)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
