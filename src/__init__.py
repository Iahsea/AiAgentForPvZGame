import socket

# Khắc phục triệt để lỗi timeout / treo kết nối trên Windows / ISP
# do hệ thống ưu tiên phân giải IPv6 nhưng hạ tầng mạng bị blackhole IPv6 quốc tế tới Google API.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        responses = _orig_getaddrinfo(host, port, family, type, proto, flags)
        ipv4 = [r for r in responses if r[0] == socket.AF_INET]
        return ipv4 if ipv4 else responses
    except Exception:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_first_getaddrinfo
