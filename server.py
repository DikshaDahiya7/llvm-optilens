from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import subprocess
import os

class CompilerHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/compile':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            user_code = data.get("code", "")

            with open("temp.cpp", "w") as f:
                f.write(user_code)

            try:
                subprocess.run(["clang", "-S", "-emit-llvm", "-O0", "-Xclang", "-disable-O0-optnone", "temp.cpp", "-o", "s0.ll"], check=True)
                subprocess.run(["clang", "-S", "-emit-llvm", "-O2", "temp.cpp", "-o", "s2.ll"], check=True)

                with open("s0.ll") as f:
                    raw_ir = f.read()
                with open("s2.ll") as f:
                    opt_ir = f.read()

                raw_lines = len([l for l in raw_ir.splitlines() if l.strip() and not l.strip().startswith(';')])
                opt_lines = len([l for l in opt_ir.splitlines() if l.strip() and not l.strip().startswith(';')])
                allocas = raw_ir.count("alloca")
                opt_allocas = opt_ir.count("alloca")

                reduction = 0
                if raw_lines > 0:
                    reduction = round(((raw_lines - opt_lines) / raw_lines) * 100, 1)

                response = {
                    "raw_ir": raw_ir,
                    "opt_ir": opt_ir,
                    "raw_lines": raw_lines,
                    "opt_lines": opt_lines,
                    "raw_alloc": allocas,
                    "opt_alloc": opt_allocas,
                    "saved_pct": max(0, reduction)
                }
            except Exception as e:
                response = {"error": str(e)}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            super().do_POST()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    print(f"Serving on port {port}")
    httpd = HTTPServer(('0.0.0.0', port), CompilerHandler)
    httpd.serve_forever()