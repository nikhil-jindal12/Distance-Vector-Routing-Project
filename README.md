# Distance Vector Routing Implementation

This project implements the Distance Vector (DV) routing algorithm using UDP and Python. The implementation simulates a network topology where routers exchange routing information to discover optimal paths.

## Project Structure

- `server.py` - The central server that manages router connections and forwards messages
- `client.py` - The router implementation that executes the DV algorithm
- `config.txt` - Network topology configuration file
- `start_routing.bash` - Bash script to start all components
- `README.md` - This file

## Prerequisites

- Python 3.7+
- No additional libraries required (uses only standard library)

## Configuration File Format

The `config.txt` file defines the network topology using the following format:
```
router_id <neighbor, cost>, <neighbor, cost>, ...
```
Where `-1` indicates no direct connection between routers.

## Compilation and Execution

### Using the Automated Scripts

The easiest way to run the project is using the provided scripts:

```bash
# Make scripts executable
chmod +x start_routing.bash

# Run the bash script (recommended)
./start_routing.bash
```

### Manual Execution

#### Starting the Server

```bash
# Make sure the server script has execution permissions
chmod +x server.py

# Start the server
python3 server.py <port> <config_file>

# Example:
python3 server.py 5555 config.txt
```

#### Starting the Routers

Each router runs as a separate process. Open a new terminal for each router:

```bash
# Make sure the client script has execution permissions
chmod +x client.py

# Start each router
python3 client.py <router_id> <server_host> <server_port>

# Examples:
# Terminal 1:
python3 client.py u localhost 5555

# Terminal 2:
python3 client.py x localhost 5555

# Terminal 3:
python3 client.py w localhost 5555

# Terminal 4:
python3 client.py v localhost 5555

# Terminal 5:
python3 client.py y localhost 5555

# Terminal 6:
python3 client.py z localhost 5555
```

## How It Works

1. **Parallel Initialization**: All routers start simultaneously and join the network
2. **Neighbor Discovery**: Each router receives its neighbor information from the server
3. **Asynchronous Updates**: Routers exchange distance vectors using non-blocking UDP
4. **DV Algorithm**: 
   - Routers continuously exchange distance vectors with neighbors
   - Each router updates its routing table using the Bellman-Ford equation
   - Updates are sent periodically (every 3 cycles) to ensure convergence
5. **Convergence**: The algorithm terminates when no changes occur for 10 consecutive cycles
6. **Continued Operation**: Routers continue running after convergence to help late joiners
7. **Output**: Final forwarding tables are displayed with staggered timing

## Expected Output

The program produces clean output showing only the final converged forwarding tables:

```
==================================================
FORWARDING TABLE FOR ROUTER u
==================================================
Destination | Cost | Next Hop
---------------------------------
u           |    0 | u
v           |    6 | w
w           |    3 | w
x           |    5 | x
y           |   10 | w
z           |   12 | w
==================================================

==================================================
FORWARDING TABLE FOR ROUTER v
==================================================
Destination | Cost | Next Hop
---------------------------------
u           |    6 | w
v           |    0 | v
w           |    3 | w
x           |    7 | w
y           |    4 | y
z           |    6 | y
==================================================

# ... and so on for all routers
```

Each forwarding table appears with a 1.5-second delay to ensure readable output.

## Algorithm Details

- Uses Bellman-Ford equation: `d_x(y) = min_v{c(x,v) + d_v(y)}`
- Implements split horizon (no poisoned reverse)
- Converges when no routing table changes occur for 10 consecutive cycles
- Routers use non-blocking I/O for asynchronous communication
- Periodic updates ensure full network convergence

## Error Handling

- Retries failed operations
- Exits with traceback if errors persist
- Handles network unreliability gracefully
- Non-blocking sockets prevent hanging

## Testing

The implementation has been tested with the topology provided in Figure 1 of the project specification.

## Notes

- Routers run on the same machine using different ports
- UDP is used for communication between routers and server
- All code follows PEP8 formatting guidelines
- Parallel operation ensures faster convergence
- Clean output shows only essential information