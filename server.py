#!/usr/bin/env python3
import socket
import threading
import json
import traceback

class Server:
    def __init__(self, port, config_file):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', port))
        self.router_info = {}  # router_id -> {ip, port, neighbors}
        self.client_addresses = {}  # router_id -> (ip, port)
        self.load_config(config_file)
        self.running = True
        self.lock = threading.Lock()
        
    def load_config(self, config_file):
        """Load router topology from config file"""
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    
                    router_id = line[0]
                    parts = line[1:].split('>, ')
                    if not parts:
                        continue
                        
                    # router_id = parts[0]
                    neighbors = []
                    
                    # Parse <node, cost> pairs - each might end with a comma
                    for i in range(len(parts)):
                        # Remove trailing comma if present and brackets
                        pair_str = parts[i].strip().rstrip(',').lstrip('<').rstrip('>')
                        nodecost = pair_str.split(', ')
                        node = nodecost[0]
                        cost = int(nodecost[1])
                        if cost != -1:  # Only add connected neighbors
                            neighbors.append((node, cost))
                    
                    self.router_info[router_id] = {
                        'neighbors': neighbors,
                        'ip': '',
                        'port': 0
                    }
                    print(f"Loaded {router_id}: {neighbors}")  # Debug line
            print(f"Loaded topology for routers: {list(self.router_info.keys())}")
        except Exception as e:
            print(f"Error loading config file: {e}")
            traceback.print_exc()
            exit(1)
    
    def handle_join(self, router_id, client_addr):
        """Handle router JOIN request"""
        print(f"Received JOIN from router {router_id}")
        
        with self.lock:
            if router_id not in self.router_info:
                print(f"Error: Unknown router ID {router_id}")
                return
            
            # Store client address
            self.client_addresses[router_id] = client_addr
            self.router_info[router_id]['ip'] = client_addr[0]
            self.router_info[router_id]['port'] = client_addr[1]
            
            # Get neighbor information
            neighbors = self.router_info[router_id]['neighbors']
            print(f"Router {router_id} has neighbors: {neighbors}")  # Debug line
            
            # Send neighbor information back
            response = {
                'type': 'NEIGHBORS',
                'neighbors': neighbors
            }
            
            response_json = json.dumps(response).encode()
            self.sock.sendto(response_json, client_addr)
            print(f"Sent neighbor info to {router_id}: {neighbors}")
    
    def forward_update(self, from_id, update_data):
        """Forward UPDATE message to neighbors"""
        try:
            with self.lock:
                if from_id not in self.router_info:
                    return
                
                # Get neighbors of the sender
                neighbors = self.router_info[from_id]['neighbors']
                forward_msg = {
                    'type': 'UPDATE',
                    'from': from_id,
                    'dv': update_data.get('dv', [])
                }
                forward_json = json.dumps(forward_msg).encode()
                
                # Forward to each neighbor
                for neighbor_id, _ in neighbors:
                    if neighbor_id in self.client_addresses:
                        addr = self.client_addresses[neighbor_id]
                        self.sock.sendto(forward_json, addr)
                        print(f"Forwarded update from {from_id} to {neighbor_id}")
        except Exception as e:
            print(f"Error forwarding update: {e}")
            traceback.print_exc()
    
    def run(self):
        """Main server loop"""
        print(f"Server running on port {self.port}")
        print("Waiting for routers to join...")
        
        try:
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    message = json.loads(data.decode())
                    msg_type = message.get('type')
                    
                    if msg_type == 'JOIN':
                        router_id = message.get('router_id')
                        self.handle_join(router_id, addr)
                    
                    elif msg_type == 'UPDATE':
                        from_id = message.get('router_id')
                        self.forward_update(from_id, message)
                    
                    elif msg_type == 'TERMINATE':
                        print("Received terminate signal")
                        self.running = False
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error in server loop: {e}")
                    traceback.print_exc()
                    if not self.running:
                        break
        except KeyboardInterrupt:
            print("\nServer shutting down")
        finally:
            self.sock.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python server.py <port> <config_file>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    config_file = sys.argv[2]
    
    server = Server(port, config_file)
    server.run()