from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
import os
from flask_cors import CORS
from datetime import datetime, timezone



app = Flask(__name__)
CORS(app)

# Initialize Firestore DB
cred = credentials.Certificate('firebase.json')
default_app = initialize_app(cred)
db = firestore.client()  # this is the Firestore client

# Helper: get user document ref by fingerprint
def get_user_ref(fp):
    # you might put fingerprint as document ID under `users` collection
    return db.collection('user').document(fp)

@app.route('/api/user', methods=['POST'])
def user():
    data = request.json
    fingerprint = data.get('fingerprint')
    ip = data.get('ip')
    if not fingerprint:
        return jsonify({"error": "fingerprint required"}), 400

    user_ref = get_user_ref(fingerprint)
    doc = user_ref.get()

    now = datetime.now(timezone.utc)

    if doc.exists:
        user_data = doc.to_dict()
        visit_count = user_data.get('visit_count', 0) + 1
        # update fields
        user_ref.update({
            'last_visit': now,
            'visit_count': visit_count,
            'ip': ip
        })
    else:
        # first time
        visit_count = 1
        user_ref.set({
            'fingerprint': fingerprint,
            'ip': ip,
            'first_visit': now,
            'last_visit': now,
            'visit_count': visit_count,
            'button_clicks': {},  # empty map
            'link_clicks': {}
        })

    # fetch updated
    doc = user_ref.get()
    user_data = doc.to_dict()
    # Return relevant info
    return jsonify({
        'first_visit': user_data['first_visit'].isoformat(),
        'visit_count': user_data['visit_count'],
        'button_clicks': user_data.get('button_clicks', {}),
        'link_clicks': user_data.get('link_clicks', {})
    })


@app.route('/api/button_click', methods=['POST'])
def button_click():
    data = request.json
    fp = data.get('fingerprint')
    btn = data.get('button_id')
    if not (fp and btn):
        return jsonify({"error": "fingerprint and button_id required"}), 400

    user_ref = get_user_ref(fp)
    doc = user_ref.get()
    if not doc.exists:
        return jsonify({"error": "user not found"}), 404

    user_data = doc.to_dict()
    bc = user_data.get('button_clicks', {})
    bc_val = bc.get(btn, 0) + 1
    bc[btn] = bc_val

    user_ref.update({'button_clicks': bc})

    return jsonify({'button_id': btn, 'count': bc_val})


@app.route('/api/link_click', methods=['POST'])
def link_click():
    data = request.json
    fp = data.get('fingerprint')
    link = data.get('link_id')
    if not (fp and link):
        return jsonify({"error": "fingerprint and link_id required"}), 400

    user_ref = get_user_ref(fp)
    doc = user_ref.get()
    if not doc.exists:
        return jsonify({"error": "user not found"}), 404

    user_data = doc.to_dict()
    lc = user_data.get('link_clicks', {})
    lc_val = lc.get(link, 0) + 1
    lc[link] = lc_val

    user_ref.update({'link_clicks': lc})

    return jsonify({'link_id': link, 'count': lc_val})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
