// Global state
let currentPhone = '';

// Show/Hide loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

// Show error message
function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    errorElement.textContent = message;
    errorElement.classList.add('show');
    setTimeout(() => {
        errorElement.classList.remove('show');
    }, 5000);
}

// Clear error message
function clearError(elementId) {
    const errorElement = document.getElementById(elementId);
    errorElement.classList.remove('show');
}

// Switch between steps
function showStep(stepId) {
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById(stepId).classList.add('active');
}

// Request OTP
async function requestOTP() {
    const phoneInput = document.getElementById('phoneInput');

    // Get full phone number with country code if intl-tel-input is available
    let phone;
    if (typeof getFullPhoneNumber === 'function') {
        phone = getFullPhoneNumber();
    } else {
        phone = phoneInput.value.trim();
    }

    // Validation
    if (!phone || phone.length < 8) {
        showError('phoneError', 'يرجى إدخال رقم الهاتف / Please enter phone number');
        phoneInput.focus();
        return;
    }

    // Clean phone number (remove spaces, dashes, etc.)
    phone = phone.replace(/[\s\-\(\)]/g, '');

    // Validate with intl-tel-input if available
    if (typeof iti !== 'undefined' && iti.isValidNumber && !iti.isValidNumber()) {
        showError('phoneError', 'رقم الهاتف غير صحيح / Invalid phone number');
        phoneInput.focus();
        return;
    }

    clearError('phoneError');
    showLoading();

    try {
        const response = await fetch('/api/request-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone: phone })
        });

        const data = await response.json();

        if (data.success) {
            currentPhone = phone;
            document.getElementById('phoneDisplay').textContent = phone;
            showStep('otpStep');
            document.getElementById('otpInput').focus();
        } else {
            showError('phoneError', data.message);
        }
    } catch (error) {
        showError('phoneError', 'حدث خطأ في الاتصال / Connection error');
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

// Verify OTP
async function verifyOTP() {
    const otpInput = document.getElementById('otpInput');
    const otp = otpInput.value.trim();

    // Validation
    if (!otp) {
        showError('otpError', 'يرجى إدخال رمز التحقق / Please enter OTP');
        otpInput.focus();
        return;
    }

    if (!/^[0-9]{6}$/.test(otp)) {
        showError('otpError', 'رمز التحقق يجب أن يكون 6 أرقام / OTP must be 6 digits');
        otpInput.focus();
        return;
    }

    clearError('otpError');
    showLoading();

    try {
        const response = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                phone: currentPhone,
                otp: otp
            })
        });

        const data = await response.json();

        if (data.success) {
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } else {
            showError('otpError', data.message);
            otpInput.value = '';
            otpInput.focus();
        }
    } catch (error) {
        showError('otpError', 'حدث خطأ في الاتصال / Connection error');
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

// Back to phone step
function backToPhone() {
    document.getElementById('otpInput').value = '';
    clearError('otpError');
    showStep('phoneStep');
    document.getElementById('phoneInput').focus();
}

// Resend OTP
async function resendOTP() {
    const resendBtn = document.getElementById('resendBtn');
    resendBtn.disabled = true;
    resendBtn.textContent = 'جاري الإرسال...';

    try {
        const response = await fetch('/api/request-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone: currentPhone })
        });

        const data = await response.json();

        if (data.success) {
            showError('otpError', '✅ ' + data.message);
            document.getElementById('otpInput').value = '';
            document.getElementById('otpInput').focus();
        } else {
            showError('otpError', data.message);
        }
    } catch (error) {
        showError('otpError', 'حدث خطأ في الاتصال / Connection error');
        console.error('Error:', error);
    } finally {
        setTimeout(() => {
            resendBtn.disabled = false;
            resendBtn.textContent = 'إعادة الإرسال';
        }, 30000); // 30 seconds cooldown
    }
}

// Handle Enter key press
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('phoneInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            requestOTP();
        }
    });

    document.getElementById('otpInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            verifyOTP();
        }
    });

    // Auto-format OTP input (numbers only)
    document.getElementById('otpInput').addEventListener('input', function(e) {
        this.value = this.value.replace(/[^0-9]/g, '');
    });
});