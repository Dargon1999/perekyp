from web import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Run the server on all interfaces (0.0.0.0) so it's accessible
    # Use port 5000 by default
    print("Starting Perekyp Web Server...")
    print("Go to http://localhost:5000 to view the new design.")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
