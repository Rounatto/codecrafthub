from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import json
import os
from datetime import datetime

DATA_FILENAME = 'courses.json'
ALLOWED_STATUSES = {'Not Started', 'In Progress', 'Completed'}

def get_data_path():
    return os.path.join(os.path.dirname(__file__), DATA_FILENAME)

def ensure_data_file():
    path = get_data_path()
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    if not os.path.exists(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
        except (IOError, OSError) as e:
            abort(500, description=f"Error initializing data file: {e}")

def load_data():
    path = get_data_path()
    try:
        ensure_data_file()
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (IOError, OSError) as e:
        abort(500, description=f"Error reading data file: {e}")
    except json.JSONDecodeError:
        return []

def save_data(data):
    path = get_data_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except (IOError, OSError) as e:
        abort(500, description=f"Error writing data file: {e}")

def get_next_id(items):
    if not items:
        return 1
    return max((item.get('id', 0) for item in items), default=0) + 1

def validate_course(payload, require_all=True):
    required_fields = {'name', 'description', 'target_date', 'status'}
    if require_all:
        missing = [f for f in required_fields if f not in payload]
        if missing:
            return False, f"Missing required field(s): {', '.join(missing)}"
    if 'target_date' in payload:
        try:
            datetime.strptime(payload['target_date'], '%Y-%m-%d')
        except ValueError:
            return False, "target_date must be in YYYY-MM-DD format"
    if 'status' in payload and payload['status'] not in ALLOWED_STATUSES:
        return False, f"Invalid status. Allowed values: {', '.join(ALLOWED_STATUSES)}"
    return True, ""

app = Flask(__name__)
CORS(app)  # ✅ CORS activé

@app.route('/api/courses', methods=['GET'])
def get_all_courses():
    return jsonify(load_data()), 200

@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    course = next((c for c in load_data() if c.get('id') == course_id), None)
    if course is None:
        abort(404, description="Course not found")
    return jsonify(course), 200

@app.route('/api/courses', methods=['POST'])
def create_course():
    payload = request.get_json(silent=True)
    if payload is None:
        abort(400, description="Request must contain JSON body")
    is_valid, msg = validate_course(payload, require_all=True)
    if not is_valid:
        abort(400, description=msg)
    data = load_data()
    course = {
        'id': get_next_id(data),
        'name': payload['name'],
        'description': payload['description'],
        'target_date': payload['target_date'],
        'status': payload['status'],
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }
    data.append(course)
    save_data(data)
    return jsonify(course), 201

@app.route('/api/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    payload = request.get_json(silent=True)
    if payload is None:
        abort(400, description="Request must contain JSON body")
    is_valid, msg = validate_course(payload, require_all=True)
    if not is_valid:
        abort(400, description=msg)
    courses = load_data()
    index = next((i for i, c in enumerate(courses) if c.get('id') == course_id), None)
    if index is None:
        abort(404, description="Course not found")
    updated = {
        'id': course_id,
        'name': payload['name'],
        'description': payload['description'],
        'target_date': payload['target_date'],
        'status': payload['status'],
        'created_at': courses[index].get('created_at', datetime.utcnow().isoformat() + 'Z')
    }
    courses[index] = updated
    save_data(courses)
    return jsonify(updated), 200

@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    courses = load_data()
    index = next((i for i, c in enumerate(courses) if c.get('id') == course_id), None)
    if index is None:
        abort(404, description="Course not found")
    courses.pop(index)
    save_data(courses)
    return jsonify({'message': 'Course deleted'}), 200

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': error.description}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': error.description}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': error.description}), 500

if __name__ == '__main__':
    ensure_data_file()
    app.run(debug=True)