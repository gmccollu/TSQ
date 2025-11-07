#!/usr/bin/env python3
"""
Python wrapper for Quiche C API
Provides access to QUIC datagrams via Quiche
"""
import ctypes
import os
from ctypes import (
    c_void_p, c_char_p, c_size_t, c_uint8, c_uint16, c_uint32, c_uint64,
    c_int, c_bool, POINTER, Structure, byref
)

# Find quiche library
QUICHE_LIB_PATHS = [
    "/usr/local/lib/libquiche.so",
    "/usr/lib/libquiche.so",
    "~/quiche/target/release/libquiche.so",
    "/opt/homebrew/lib/libquiche.dylib",  # macOS ARM
    "/usr/local/lib/libquiche.dylib",      # macOS Intel
]

def find_quiche_lib():
    """Find quiche library"""
    for path in QUICHE_LIB_PATHS:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return expanded
    raise RuntimeError("Quiche library not found. Please install quiche first.")

# Load library
try:
    quiche = ctypes.CDLL(find_quiche_lib())
except Exception as e:
    print(f"Warning: Could not load quiche library: {e}")
    print("Please follow QUICHE_SETUP.md to install quiche")
    quiche = None

# Define structures
class QuicheConfig(Structure):
    pass

class QuicheConn(Structure):
    pass

if quiche:
    # Configuration functions
    quiche.quiche_config_new.argtypes = [c_uint32]
    quiche.quiche_config_new.restype = POINTER(QuicheConfig)
    
    quiche.quiche_config_set_application_protos.argtypes = [
        POINTER(QuicheConfig), POINTER(c_uint8), c_size_t
    ]
    quiche.quiche_config_set_application_protos.restype = c_int
    
    quiche.quiche_config_set_max_idle_timeout.argtypes = [POINTER(QuicheConfig), c_uint64]
    quiche.quiche_config_set_max_idle_timeout.restype = None
    
    quiche.quiche_config_set_max_recv_udp_payload_size.argtypes = [POINTER(QuicheConfig), c_size_t]
    quiche.quiche_config_set_max_recv_udp_payload_size.restype = None
    
    quiche.quiche_config_set_initial_max_data.argtypes = [POINTER(QuicheConfig), c_uint64]
    quiche.quiche_config_set_initial_max_data.restype = None
    
    quiche.quiche_config_set_initial_max_stream_data_bidi_local.argtypes = [POINTER(QuicheConfig), c_uint64]
    quiche.quiche_config_set_initial_max_stream_data_bidi_local.restype = None
    
    quiche.quiche_config_set_initial_max_stream_data_bidi_remote.argtypes = [POINTER(QuicheConfig), c_uint64]
    quiche.quiche_config_set_initial_max_stream_data_bidi_remote.restype = None
    
    quiche.quiche_config_set_initial_max_streams_bidi.argtypes = [POINTER(QuicheConfig), c_uint64]
    quiche.quiche_config_set_initial_max_streams_bidi.restype = None
    
    quiche.quiche_config_enable_dgram.argtypes = [POINTER(QuicheConfig), c_bool, c_size_t, c_size_t]
    quiche.quiche_config_enable_dgram.restype = None
    
    quiche.quiche_config_set_disable_active_migration.argtypes = [POINTER(QuicheConfig), c_bool]
    quiche.quiche_config_set_disable_active_migration.restype = None
    
    # Connection functions
    quiche.quiche_connect.argtypes = [
        c_char_p, POINTER(c_uint8), c_size_t, POINTER(c_uint8), c_size_t,
        POINTER(c_uint8), c_size_t, POINTER(c_uint8), c_size_t,
        POINTER(QuicheConfig)
    ]
    quiche.quiche_connect.restype = POINTER(QuicheConn)
    
    quiche.quiche_conn_send.argtypes = [POINTER(QuicheConn), POINTER(c_uint8), c_size_t]
    quiche.quiche_conn_send.restype = c_int
    
    quiche.quiche_conn_recv.argtypes = [POINTER(QuicheConn), POINTER(c_uint8), c_size_t]
    quiche.quiche_conn_recv.restype = c_int
    
    quiche.quiche_conn_dgram_send.argtypes = [POINTER(QuicheConn), POINTER(c_uint8), c_size_t]
    quiche.quiche_conn_dgram_send.restype = c_int
    
    quiche.quiche_conn_dgram_recv.argtypes = [POINTER(QuicheConn), POINTER(c_uint8), c_size_t]
    quiche.quiche_conn_dgram_recv.restype = c_int
    
    quiche.quiche_conn_is_established.argtypes = [POINTER(QuicheConn)]
    quiche.quiche_conn_is_established.restype = c_bool
    
    quiche.quiche_conn_is_closed.argtypes = [POINTER(QuicheConn)]
    quiche.quiche_conn_is_closed.restype = c_bool
    
    quiche.quiche_conn_free.argtypes = [POINTER(QuicheConn)]
    quiche.quiche_conn_free.restype = None
    
    quiche.quiche_config_free.argtypes = [POINTER(QuicheConfig)]
    quiche.quiche_config_free.restype = None

class QuicheWrapper:
    """High-level wrapper for Quiche"""
    
    def __init__(self):
        if quiche is None:
            raise RuntimeError("Quiche library not loaded")
        self.lib = quiche
    
    def create_config(self, version=0x00000001):
        """Create QUIC configuration"""
        config = self.lib.quiche_config_new(version)
        if not config:
            raise RuntimeError("Failed to create quiche config")
        
        # Set ALPN
        alpn = b"\x05tsq/1"  # Length-prefixed
        alpn_ptr = ctypes.cast(alpn, POINTER(c_uint8))
        self.lib.quiche_config_set_application_protos(config, alpn_ptr, len(alpn))
        
        # Set parameters
        self.lib.quiche_config_set_max_idle_timeout(config, 30000)  # 30 seconds
        self.lib.quiche_config_set_max_recv_udp_payload_size(config, 65535)
        self.lib.quiche_config_set_initial_max_data(config, 10000000)
        self.lib.quiche_config_set_initial_max_stream_data_bidi_local(config, 1000000)
        self.lib.quiche_config_set_initial_max_stream_data_bidi_remote(config, 1000000)
        self.lib.quiche_config_set_initial_max_streams_bidi(config, 100)
        
        # Enable datagrams
        self.lib.quiche_config_enable_dgram(config, True, 1000, 1000)
        
        # Disable migration
        self.lib.quiche_config_set_disable_active_migration(config, True)
        
        return config
    
    def connect(self, server_name, scid, config):
        """Create client connection"""
        server_name_bytes = server_name.encode('utf-8')
        scid_ptr = ctypes.cast(scid, POINTER(c_uint8))
        
        conn = self.lib.quiche_connect(
            server_name_bytes,
            scid_ptr, len(scid),
            None, 0,  # local address
            None, 0,  # peer address
            None, 0,  # odcid
            config
        )
        
        if not conn:
            raise RuntimeError("Failed to create quiche connection")
        
        return conn
    
    def send_datagram(self, conn, data):
        """Send datagram"""
        data_ptr = ctypes.cast(data, POINTER(c_uint8))
        result = self.lib.quiche_conn_dgram_send(conn, data_ptr, len(data))
        return result
    
    def recv_datagram(self, conn, max_len=65535):
        """Receive datagram"""
        buf = ctypes.create_string_buffer(max_len)
        buf_ptr = ctypes.cast(buf, POINTER(c_uint8))
        result = self.lib.quiche_conn_dgram_recv(conn, buf_ptr, max_len)
        
        if result > 0:
            return buf.raw[:result]
        return None
    
    def is_established(self, conn):
        """Check if connection is established"""
        return self.lib.quiche_conn_is_established(conn)
    
    def is_closed(self, conn):
        """Check if connection is closed"""
        return self.lib.quiche_conn_is_closed(conn)
    
    def free_conn(self, conn):
        """Free connection"""
        self.lib.quiche_conn_free(conn)
    
    def free_config(self, config):
        """Free configuration"""
        self.lib.quiche_config_free(config)

# Test if quiche is available
def is_quiche_available():
    """Check if quiche library is available"""
    return quiche is not None

if __name__ == "__main__":
    if is_quiche_available():
        print("✓ Quiche library loaded successfully")
        print(f"  Library path: {find_quiche_lib()}")
    else:
        print("✗ Quiche library not found")
        print("  Please follow QUICHE_SETUP.md to install quiche")
