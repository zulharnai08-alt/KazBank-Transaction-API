from app import create_app

app = create_app()

if __name__ == "__main__":
    # Disable the reloader so the shared pool is initialized only once.
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
