"""Translation management routes (Admin only)"""

from flask import Blueprint, render_template, request, jsonify, session, Response
from functools import wraps

translations_bp = Blueprint('translations', __name__)


def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

        from models import User
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated


def require_admin_page(f):
    """Decorator for page routes that require admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            from flask import redirect, url_for
            return redirect(url_for('auth.login'))

        from models import User
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            from flask import abort
            abort(403)

        return f(*args, **kwargs)
    return decorated


@translations_bp.route('/translations')
@require_admin_page
def translations_page():
    """Translation management page"""
    return render_template('translations.html', active_page='translations')


# ===== Languages API =====

@translations_bp.route('/api/translations/languages')
@require_admin
def get_languages():
    """Get all languages with translation counts"""
    from models import Language, Translation

    languages = Language.query.all()
    result = []

    for lang in languages:
        trans_count = Translation.query.filter_by(language_id=lang.id).count()
        translated_count = Translation.query.filter(
            Translation.language_id == lang.id,
            Translation.value.isnot(None),
            Translation.value != ''
        ).count()

        result.append({
            **lang.to_dict(),
            'total_strings': trans_count,
            'translated_count': translated_count
        })

    return jsonify(result)


@translations_bp.route('/api/translations/languages', methods=['POST'])
@require_admin
def create_language():
    """Create a new language"""
    from models import db, Language

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    name = data.get('name', '').strip()
    iso_code = data.get('iso_code', '').strip().lower()

    if not name or not iso_code:
        return jsonify({'error': 'Name and ISO code are required'}), 400

    # Check if language already exists
    existing = Language.query.filter_by(iso_code=iso_code).first()
    if existing:
        return jsonify({'error': 'Language with this ISO code already exists'}), 409

    new_lang = Language(name=name, iso_code=iso_code)
    db.session.add(new_lang)
    db.session.commit()

    return jsonify({
        'success': True,
        'language': new_lang.to_dict()
    }), 201


@translations_bp.route('/api/translations/languages/<int:language_id>', methods=['DELETE'])
@require_admin
def delete_language(language_id):
    """Delete a language and all its translations"""
    from models import db, Language

    language = Language.query.get(language_id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404

    # Prevent deleting Arabic (base language)
    if language.iso_code == 'ar':
        return jsonify({'error': 'Cannot delete base language (Arabic)'}), 400

    db.session.delete(language)
    db.session.commit()

    return jsonify({'success': True})


# ===== Translations API =====

@translations_bp.route('/api/translations/<int:language_id>')
@require_admin
def get_translations(language_id):
    """Get all translations for a language"""
    from models import Translation, Language

    language = Language.query.get(language_id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404

    translations = Translation.query.filter_by(language_id=language_id).all()
    return jsonify([t.to_dict() for t in translations])


@translations_bp.route('/api/translations/<int:language_id>', methods=['PUT'])
@require_admin
def update_translation(language_id):
    """Update a single translation"""
    from models import db, Translation, Language

    language = Language.query.get(language_id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404

    data = request.get_json()
    translation_id = data.get('id')
    new_value = data.get('value', '').strip()

    if not translation_id:
        return jsonify({'error': 'Translation ID required'}), 400

    trans = Translation.query.get(translation_id)
    if not trans or trans.language_id != language_id:
        return jsonify({'error': 'Translation not found'}), 404

    trans.value = new_value if new_value else None
    db.session.commit()

    return jsonify({
        'success': True,
        'translation': trans.to_dict()
    })


# ===== Export/Import =====

@translations_bp.route('/api/translations/<int:language_id>/export')
@require_admin
def export_translations(language_id):
    """Export translations to .po file"""
    from models import Language
    from services.translation_service import TranslationService

    language = Language.query.get(language_id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404

    service = TranslationService()
    po_content = service.export_to_po(language.iso_code)

    if po_content is None:
        return jsonify({'error': 'Export failed'}), 500

    filename = f'{language.iso_code}.po'
    return Response(
        po_content,
        mimetype='text/x-gettext-translation',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@translations_bp.route('/api/translations/<int:language_id>/import', methods=['POST'])
@require_admin
def import_translations(language_id):
    """Import translations from .po file"""
    from models import Language
    from services.translation_service import TranslationService

    language = Language.query.get(language_id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404

    # Get file from request
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    try:
        content = file.read().decode('utf-8')
    except Exception as e:
        return jsonify({'error': f'Failed to read file: {str(e)}'}), 400

    service = TranslationService()
    result = service.import_from_po(language_id, content)

    return jsonify(result)


# ===== Extract & Sync =====

@translations_bp.route('/api/translations/extract')
@require_admin
def extract_strings():
    """Extract translatable strings from templates"""
    from services.translation_service import TranslationService

    service = TranslationService()
    strings = service.extract_strings_from_templates()

    return jsonify({
        'count': len(strings),
        'strings': strings
    })


@translations_bp.route('/api/translations/<int:language_id>/sync', methods=['POST'])
@require_admin
def sync_translations(language_id):
    """Sync extracted strings to a language"""
    from models import Language
    from services.translation_service import TranslationService

    language = Language.query.get(language_id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404

    service = TranslationService()
    result = service.sync_strings_to_language(language_id)

    return jsonify({
        'success': True,
        **result
    })
