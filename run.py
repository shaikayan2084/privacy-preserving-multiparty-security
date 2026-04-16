"""
SMPC Shield — Application Entry Point
Run: python run.py
"""
import os
import sys

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create required directories
os.makedirs('logs', exist_ok=True)
os.makedirs('instance', exist_ok=True)

from app import app, init_db

if __name__ == '__main__':
    print("\n" + "═" * 55)
    print("  🔐  SMPC Shield — Privacy-Preserving Collaboration")
    print("  📡  http://127.0.0.1:5000")
    print("  👤  Admin: admin@smpc.local / Admin@1234")
    print("  ⚠️   Change admin password after first login!")
    print("═" * 55 + "\n")

    # Initialize DB + default admin
    init_db()

    debug_mode = os.getenv('FLASK_DEBUG', 'True') == 'True'
    app.run(
        debug=debug_mode,
        host='127.0.0.1',
        port=5000,
        use_reloader=debug_mode
    )
