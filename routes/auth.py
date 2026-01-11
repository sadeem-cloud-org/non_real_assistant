"""Authentication routes"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.auth import AuthService
from models import db, UserLoginHistory

auth_bp = Blueprint('auth', __name__)

# Initialize auth service
auth_service = AuthService()


@auth_bp.route('/')
def index():
    """Main route - check if user is logged in"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login')
def login():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/request-otp', methods=['POST'])
def request_otp():
    """API endpoint to request OTP"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'طلب غير صالح / Invalid request'
            }), 400

        mobile = data.get('phone', '').strip()  # Keep 'phone' for backward compatibility

        if not mobile:
            return jsonify({
                'success': False,
                'message': 'يرجى إدخال رقم الهاتف / Please enter phone number'
            }), 400

        print(f"[DEBUG] Request OTP for phone: {mobile}")  # Debug log
        result = auth_service.request_otp(mobile)
        print(f"[DEBUG] Result: {result}")  # Debug log
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] request_otp error: {e}")
        return jsonify({
            'success': False,
            'message': 'حدث خطأ في الخادم / Server error'
        }), 500


@auth_bp.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """API endpoint to verify OTP"""
    data = request.get_json()
    mobile = data.get('phone', '').strip()  # Keep 'phone' for backward compatibility
    otp_code = data.get('otp', '').strip()

    if not mobile or not otp_code:
        return jsonify({
            'success': False,
            'message': 'يرجى إدخال جميع البيانات / Please enter all fields'
        }), 400

    result = auth_service.verify_otp(mobile, otp_code)

    if result['success']:
        # Create session
        session.permanent = True
        session['user_id'] = result['user']['id']
        session['mobile'] = result['user']['mobile']

        # Track login history
        try:
            login_history = UserLoginHistory(
                user_id=result['user']['id'],
                ip=request.remote_addr,
                browser=request.user_agent.string[:200] if request.user_agent else None
            )
            db.session.add(login_history)
            db.session.commit()
        except Exception as e:
            print(f"Error tracking login history: {e}")

    return jsonify(result)
