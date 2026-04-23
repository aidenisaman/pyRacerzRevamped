"""Thin TCP networking layer for pyRacerz multiplayer.

Messages are newline-terminated JSON objects sent over a TCP socket.
Sending and receiving run on background daemon threads so the pygame
main-thread never blocks waiting for I/O.

Usage::

    # Server (host):
    srv = NetworkServer()
    srv.start()
    srv.broadcast({"type": "chat", "sender": "HOST", "text": "hi"})
    for msg in srv.recv_all():   # call each frame
        ...
    srv.stop()

    # Client (joiner):
    cli = NetworkClient("192.168.1.5")
    ok  = cli.connect()
    cli.send({"type": "hello", "name": "ALICE", "color": 3, "level": 2})
    for msg in cli.recv_all():   # call each frame
        ...
    cli.disconnect()

Message types used by the game
-------------------------------
  hello    : {"type":"hello",  "name":"...", "color":1, "level":1}
                                                        client → host on connect
  assigned : {"type":"assigned", "pid":1}              host → client (phase 2)
  players  : {"type":"players","list":[...],
              "roster":[{pid,name,color,level},...]}    host → all, updated roster
  chat     : {"type":"chat",   "sender":"...","text":"..."}  any direction
  start    : {"type":"start",  "track":"...","reverse":0,
              "laps":3,"host_name":"...","host_color":1,
              "host_level":1,
              "roster":[{pid,name,color,level},...]}    host → all before race
  state    : {"type":"state",  "pid":0,
              "x":512,"y":384,"a":1570,
              "br":0,"sl":0,"bl":0}                    any direction, per frame
                                                        (pid=0 host; pid>0 client)
  finish   : {"type":"finish"}                         host → all, race over
  bye      : {"type":"bye"}                            client → host on leave

Phase-2 notes
-------------
* ``_seq`` is injected automatically on every outgoing ``state`` message by
  ``_Connection._sender``; the receiver silently drops state packets whose
  ``_seq`` is not strictly greater than the last seen value, eliminating
  stale-state glitches.
* ``TCP_NODELAY`` is set on every socket so Nagle batching cannot add
  per-frame latency.
* ``NetworkServer.register_player()`` assigns a stable ``pid`` to each
  client when their ``hello`` is processed; pid 0 is always the host.
* ``NetworkClient.send_state()`` is the phase-2 per-frame send helper.
"""

import json
import queue
import socket
import threading

DEFAULT_PORT = 12345
_ENC = "utf-8"


# ---------------------------------------------------------------------------
class _Connection:
  """Wraps a single TCP socket with non-blocking send/receive queues."""

  def __init__(self, sock, addr=None):
    self._sock = sock
    self.addr  = addr
    # Disable Nagle batching so state packets are sent immediately
    try:
      self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
      pass
    self._send_q  = queue.Queue()
    self._recv_q  = queue.Queue()
    self._alive   = True
    # Sequence counters for "state" messages only (stale-drop on receive)
    self._state_seq_out = 0
    self._state_seq_in  = -1
    threading.Thread(target=self._sender,   daemon=True).start()
    threading.Thread(target=self._receiver, daemon=True).start()

  # ------------------------------------------------------------------
  def send(self, msg):
    """Queue *msg* (dict) for sending."""
    if self._alive:
      self._send_q.put(msg)

  def recv_all(self):
    """Drain and return all pending received dicts."""
    out = []
    try:
      while True:
        out.append(self._recv_q.get_nowait())
    except queue.Empty:
      pass
    return out

  def disconnect(self):
    self._alive = False
    try:
      self._sock.shutdown(socket.SHUT_RDWR)
    except Exception:
      pass
    try:
      self._sock.close()
    except Exception:
      pass

  @property
  def alive(self):
    return self._alive

  # ------------------------------------------------------------------
  def _sender(self):
    while self._alive:
      try:
        msg = self._send_q.get(timeout=0.1)
        # Stamp outgoing state packets with a sequence number
        if msg.get("type") == "state":
          msg["_seq"] = self._state_seq_out
          self._state_seq_out += 1
        raw = (json.dumps(msg) + "\n").encode(_ENC)
        self._sock.sendall(raw)
      except queue.Empty:
        pass
      except Exception:
        self._alive = False
        break

  def _receiver(self):
    buf = b""
    while self._alive:
      try:
        chunk = self._sock.recv(4096)
        if not chunk:
          self._alive = False
          break
        buf += chunk
        while b"\n" in buf:
          line, buf = buf.split(b"\n", 1)
          try:
            decoded = json.loads(line.decode(_ENC))
            # Drop stale state packets to prevent old positions rendering
            if decoded.get("type") == "state":
              seq = decoded.get("_seq", -1)
              if seq <= self._state_seq_in:
                continue   # stale — discard
              self._state_seq_in = seq
            self._recv_q.put(decoded)
          except json.JSONDecodeError:
            pass
      except Exception:
        self._alive = False
        break


# ---------------------------------------------------------------------------
class NetworkServer:
  """TCP server: accepts up to 8 client connections and can broadcast."""

  def __init__(self, port=DEFAULT_PORT):
    self.port     = port
    self._clients = []          # list of _Connection
    self._lock    = threading.Lock()
    self._running = False
    # Phase-2 player registry: client_idx → {pid, name, color, level}
    self._player_registry = {}
    self._next_pid        = 1   # pid 0 is always the host

  def start(self):
    """Begin listening; returns immediately (accept loop is a daemon thread)."""
    self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self._sock.bind(("", self.port))
    self._sock.listen(8)
    self._sock.settimeout(0.5)
    self._running = True
    threading.Thread(target=self._accept_loop, daemon=True).start()

  def broadcast(self, msg):
    """Send *msg* to every alive client."""
    with self._lock:
      self._prune()
      for c in self._clients:
        if c and c.alive:
          c.send(msg)

  def send_to(self, idx, msg):
    """Send *msg* to one client by its index in the connection list."""
    with self._lock:
      if 0 <= idx < len(self._clients):
        conn = self._clients[idx]
        if conn and conn.alive:
          conn.send(msg)

  def recv_all(self):
    """Drain messages from all clients.
    Each returned dict gains a ``_client_idx`` key identifying the sender."""
    msgs = []
    with self._lock:
      self._prune()
      for i, c in enumerate(self._clients):
        if c and c.alive:
          for m in c.recv_all():
            m["_client_idx"] = i
            msgs.append(m)
    return msgs

  def client_count(self):
    with self._lock:
      self._prune()
      return len([c for c in self._clients if c and c.alive])

  def register_player(self, client_idx, name, color=1, level=1):
    """Assign a stable pid to a client. Call when their 'hello' is processed.

    pid 0 is reserved for the host; clients receive pid 1, 2, 3 …
    Returns the assigned pid.
    """
    with self._lock:
      if client_idx in self._player_registry:
        pid = self._player_registry[client_idx]["pid"]
      else:
        pid = self._next_pid
        self._next_pid += 1
      self._player_registry[client_idx] = {
        "pid": pid, "name": name, "color": color, "level": level
      }
    return pid

  def get_player_list(self):
    """Return list of player-info dicts sorted by pid (host not included).

    Each entry: {"pid": int, "name": str, "color": int, "level": int}
    """
    with self._lock:
      return sorted(self._player_registry.values(), key=lambda p: p["pid"])

  def get_pid(self, client_idx):
    """Return the pid for a connected client, or -1 if not yet registered."""
    with self._lock:
      return self._player_registry.get(client_idx, {}).get("pid", -1)

  def get_player(self, client_idx):
    """Return the player metadata for a connected client index."""
    with self._lock:
      return self._player_registry.get(client_idx)

  def remove_player(self, client_idx):
    """Remove a player from the server-side registry."""
    with self._lock:
      if client_idx in self._player_registry:
        del self._player_registry[client_idx]


  def stop(self):
    self._running = False
    try:
      self._sock.close()
    except Exception:
      pass
    with self._lock:
      for c in self._clients:
        if c:
          c.disconnect()
      self._clients.clear()
      self._player_registry.clear()

  # ------------------------------------------------------------------
  def _prune(self):
    """Remove dead connections (caller must hold _lock)."""
    for idx, conn in enumerate(self._clients):
      if conn and not conn.alive:
        self._clients[idx] = None
        if idx in self._player_registry:
          del self._player_registry[idx]

  def _accept_loop(self):
    while self._running:
      try:
        sock, addr = self._sock.accept()
        sock.settimeout(None)   # ensure accepted socket is in blocking mode
        conn = _Connection(sock, addr)
        with self._lock:
          self._clients.append(conn)
      except socket.timeout:
        pass
      except Exception:
        break


# ---------------------------------------------------------------------------
class NetworkClient:
  """TCP client that connects to a NetworkServer."""

  def __init__(self, host, port=DEFAULT_PORT):
    self.host      = host
    self.port      = port
    self._conn     = None
    # Assigned by the host after 'hello' is processed (phase 2)
    self.player_id = -1

  def connect(self, timeout=5.0):
    """Try to connect; returns True on success."""
    try:
      sock = socket.create_connection((self.host, self.port), timeout=timeout)
      # create_connection leaves the socket with the connect-timeout still
      # active.  Reset to blocking mode so the background _receiver thread
      # never dies from a spurious socket.timeout during idle periods.
      sock.settimeout(None)
      self._conn = _Connection(sock, (self.host, self.port))
      return True
    except Exception:
      return False

  def send(self, msg):
    if self._conn and self._conn.alive:
      self._conn.send(msg)

  def recv_all(self):
    if self._conn:
      return self._conn.recv_all()
    return []

  def disconnect(self):
    if self._conn:
      self._conn.disconnect()
      self._conn = None

  def send_state(self, x, y, a, br=0, sl=0, bl=0, cp=0, lap=0, race_finish=0, sp=0.0, tick=0):
    """Phase-2 convenience: send a per-frame car-state packet.

    Coordinates must already be in track-space (divided by zoom).
    The ``pid`` field is filled from ``self.player_id``.
    """
    self.send({
      "type": "state",
      "pid":  self.player_id,
      "x": int(x), "y": int(y), "a": int(a),
      "br": br, "sl": sl, "bl": bl,
      "cp": int(cp),
      "lap": int(lap),
      "rf": 1 if race_finish else 0,
      "sp": float(sp),
      "tick": int(tick),
    })

  @property
  def connected(self):
    return self._conn is not None and self._conn.alive
