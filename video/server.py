from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler
import os

os.chdir(".")

server = HTTPServer(
    ("localhost", 8000),
    SimpleHTTPRequestHandler
)

print("Server running at:")
print("http://localhost:8000")

server.serve_forever()