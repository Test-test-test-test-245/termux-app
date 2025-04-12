from flask_socketio import emit, join_room, leave_room
from app.services.terminal_service import TerminalService

terminal_service = TerminalService()

def register_socket_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        emit('connected', {'status': 'connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        # Clean up any specific resources for this client if needed
        pass

    @socketio.on('join')
    def handle_join(data):
        """Join a specific terminal session room"""
        session_id = data.get('session_id')
        if not session_id:
            emit('error', {'message': 'Session ID is required'})
            return
        
        session = terminal_service.get_session(session_id)
        if not session:
            emit('error', {'message': 'Session not found'})
            return
        
        join_room(session_id)
        emit('joined', {
            'session_id': session_id,
            'status': 'joined',
            'session': session.to_dict()
        })

    @socketio.on('leave')
    def handle_leave(data):
        """Leave a specific terminal session room"""
        session_id = data.get('session_id')
        if session_id:
            leave_room(session_id)
            emit('left', {'status': 'left', 'session_id': session_id})

    @socketio.on('input')
    def handle_input(data):
        """Handle terminal input from client"""
        session_id = data.get('session_id')
        input_data = data.get('data')
        
        if not session_id or not input_data:
            emit('error', {'message': 'Session ID and input data are required'})
            return
        
        try:
            terminal_service.write_to_session(session_id, input_data)
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('resize')
    def handle_resize(data):
        """Handle terminal resize event"""
        session_id = data.get('session_id')
        cols = data.get('cols')
        rows = data.get('rows')
        
        if not session_id or not cols or not rows:
            emit('error', {'message': 'Session ID, cols, and rows are required'})
            return
        
        try:
            terminal_service.resize_session(session_id, cols, rows)
            emit('resized', {
                'session_id': session_id,
                'cols': cols,
                'rows': rows
            })
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('terminate')
    def handle_terminate(data):
        """Handle terminal session termination"""
        session_id = data.get('session_id')
        
        if not session_id:
            emit('error', {'message': 'Session ID is required'})
            return
        
        try:
            terminal_service.terminate_session(session_id)
            emit('terminated', {'session_id': session_id})
        except Exception as e:
            emit('error', {'message': str(e)})
