"""
Translation Service for managing UI translations
- Extract strings from templates
- Export to .po format
- Import from .po format
"""

import os
import re
from datetime import datetime
from models import db, Language, Translation


class TranslationService:
    """Service for handling translations"""

    def __init__(self, templates_dir='templates'):
        self.templates_dir = templates_dir

    def extract_strings_from_templates(self):
        """Extract translatable strings from all template files"""
        strings = []
        arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s\d\-\.\,\:\!\?\(\)]*')

        for root, dirs, files in os.walk(self.templates_dir):
            for filename in files:
                if filename.endswith('.html'):
                    filepath = os.path.join(root, filename)
                    relative_path = os.path.relpath(filepath, self.templates_dir)

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Find Arabic text (likely translatable)
                        matches = arabic_pattern.findall(content)
                        for match in matches:
                            match = match.strip()
                            if len(match) > 1:  # Skip single characters
                                strings.append({
                                    'text': match,
                                    'context': relative_path
                                })
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_strings = []
        for s in strings:
            if s['text'] not in seen:
                seen.add(s['text'])
                unique_strings.append(s)

        return unique_strings

    def export_to_po(self, language_code):
        """Export translations to .po format"""
        language = Language.query.filter_by(iso_code=language_code).first()
        if not language:
            return None

        translations = Translation.query.filter_by(language_id=language.id).all()

        # Build .po file content
        po_content = f'''# Translation file for {language.name}
# Language: {language.iso_code}
# Generated: {datetime.utcnow().isoformat()}

msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"
"Language: {language.iso_code}\\n"

'''
        for trans in translations:
            # Escape special characters
            key = trans.key.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            value = (trans.value or '').replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

            if trans.context:
                po_content += f'#: {trans.context}\n'

            po_content += f'msgid "{key}"\n'
            po_content += f'msgstr "{value}"\n\n'

        return po_content

    def import_from_po(self, language_id, po_content):
        """Import translations from .po format"""
        language = Language.query.get(language_id)
        if not language:
            return {'success': False, 'error': 'Language not found'}

        # Parse .po content
        entries = self._parse_po(po_content)

        imported = 0
        updated = 0
        errors = []

        for entry in entries:
            msgid = entry.get('msgid', '').strip()
            msgstr = entry.get('msgstr', '').strip()
            context = entry.get('context')

            if not msgid:
                continue

            try:
                # Check if translation exists
                existing = Translation.query.filter_by(
                    language_id=language_id,
                    key=msgid
                ).first()

                if existing:
                    if msgstr:  # Only update if there's a translation
                        existing.value = msgstr
                        if context:
                            existing.context = context
                        updated += 1
                else:
                    # Create new translation
                    new_trans = Translation(
                        language_id=language_id,
                        key=msgid,
                        value=msgstr if msgstr else None,
                        context=context
                    )
                    db.session.add(new_trans)
                    imported += 1

            except Exception as e:
                errors.append(f"Error for '{msgid[:30]}...': {str(e)}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}

        return {
            'success': True,
            'imported': imported,
            'updated': updated,
            'errors': errors
        }

    def _parse_po(self, content):
        """Parse .po file content"""
        entries = []
        current_entry = {}
        current_field = None

        for line in content.split('\n'):
            line = line.strip()

            # Skip empty lines and comments (except context)
            if not line:
                if current_entry.get('msgid'):
                    entries.append(current_entry)
                current_entry = {}
                continue

            if line.startswith('#:'):
                # Context comment
                current_entry['context'] = line[2:].strip()
            elif line.startswith('#'):
                # Other comments
                continue
            elif line.startswith('msgid '):
                current_field = 'msgid'
                value = line[6:].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                current_entry['msgid'] = self._unescape_po(value)
            elif line.startswith('msgstr '):
                current_field = 'msgstr'
                value = line[7:].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                current_entry['msgstr'] = self._unescape_po(value)
            elif line.startswith('"') and line.endswith('"') and current_field:
                # Continuation line
                value = line[1:-1]
                current_entry[current_field] = current_entry.get(current_field, '') + self._unescape_po(value)

        # Don't forget last entry
        if current_entry.get('msgid'):
            entries.append(current_entry)

        return entries

    def _unescape_po(self, text):
        """Unescape .po format special characters"""
        return text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

    def sync_strings_to_language(self, language_id):
        """Sync extracted strings to a language (add missing, don't remove existing)"""
        strings = self.extract_strings_from_templates()

        added = 0
        for s in strings:
            existing = Translation.query.filter_by(
                language_id=language_id,
                key=s['text']
            ).first()

            if not existing:
                new_trans = Translation(
                    language_id=language_id,
                    key=s['text'],
                    value=None,  # No translation yet
                    context=s['context']
                )
                db.session.add(new_trans)
                added += 1

        db.session.commit()
        return {'added': added, 'total_strings': len(strings)}

    def get_translation(self, key, language_code):
        """Get translation for a key in a specific language"""
        language = Language.query.filter_by(iso_code=language_code).first()
        if not language:
            return key

        trans = Translation.query.filter_by(
            language_id=language.id,
            key=key
        ).first()

        if trans and trans.value:
            return trans.value
        return key  # Return original if no translation
