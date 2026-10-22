import subprocess, sys, os, time, webbrowser

def main():
    # Change to the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Check if server is already running on port 5555
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_EXCLUSIVEADDRUSE: on Windows a plain bind() to 127.0.0.1 SUCCEEDS even
    # when another process holds 0.0.0.0:5555 (SO_REUSEADDR allows it), so the
    # old check reported "not running" and spawned a duplicate server that then
    # shared the port with the stale one. Exclusive bind makes the probe honest.
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    except (AttributeError, OSError):
        pass
    try:
        s.bind(('0.0.0.0', 5555))
        s.close()
    except OSError:
        print("السيرفر يعمل بالفعل على http://localhost:5555")
        webbrowser.open('http://localhost:5555')
        return
    s.close()

    # Start the server
    print("جاري تشغيل سيرفر ألعاب أمين...")
    print("افتح المتصفح على: http://localhost:5555")
    print()

    proc = subprocess.Popen([sys.executable, 'server.py'])

    # Wait a moment for server to start
    time.sleep(3)

    # Open browser
    webbrowser.open('http://localhost:5555')

    # Keep running until user presses Ctrl+C
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nإيقاف السيرفر...")
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    main()
