from flask import Flask, render_template_string, request, jsonify, send_file, render_template
import os
import re
from bs4 import BeautifulSoup
import tempfile
import json
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

from app.utils import extract_post_elements, render_linkedin_preview, save_post_as_html
from app.linkedin_bot import get_posting_data

CONTENT_DIR = Path(f"{os.getcwd()}/content/new")
CONFIG_FILE = f"{os.getcwd()}/config/config.ini"

app = Flask(__name__, static_folder="../content")

editable_elements = ['confirmed', 'origin', 'text', 'image']



def extract_post_elements_local(html_file):
    html_file = f"{CONTENT_DIR}/{html_file}"

    try:
        all_elements = get_posting_data(html_file)
        elements = {}
        # select only editable fields:
        for item in editable_elements:
            elements[item] = all_elements.get(item)
            
        print(f"Elements: {elements}")
        return elements
        
    except Exception as e:
        raise Exception(f"Fehler beim Extrahieren der Elemente: {str(e)}")



def apply_elements_to_html(file, elements):
    try:
        #old_elements = extract_post_elements(file)
        text = elements.get('text')
        image = elements.get('image')
        print(f"Image: {image}")

        temp_file = f"{CONTENT_DIR}/{file}.tmp"
        save_post_as_html(text, image, temp_file)

        with open(temp_file, 'r', encoding='utf-8') as file:
            content = file.read()

        soup = BeautifulSoup(content, 'html.parser')

        #os.unlink(temp_file)

        return str(soup)
        
    except Exception as e:
        raise Exception(f"Fehler beim Anwenden der Änderungen: {str(e)}")



def apply_elements_to_html_BAK(html_file, elements):
    """
    Wendet die geänderten Elemente auf die HTML-Datei an und gibt den neuen Inhalt zurück.
    """
    try:
        html_file = f"{CONTENT_DIR}/{html_file}"
        with open(html_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        for key, value in elements.items():
           
            # Title ändern
            if key == 'title':
                title_tag = soup.find('title')
                if title_tag:
                    title_tag.string = value
                else:
                    # Title-Tag erstellen falls nicht vorhanden
                    head = soup.find('head')
                    if head:
                        new_title = soup.new_tag('title')
                        new_title.string = value
                        head.append(new_title)
            
            # Meta-Tags ändern
            elif key.startswith('meta_'):
                meta_name = key.replace('meta_', '')
                meta_tag = soup.find('meta', {'name': meta_name})
                if meta_tag:
                    meta_tag['content'] = value
                else:
                    # Meta-Tag erstellen falls nicht vorhanden
                    head = soup.find('head')
                    if head:
                        new_meta = soup.new_tag('meta', attrs={'name': meta_name, 'content': value})
                        head.append(new_meta)
            
            # H1-Tags ändern
            elif key.startswith('h1_'):
                try:
                    index = int(key.replace('h1_', '')) - 1
                    h1_tags = soup.find_all('h1')
                    if index < len(h1_tags):
                        h1_tags[index].string = value
                except (ValueError, IndexError):
                    pass
            
            # P-Tags ändern
            elif key.startswith('p_'):
                try:
                    index = int(key.replace('p_', '')) - 1
                    p_tags = soup.find_all('p')
                    if index < len(p_tags):
                        p_tags[index].string = value
                except (ValueError, IndexError):
                    pass
            
            # Elemente mit ID ändern
            else:
                elem = soup.find(attrs={'id': key})
                if elem:
                    elem.string = value
                
                # Alternativ: Elemente mit data-editable und passender ID
                elem = soup.find(attrs={'data-editable': True, 'id': key})
                if elem:
                    elem.string = value
        
        return str(soup)
        
    except Exception as e:
        raise Exception(f"Fehler beim Anwenden der Änderungen: {str(e)}")




@app.route('/contenteditor')
def content_editor():
    return render_template('content_editor.html')


@app.route('/api/extract-elements')
def api_extract_elements():
    """
    API-Endpunkt zum Extrahieren der editierbaren Elemente aus einer HTML-Datei
    """
    file = request.args.get('file')
    file_path = f"{CONTENT_DIR}/{file}"
    
    if not file_path:
        return jsonify({
            'success': False, 
            'error': 'Kein Dateipfad angegeben'
        }), 400
    
    # Sicherheitsprüfung: Nur Dateien aus erlaubten Verzeichnissen
    if not os.path.exists(file_path):
        return jsonify({
            'success': False, 
            'error': 'Datei nicht gefunden'
        }), 404
    
    # Prüfe ob es eine HTML-Datei ist
    if not file_path.lower().endswith(('.html', '.htm')):
        return jsonify({
            'success': False, 
            'error': 'Nur HTML-Dateien werden unterstützt'
        }), 400
    
    try:
        elements = extract_post_elements_local(file)
        return jsonify({
            'success': True, 
            'elements': elements,
            'file_path': file_path
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


@app.route('/api/preview', methods=['POST'])
def api_preview():
    """
    API-Endpunkt zum Generieren einer Vorschau mit den geänderten Elementen
    """
    try:
        data = request.get_json()
        
        if not data or 'file' not in data or 'elements' not in data:
            return jsonify({
                'success': False, 
                'error': 'Ungültige Anfrage'
            }), 400
        
        file = data['file']
        file_path = f"{CONTENT_DIR}/{file}"
        elements = data['elements']
        
        # Prüfe ob Datei existiert
        if not os.path.exists(file_path):
            return jsonify({
                'success': False, 
                'error': 'Originaldatei nicht gefunden'
            }), 404
        
        # Wende Änderungen an
        modified_html = apply_elements_to_html(file, elements)
        
        # Erstelle temporäre Datei für Vorschau
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(modified_html)
            temp_file_path = temp_file.name
        
        # Sende die Datei zurück und lösche sie danach
        def remove_file(response):
            try:
                os.unlink(temp_file_path)
            except:
                pass
            return response
        
        return send_file(temp_file_path, as_attachment=False, mimetype='text/html')
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Fehler beim Generieren der Vorschau: {str(e)}'
        }), 500




@app.route('/api/save', methods=['POST'])
def api_save():
    """
    API-Endpunkt zum Speichern der geänderten HTML-Datei
    """
    try:
        data = request.get_json()
        
        if not data or 'file' not in data or 'elements' not in data:
            return jsonify({
                'success': False, 
                'error': 'Ungültige Anfrage'
            }), 400
        
        file = data['file']
        file_path = f"{CONTENT_DIR}/{file}"
        elements = data['elements']
        save_path = data.get('savePath', f"{CONTENT_DIR}")
        
        # Prüfe ob Originaldatei existiert
        if not os.path.exists(file_path):
            return jsonify({
                'success': False, 
                'error': 'Originaldatei nicht gefunden'
            }), 404
        
        # Generiere neuen Dateinamen
        
        original_filename = file
        name, ext = os.path.splitext(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{name}_edited_{timestamp}{ext}"
        final_save_path = os.path.join(CONTENT_DIR, new_filename)

        
        # Wende Änderungen an
        modified_html = apply_elements_to_html(file, elements)
        
        # Speichere die Datei
        with open(final_save_path, 'w', encoding='utf-8') as file:
            file.write(modified_html)
        
        return jsonify({
            'success': True, 
            'message': 'Datei erfolgreich gespeichert',
            'saved_to': file_path,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Fehler beim Speichern: {str(e)}'
        }), 500





@app.route('/api/file-info')
def api_file_info():
    """
    API-Endpunkt zum Abrufen von Datei-Informationen
    """
    file_path = request.args.get('file')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({
            'success': False, 
            'error': 'Datei nicht gefunden'
        }), 404
    
    try:
        stat = os.stat(file_path)
        
        return jsonify({
            'success': True,
            'file_info': {
                'path': file_path,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Fehler beim Abrufen der Datei-Informationen: {str(e)}'
        }), 500


# Zusätzliche Hilfsfunktionen

def validate_file_path(file_path):
    """
    Validiert den Dateipfad aus Sicherheitsgründen
    """
    # Verhindere Directory Traversal Angriffe
    if '..' in file_path or file_path.startswith('/'):
        return False
    
    # Nur bestimmte Dateierweiterungen erlauben
    allowed_extensions = ['.html', '.htm']
    if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
        return False
    
    return True


def backup_original_file(file_path):
    """
    Erstellt ein Backup der Originaldatei
    """
    try:
        backup_dir = os.path.join(os.path.dirname(file_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        original_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{timestamp}_{original_name}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        with open(file_path, 'r', encoding='utf-8') as original:
            content = original.read()
        
        with open(backup_path, 'w', encoding='utf-8') as backup:
            backup.write(content)
        
        return backup_path
        
    except Exception as e:
        print(f"Warnung: Backup konnte nicht erstellt werden: {str(e)}")
        return None


# Fehlerbehandlung
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False, 
        'error': 'Endpunkt nicht gefunden'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False, 
        'error': 'Interner Serverfehler'
    }), 500


if __name__ == '__main__':
    # Erstelle notwendige Verzeichnisse
    os.makedirs('content/new', exist_ok=True)
    
    # Starte die Anwendung
    app.run(debug=True, host='0.0.0.0', port=5000)