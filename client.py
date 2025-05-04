#!/usr/bin/env python3
import socket
import json
import time
import threading
import sys
import traceback

INF = float('inf')

class Router:
    def __init__(self, router_id, server_host, server_port):
        self.router_id = router_id
        self.server_host = server_host
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dv = {}  # Destination -> (cost, next_hop)
        self.neighbor_dvs = {}  # neighbor_id -> {dest: cost}
        self.neighbors = []  # [(neighbor_id, cost)]
        self.running = True
        self.stable_cycles = 0
        self.cycle_count = 0
        self.lock = threading.Lock()
        self.has_printed = False  # Track if we've printed the final table
        
    def join_network(self):
        """Send JOIN message to server"""
        join_msg = {
            'type': 'JOIN',
            'router_id': self.router_id
        }
        self.sock.sendto(json.dumps(join_msg).encode(), (self.server_host, self.server_port))
    
    def wait_for_neighbors(self):
        """Wait for server to send neighbor information"""
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                message = json.loads(data.decode())
                
                if message.get('type') == 'NEIGHBORS':
                    self.neighbors = message.get('neighbors', [])
                    print(f"Received neighbors: {self.neighbors}")
                    break
            except Exception as e:
                print(f"Error waiting for neighbors: {e}")
                if not self.running:
                    break
    
    def initialize_dv(self):
        """Initialize distance vector with direct costs"""
        # Set cost to self as 0
        self.dv[self.router_id] = (0, self.router_id)
        
        # Set costs to direct neighbors
        for neighbor, cost in self.neighbors:
            self.dv[neighbor] = (cost, neighbor)
        
        # Initialize costs to non-neighbors as infinity
        all_routers = ['u', 'x', 'w', 'v', 'y', 'z']
        for router in all_routers:
            if router not in self.dv:
                self.dv[router] = (INF, None)
        
        print(f"Initial DV for {self.router_id}: {self.dv}")
    
    def send_update(self):
        """Send distance vector update to server"""
        dv_to_send = {dest: cost for dest, (cost, _) in self.dv.items()}
        update_msg = {
            'type': 'UPDATE',
            'router_id': self.router_id,
            'dv': dv_to_send
        }
        self.sock.sendto(json.dumps(update_msg).encode(), (self.server_host, self.server_port))
        print(f"Sent update from {self.router_id}: {dv_to_send}")
    
    def process_update(self, from_id, neighbor_dv):
        """Process received distance vector update"""
        if from_id not in [n[0] for n in self.neighbors]:
            return  # Ignore updates from non-neighbors
        
        print(f"Received update from {from_id}: {neighbor_dv}")
        
        # Store neighbor's DV
        self.neighbor_dvs[from_id] = neighbor_dv
        
        # Get cost to this neighbor
        cost_to_from = next(cost for n, cost in self.neighbors if n == from_id)
        
        # Update our DV using Bellman-Ford
        updated = False
        new_dv = self.dv.copy()
        
        for dest, (current_cost, _) in self.dv.items():
            if dest in neighbor_dv:
                new_cost = cost_to_from + neighbor_dv[dest]
                if new_cost < current_cost:
                    new_dv[dest] = (new_cost, from_id)
                    updated = True
        
        # Check if our current next hops are still optimal
        for dest, (cost, next_hop) in self.dv.items():
            if next_hop and next_hop in self.neighbor_dvs:
                if dest in self.neighbor_dvs[next_hop]:
                    new_cost = next(c for n, c in self.neighbors if n == next_hop) + self.neighbor_dvs[next_hop][dest]
                    if new_cost != cost:
                        # Need to re-evaluate this path
                        min_cost = INF
                        best_next_hop = None
                        
                        for neighbor, neighbor_cost in self.neighbors:
                            if neighbor in self.neighbor_dvs and dest in self.neighbor_dvs[neighbor]:
                                total_cost = neighbor_cost + self.neighbor_dvs[neighbor][dest]
                                if total_cost < min_cost:
                                    min_cost = total_cost
                                    best_next_hop = neighbor
                        
                        if min_cost < cost:
                            new_dv[dest] = (min_cost, best_next_hop)
                            updated = True
        
        if updated:
            self.dv = new_dv
            print(f"Updated DV for {self.router_id}: {self.dv}")
            self.stable_cycles = 0
            self.send_update()
        else:
            print(f"No updates needed for {self.router_id}")
    
    def print_forwarding_table(self):
        """Print the final forwarding table"""
        print("\n" + "=" * 50)
        print(f"FORWARDING TABLE FOR ROUTER {self.router_id}")
        print("=" * 50)
        print("Destination | Cost | Next Hop")
        print("-" * 33)
        
        sorted_dests = sorted(self.dv.keys())
        for dest in sorted_dests:
            cost, next_hop = self.dv[dest]
            if cost == INF:
                print(f"{dest:11} | INF  | -")
            else:
                print(f"{dest:11} | {cost:4} | {next_hop if next_hop else '-'}")
        print("=" * 50)
    
    def run(self):
        """Main client loop"""
        try:
            # Add staggered start based on router ID to avoid output collision
            router_order = {'u': 0, 'v': 1, 'w': 2, 'x': 3, 'y': 4, 'z': 5}
            if self.router_id in router_order:
                start_delay = router_order[self.router_id] * 0.5
                time.sleep(start_delay)
            
            # Join the network
            self.join_network()
            self.wait_for_neighbors()
            self.initialize_dv()
            
            # Start receiving thread immediately
            receive_thread = threading.Thread(target=self.receive_updates)
            receive_thread.daemon = True
            receive_thread.start()
            
            # Wait a moment for all routers to join
            time.sleep(2)
            
            # Send initial update
            self.send_update()
            
            # Main loop - send periodic updates and check convergence
            while self.running:
                time.sleep(1)
                
                with self.lock:
                    self.cycle_count += 1
                    self.stable_cycles += 1
                    
                    # Send periodic updates to help slow joiners
                    if self.cycle_count % 3 == 0:  # Send every 3 cycles
                        self.send_update()
                    
                    # Check if algorithm has converged
                    if self.stable_cycles >= 10 and not self.has_printed:
                        # Add staggered output based on router ID
                        output_delay = router_order.get(self.router_id, 0) * 1.5  # 1.5 seconds between outputs
                        time.sleep(output_delay)
                        
                        print(f"\nAlgorithm converged for {self.router_id} after {self.cycle_count} cycles")
                        self.print_forwarding_table()
                        self.has_printed = True
                    
                    # Continue running for a while to help late joiners
                    if self.has_printed and self.cycle_count >= 40:
                        self.running = False
                        break
        except Exception as e:
            print(f"Error in router {self.router_id}: {e}")
            traceback.print_exc()
        finally:
            self.sock.close()
    
    def receive_updates(self):
        """Thread to receive updates from server"""
        # Set socket to non-blocking
        self.sock.setblocking(False)
        
        while self.running:
            try:
                # Check for incoming messages
                data, _ = self.sock.recvfrom(4096)
                message = json.loads(data.decode())
                
                if message.get('type') == 'UPDATE':
                    from_id = message.get('from')
                    neighbor_dv = message.get('dv', {})
                    print(f"Router {self.router_id}: Received UPDATE from {from_id}")
                    
                    with self.lock:
                        self.process_update(from_id, neighbor_dv)
            except BlockingIOError:
                # No data available, continue
                time.sleep(0.1)
            except Exception as e:
                if self.running:
                    print(f"Error receiving update in {self.router_id}: {e}")
                    traceback.print_exc()
                    time.sleep(0.5)  # Prevent tight error loop

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python client.py <router_id> <server_host> <server_port>")
        sys.exit(1)
    
    router_id = sys.argv[1]
    server_host = sys.argv[2]
    server_port = int(sys.argv[3])
    
    router = Router(router_id, server_host, server_port)
    router.run()