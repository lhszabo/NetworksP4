import socket, sys
import threading
import enum
import os
from time import gmtime, strftime
import time

BUFSIZE = 5242880 # 5 MB

http_head = "HTTP/1.1 "
date_head = "Date: "
content_length_head = "Content-Length: "
content_type_head = "Content-Type: "
ending_lines = "\r\n\r\n"
conn_ka = "Connection: Keep-Alive"
content_dir = "content"
secret_dir = "confidential/"
lock = threading.Lock()
status_dir = {"OK": "200", "Partial Content": "206", "Forbidden": "403", "Not Found": "404"}

plain_text = "text/plain"
css_text = "text/css"
html_text = "text/html"
image_gif = "image/gif"
image_jpeg = "image/jpeg"
image_png = "image/png"
video_mp4 = "video/mp4"
video_webm = "video/webm"
app_java = "application/javascript"
app_oct = "application/octet_stream" # others case
extension_dir = {"txt": plain_text, "css": css_text, "htm": html_text, "html": html_text, 
                 "gif": image_gif, "jpg": image_jpeg, "jpeg": image_jpeg, "png": image_png,
                 "mp4": video_mp4, "webm": video_webm, "ogg": video_webm, "js": app_java}

not_found_html = "<html><body><h1>404 Not Found</h1><p>The requested page was not found.</p></body></html>"
forbidden_html = "<html><body><h1>403 Forbidden</h1><p>The requested page is confidential.</p></body></html>"
    
def get_time():
  # from https://www.w3resource.com/python-exercises/date-time-exercise/python-date-time-exercise-29.php
  time_str = time.strftime("%a, %d %b %Y %H:%M:%S %p %Z", time.gmtime())
  time_str = time_str.replace("UTC", "GMT")
  if ("AM" in time_str):
    time_str = time_str.replace("AM", "")
  elif ("PM" in time_str):
    time_str = time_str.replace("PM", "")
  return time_str

# SAVING PARTIAL CONTENT FOR LATER
def check_file(filename): # return appropriate status code
  # check if forbidden -> contains "confidential" dir, checking first
  if (secret_dir in filename):
    return "Forbidden"
  # check if exists
  content_path = content_dir + filename
  if (os.path.exists(content_path)):
    return "OK"
  return "Not Found"
  
# will want to get more info later
def parse_method(msg):
  fields = msg.split("\r\n") # watch ending two \r\n's
  req = fields[0].split(" ")
  filename = req[1]
  return filename

def get_file_ext(filepath):
  fields = filepath.split("/")
  filename = fields[-1]
  name_ext = filename.split(".")
  ext = name_ext[-1]
  return ext
  
def build_resp(status_code, resp, filepath):
  http_header = http_head + status_code + " " + resp + "\r\n"
  date_header = "Date: " + get_time() + "\r\n"
  connection_header = conn_ka + "\r\n"
  
  if (resp == "Forbidden"): 
    content_type = content_type_head + html_text + "\r\n"
    final_resp = http_header + date_header + content_type + connection_header + \
                ending_lines + forbidden_html
    # print('final_resp forbidden', final_resp)
    return final_resp
  
  elif (resp == "OK"):
    file_size = str(os.path.getsize(filepath))
    content_len = content_length_head + file_size + "\r\n"
    
    ext = get_file_ext(filepath)
    file_type = extension_dir[ext]
    content_type = content_type_head + file_type + "\r\n"
    final_resp = http_header + date_header + content_len + content_type + connection_header + ending_lines
    # print('final resp ok', final_resp)
    return final_resp
  
  elif (resp == "Not Found"): # NOT including content length
    content_type = content_type_head + html_text + "\r\n"
    final_resp = http_header + date_header + content_type + connection_header + \
                ending_lines + not_found_html
    return final_resp
    
if __name__ == '__main__':
  port_num = None
  if len(sys.argv) != 2:
    sys.exit(-1)
  else:
    port_num = int(sys.argv[1])
    
  local_host = "localhost"
  # server = Server(port_num)
  
    
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
    print('msg', msg)
    filename = parse_method(msg)
    
    resp = check_file(filename) # resp = OK, Forbidden, Not Found, Partial Content
    content_path = None
    if (resp == "OK"):
      content_path = content_dir + filename # need path to get size of file
    status_code = status_dir[resp]
    final_resp = build_resp(status_code, resp, content_path)
    # print('final_resp', final_resp)
    # print('client info', server.client_addr, server.port)
    client_sock.send(final_resp.encode())
    client_sock.close()
    
    