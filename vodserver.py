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
accept_ranges_head = "Accept-Ranges: bytes" + "\r\n"
content_ranges_head = "Content-Range: bytes "
ending_line = "\r\n"
conn_ka = "Connection: Keep-Alive\r\n"
content_dir = "content"
secret_dir = "confidential/"
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
app_oct = "application/octet-stream" # others case
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
    time_str = time_str.replace("AM ", "")
  elif ("PM" in time_str):
    time_str = time_str.replace("PM ", "")
  return time_str

def check_file(filename): # return appropriate status code
  # check if forbidden -> contains "confidential" dir, checking first
  if (secret_dir in filename):
    return "Forbidden"
  # check if exists
  content_path = content_dir + filename
  if (os.path.exists(content_path) and os.path.getsize(content_path) <= BUFSIZE):
    return "OK"
  if (os.path.exists(content_path) and os.path.getsize(content_path) > BUFSIZE):
    return "Partial Content"
  return "Not Found"
  
def get_range_index(bytes_range):
  fields = bytes_range.split("=")
  range_index = fields[1]
  if ("-" in range_index):
    range_index = range_index.replace("-", "")
  return int(range_index)

# will want to get more info later
# Range: bytes=22904832-
def parse_method(msg):
  fields = msg.split("\r\n") # watch ending two \r\n's
  req = fields[0].split(" ")
  filename = req[1]
  range_index = None
  found_range_index = False
  for field in fields:
    header = field.split(" ")
    # should be [Range:, bytes=22904832-]
    # print('header', header)
    if (header[0] == "Range:"):
      range_index = get_range_index(header[1])
      print('range_index=', range_index)
      # if ("-" in range_index):
      #   range_index = range_index.replace("-", "")
      #   range_index = int(range_index)
      found_range_index = True
  if (not found_range_index):
    range_index = 0
  return filename, range_index

def get_file_ext(filepath):
  fields = filepath.split("/")
  filename = fields[-1]
  name_ext = filename.split(".")
  ext = name_ext[-1]
  return ext
  
def build_resp(status_code, resp, filepath, range_index):
  http_header = http_head + status_code + " " + resp + "\r\n"
  date_header = "Date: " + get_time() + "\r\n"
  # print('building response')
  
  if (resp == "Forbidden"): 
    content_type = content_type_head + html_text + "\r\n"
    final_resp = http_header + date_header + content_type + conn_ka + \
                ending_line + forbidden_html
    final_resp = final_resp.encode()
    return final_resp
  
  # to avoid timeout ONLY
  elif (resp == "OK"): # file is smaller than 5 MB
    # print("SMALLER FILE")
    file_size = str(os.path.getsize(filepath))
    content_len = content_length_head + file_size + "\r\n"
    
    ext = get_file_ext(filepath)
    file_type = None
    if (ext not in extension_dir):
      file_type = app_oct
    else:
      file_type = extension_dir[ext]
    content_type = content_type_head + file_type + "\r\n"
    f = open(filepath, "rb")
    chunk = f.read(BUFSIZE)
    f.close()
    final_resp = http_header + date_header + content_len + content_type + \
                 conn_ka + ending_line
    final_resp = final_resp.encode()
    final_resp += chunk 
    return final_resp
  
  elif (resp == "Not Found"): # NOT including content length
    content_type = content_type_head + html_text + "\r\n"
    final_resp = http_header + date_header + content_type + conn_ka + \
                ending_line + not_found_html
    final_resp = final_resp.encode()
    return final_resp
  elif (resp == "Partial Content"):
    # use range index
    # print('range index', range_index)
    # print('path', filepath)
    file_size = str(os.path.getsize(filepath))
    # print('size', file_size)
    content_len = content_length_head + file_size + "\r\n"
    
    ext = get_file_ext(filepath)
    file_type = None
    if (ext not in extension_dir):
      file_type = app_oct
    else:
      file_type = extension_dir[ext]
    content_type = content_type_head + file_type + "\r\n"
    
    f = open(filepath, "rb")
    f.seek(range_index, 0)
    chunk = f.read(BUFSIZE)
    f.close()
    
    end_range_index = range_index + BUFSIZE
    if (end_range_index > int(file_size)):
      end_range_index = int(file_size)
    content_range = content_ranges_head + str(range_index) + "-" + str(end_range_index) \
                    + "/" + file_size + "\r\n"
    
    final_resp = http_header + date_header + content_len + content_type + \
                 conn_ka + content_range + ending_line
                 
    print('final resp', final_resp)
    final_resp = final_resp.encode()
    final_resp += chunk 
    # print('final resp', final_resp)
    return final_resp

def http_parser_thread(msg, client_sock):
  filename, range_index = parse_method(msg)
  # if (range_index != 0):
  print('msg', msg)
  # print('filename', filename)
  resp = check_file(filename) # resp = OK, Forbidden, Not Found, Partial Content
  # print('resp', resp)
  content_path = None
  if (resp == "OK" or resp == "Partial Content"):
    content_path = content_dir + filename # need path to get size of file
  status_code = status_dir[resp]
  final_resp = build_resp(status_code, resp, content_path, range_index)
  try:
    client_sock.sendall(final_resp)
    client_sock.close()
  except:
    pass
  
if __name__ == '__main__':
  port_num = None
  if len(sys.argv) != 2:
    sys.exit(-1)
  else:
    port_num = int(sys.argv[1])
    
  local_host = "localhost"  
    
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  try:
    s.bind(("localhost", port_num))
    s.listen(1)
  except:
    pass
  
  while True:
    try:
      # print('in while true')
      client_sock, client_addr = s.accept()
      msg, addr = client_sock.recvfrom(BUFSIZE)
      msg = msg.decode()
      http_parser = threading.Thread(target=http_parser_thread, args=(msg, client_sock), daemon=True)
      http_parser.start()
    except:
      pass
    
    