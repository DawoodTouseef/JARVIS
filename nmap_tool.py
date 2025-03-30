import nmap

def nmap_tool(target:str,port:int)->dict:
    """
    A function  provides a number of features for probing computer networks, including host discovery and service and operating system detection.
    These features are extensible by scripts that provide more advanced service detection, vulnerability detection, and other features.
    Nmap can adapt to network conditions including latency and congestion during a scan.
    :param target:ip address of the network
    :param port:port of the device to scan.
    :return:
    """
    scanner = nmap.PortScanner()
    res = scanner.scan(target, str(port))
    return res

