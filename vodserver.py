import socket, sys
import threading
import enum
import os
from time import gmtime, strftime
import time

BUFSIZE = 5242880 # 5 MB
HTTP_HEAD = "HTTP/1.1 "
CONN_KA = "Connection: Keep-Alive"
content_dir = "content"
secret_dir = "content/confidential"
lock = threading.Lock()
status_dir = {"OK": "200", "Partial Content": "206", "Forbidden": "403", "Not Found": "404"}


class server_states(enum.Enum):
  waiting = 1
  sending = 2
  
class Server():
  def __init__(self, port):
    self.state = server_states.waiting
    
def get_time():
  time_str = time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime())+ " GMT"
  return time_str

# SAVING PARTIAL CONTENT FOR LATER
def check_file(filename):
  # check if forbidden
  secret_path = secret_dir + filename
  if (os.path.exists(secret_path)):
    return "Forbidden"
  # check if exists
  content_path = content_dir + filename
  # print('content path', content_path)
  if (os.path.exists(content_path)):
    return "OK"
  return "Not Found"
  
def parse_method(msg):
  fields = msg.split("\r\n")
  req = fields[0].split(" ")
  filename = req[1]
  return filename

def build_resp(status_code, resp):
  line_1 = HTTP_HEAD + status_code + " " + resp + "\r\n"
  line_2 = "Date: " + get_time() + "\r\n"
  line_3 = CONN_KA + "\r\n"
  final_resp = line_1 + line_2 + line_3
  return final_resp
  
  
def rx_thread(name, socket, server):
  while True:
    try:
      conn, addr = socket.accept() # could be how different clients are differentiated
      server.client_addr = addr[0]
      # print('addr', addr)
      msg, addr = conn.recvfrom(BUFSIZE)
      msg = msg.decode()
      filename = parse_method(msg)
      server.filename = filename
    except:
      pass

def tx_thread(name, socket, server):
  while True:
    if (server.filename != None):
      resp = check_file(server.filename)
      status_code = status_dir[resp]
      final_resp = build_resp(status_code, resp)
      # print('client info', server.client_addr, server.port)
      socket.sendto(final_resp.encode(), (server.client_addr, server.port))
    
if __name__ == '__main__':
  port_num = None
  if len(sys.argv) != 2:
    sys.exit(-1)
  else:
    port_num = int(sys.argv[1])
    
  local_host = "localhost"
  server = Server(port_num)
  
    
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind(("localhost", port_num))
  s.listen(1)
  
  # tx = threading.Thread(target=tx_thread, args=(1, s, server), daemon=True)
  # tx.start()
  
  # rx = threading.Thread(target=rx_thread, args=(2, s, server), daemon=True)
  # rx.start()
  
  while True:
    client_sock, client_addr = s.accept()
    msg, addr = client_sock.recvfrom(BUFSIZE)
    msg = msg.decode()
    filename = parse_method(msg)
    
    resp = check_file(filename)
    status_code = status_dir[resp]
    final_resp = build_resp(status_code, resp)
    # print('final_resp', final_resp)
    # print('client info', server.client_addr, server.port)
    client_sock.send(final_resp.encode())
    client_sock.close()
    
    