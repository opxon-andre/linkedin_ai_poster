from flask import Flask, render_template_string, request, jsonify, send_file, render_template
import os
import re
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
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



editable_elements = ['text', 'image']
#editable_elements = ['confirmed', 'origin', 'text', 'image']


def extract_post_elements_local(html_file):
    html_file = f"{CONTENT_DIR}/{html_file}"

    try:
        all_elements = get_posting_data(html_file)
        elements = {}
        # select only editable fields:
        for item in editable_elements:
            elements[item] = all_elements.get(item)
            
        #print(f"Elements: {elements}")
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

        os.unlink(temp_file)

        return str(soup)
        
    except Exception as e:
        raise Exception(f"Fehler beim Anwenden der Änderungen: {str(e)}")




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
#        print(f"Preview ELements: {elements}")

        image = elements.get('image')
        if image.startswith("http"):
            print(f"Use url for Image: {image}")
        else:
            image_file = os.path.basename(image)
            # set path according to filesystem
            images_dir = os.path.join(CONTENT_DIR, "../images")
            #image = f"{images_dir}/{image_file}"
            image = f"/content/images/{image_file}"
            url = request.host_url + "/content/images/" + image_file
            elements.update({'image':url})
        
#        print(f"Preview ELements 2: {elements}")

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
        
        image = elements.get('image')
        if image.startswith("http"):
            print(f"Use url for Image: {image}")
        else:
            image_file = os.path.basename(image)
            # set path according to filesystem
            images_dir = os.path.join(CONTENT_DIR, "../images")
            #image = f"{images_dir}/{image_file}"
            image = f"/content/images/{image_file}"
            elements.update({'image':image})

        print(f"SAVE Elements: {elements}")
        save_path = data.get('savePath', f"{CONTENT_DIR}")
        
        # Prüfe ob Originaldatei existiert
        if not os.path.exists(file_path):
            return jsonify({
                'success': False, 
                'error': 'Originaldatei nicht gefunden'
            }), 404
        
        # Generiere neuen Dateinamen
        
        original_filename = file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(original_filename)
        if not name.startswith("post"):
            new_filename = f"post_{timestamp}.html"
        else:
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



def api_images():
    """
    API-Endpunkt zum Abrufen aller verfügbaren Bilder aus /content/images
    """
    try:
        images_dir = os.path.join(CONTENT_DIR, "../images")
        #images_dir = '/content/images'
        
        # Prüfe ob das Verzeichnis existiert
        if not os.path.exists(images_dir):
            return jsonify({
                'success': False,
                'error': 'Bilderverzeichnis nicht gefunden'
            }), 404
        
        # Unterstützte Bildformate
        supported_formats = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp')
        
        # Alle Bilddateien im Verzeichnis finden
        images = []
        for filename in os.listdir(images_dir):
            if filename.lower().endswith(supported_formats):
                # Zusätzliche Informationen über das Bild sammeln
                filepath = os.path.join(images_dir, filename)
                stat = os.stat(filepath)
                
                images.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Nach Änderungsdatum sortieren (neueste zuerst)
        images.sort(key=lambda x: x['modified'], reverse=True)
        
        # Nur Dateinamen für die Frontend-Anzeige zurückgeben
        image_filenames = [img['filename'] for img in images]
        
        return jsonify({
            'success': True,
            'images': image_filenames,
            'count': len(image_filenames),
            'details': images  # Zusätzliche Details falls benötigt
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Laden der Bilder: {str(e)}'
        }), 500
    


def serve_image(filename):
    """
    Statische Bilddateien aus /content/images bereitstellen
    """
    images_dir = os.path.join(CONTENT_DIR, "../images")
    filename = os.path.basename(filename)
    
    
    # Sicherheitsprüfung gegen Directory Traversal
    if '..' in filename or '/' in filename:
        return jsonify({'error': 'Ungültiger Dateiname'}), 400
    
    filepath = os.path.join(images_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Bild nicht gefunden'}), 404
    
    return send_file(filepath)


def api_upload_image():
    """
    API-Endpunkt zum Hochladen neuer Bilder
    """
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Keine Datei ausgewählt'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Keine Datei ausgewählt'
            }), 400
        
        # Prüfe Dateierweiterung
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                'success': False,
                'error': 'Ungültiges Dateiformat'
            }), 400
        
        # Sichere den Dateinamen
        filename = secure_filename(file.filename)
        
        # Erstelle Verzeichnis falls nicht vorhanden
        images_dir = os.path.join(CONTENT_DIR, "../images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Speichere die Datei
        filepath = os.path.join(images_dir, filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'message': 'Bild erfolgreich hochgeladen',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Hochladen: {str(e)}'
        }), 500
