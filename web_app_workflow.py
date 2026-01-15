"""
Flask web interface for new Plotly Agent workflow.
Uses the complete pipeline: Communication -> Generator -> Router -> Optimizer -> Verifier
"""

import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

from plotly_agent.workflow_orchestrator import WorkflowOrchestrator

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store orchestrators by session
orchestrators = {}


def get_or_create_orchestrator(session_id: str) -> WorkflowOrchestrator:
    """Get existing orchestrator or create new one"""
    if session_id not in orchestrators:
        orchestrators[session_id] = WorkflowOrchestrator()
    return orchestrators[session_id]


@app.route('/')
def index():
    """Serve main chat interface"""
    return render_template('chat.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle CSV file upload"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'Only CSV files supported'}), 400

    try:
        # Generate session ID if needed
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())

        session_id = session['session_id']

        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
        file.save(filepath)

        # Load into orchestrator
        orchestrator = get_or_create_orchestrator(session_id)
        result = orchestrator.load_data(filepath)

        if result['success']:
            data_summary = result['data_summary']
            return jsonify({
                'success': True,
                'message': result['message'],
                'columns': data_summary['columns'],
                'shape': data_summary['shape']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat message"""
    try:
        data = request.json
        message = data.get('message', '').strip()

        if not message:
            return jsonify({'success': False, 'error': 'Empty message'}), 400

        # Get or create session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())

        session_id = session['session_id']
        orchestrator = get_or_create_orchestrator(session_id)

        # Process message through workflow
        response = orchestrator.chat(message)

        # Format response based on type
        result = {
            'success': True,
            'type': response['type'],
            'content': response['message'],
            'code': response.get('code'),
        }

        # Add workflow metadata if available
        if response.get('metadata'):
            result['metadata'] = response['metadata']

        return jsonify(result)

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset_session():
    """Reset conversation"""
    if 'session_id' in session:
        session_id = session['session_id']
        if session_id in orchestrators:
            orchestrators[session_id].new_session()

    return jsonify({'success': True, 'message': 'Session reset'})


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current session status"""
    if 'session_id' not in session:
        return jsonify({
            'session_exists': False
        })

    session_id = session['session_id']
    if session_id not in orchestrators:
        return jsonify({
            'session_exists': False
        })

    orchestrator = orchestrators[session_id]
    summary = orchestrator.get_session_summary()

    return jsonify({
        'session_exists': True,
        'data_loaded': summary['data_loaded'],
        'messages_count': summary['messages_count'],
        'current_story': summary['current_story']
    })


if __name__ == '__main__':
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  WARNING: OPENAI_API_KEY not set!")
        print("   Set it: export OPENAI_API_KEY='your-key'\n")

    print("\n" + "="*70)
    print(" "*15 + "PLOTLY AGENT - NEW WORKFLOW")
    print("="*70)
    print("\n🎨 Workflow Pipeline:")
    print("   User → Communication Agent → Plot Generator")
    print("        → Router → Optimizer → Verifier → User")
    print("\n🚀 Starting server...")
    print("   Navigate to: http://localhost:5000")
    print("\n📋 Features:")
    print("   • Natural conversation interface")
    print("   • Intelligent clarification questions")
    print("   • Multi-agent visualization pipeline")
    print("   • Chart-type specialized optimizers")
    print("   • Automatic code verification")
    print("\n⌨️  Press Ctrl+C to stop")
    print("="*70 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
