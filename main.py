from dotenv import load_dotenv
from logger import server_log
from rabbit import rabbit_manager


VERSION = "0.1"


if __name__ == "__main__":
    server_log.info(f"Starting server (version {VERSION})")
    try:
        rabbit_manager.start_listening()
        
    except Exception as e:
        server_log.info(f"Failed to initialize service: {str(e)}")
        exit(1)
