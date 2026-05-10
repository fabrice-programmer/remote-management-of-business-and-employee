from flask_socketio import emit

def register_socket_events(socketio):

    @socketio.on('message')
    def handle_message(data):
        emit('message', data, broadcast=True)
