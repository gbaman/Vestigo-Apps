import time
import os
import sys
import pythonping
import vestigo_client
import speedtest

#if os.path.exists("/boot/internet_config.py"):
    #sys.path.append('/boot')
sys.path.append('/boot')

from internet_config import vestigo_sensor_name, vestigo_node_id, vestigo_server_url, ping_ip, test_interval, max_speed_test_server_usage, enable_ping_testing, enable_speed_testing, pings_per_speed_test, ping_pause


if enable_ping_testing and not os.geteuid() == 0:
    print("\n\n\n\n\n")
    print("----WARNING----")
    print("Script is not being run with root permissions...")
    print("Ping testing disabled :(")
    print("If you want to run with ping testing enabled, run with sudo!")
    print("\n\n\n")
    enable_ping_testing = False
    time.sleep(10)


def output_configuration():
    print("------------ Configuration ------------")
    print(f"Ping testing - {enable_ping_testing}")
    print(f"Ping IP address - {ping_ip}")
    print(f"Pings per speed test - {pings_per_speed_test}")
    print(f"Pause between each ping - {ping_pause}\n")
    print(f"Speed testing - {enable_speed_testing}\n")
    print(f"Vestigo sensor name - {vestigo_sensor_name}")
    print(f"Vestigo node id - {vestigo_node_id}")
    print(f"Vestigo url - {vestigo_server_url}\n\n")
    print("Data URLs")
    if enable_ping_testing:
        print(f"{vestigo_server_url}render/{vestigo_node_id}/{vestigo_sensor_name}-ping")
    if enable_speed_testing:
        print(f"{vestigo_server_url}render/{vestigo_node_id}/{vestigo_sensor_name}-download")
        print(f"{vestigo_server_url}render/{vestigo_node_id}/{vestigo_sensor_name}-upload")

    print("\n------------ ------------- ------------\n\n\n")


def ping_test(ping_client):
    try:
        print("Starting ping test!")
        ping_result = pythonping.ping(target=ping_ip, timeout=20, count=20)
        ping = ping_result.rtt_avg_ms
        print(f"Ping test complete - {ping}ms")
    except:
        ping = -1
        print(f"Ping test failed. Unable to reach {ping_ip}!")
    ping_client.log_sensor(f"{vestigo_sensor_name}-ping", round(ping))


def speed_test(server, client):
    threads = []
    # threads = 1
    print("Starting download test")
    server.download(threads=threads)
    print("Download test done")
    # s.upload(threads=threads)
    client.log_sensor(f"{vestigo_sensor_name}-download", float((humanbytes(server.results.download))))
    print("Starting upload test")
    server.upload(threads=threads)
    print("Upload test done")
    client.log_sensor(f"{vestigo_sensor_name}-upload", float((humanbytes(server.results.upload))))


def speed_test_select_server():
    servers = []
    print("Attempting to select best speedtest server to use...")
    try:
        s = speedtest.Speedtest()
        s.get_servers(servers)
        s.get_best_server()
        return s
    except:
        print("Unable to select a speedtest server. Skipping speedtest!")
        return None


def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(float(1024) ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0}'.format(B)
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f}'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)


def main():
    output_configuration()
    print(f"Starting client with node id {vestigo_node_id} and sensor name of {vestigo_sensor_name}.")
    server_counter = 0
    server = None
    client = vestigo_client.Vestigo(vestigo_server_url, vestigo_node_id)
    while True:
        print("-------------------------------------")
        if enable_speed_testing:
            if not server or server_counter > max_speed_test_server_usage:
                server = speed_test_select_server()
            if server:
                speed_test(server, client)
                server_counter = server_counter + 1
            time.sleep(1)
        if enable_ping_testing:
            for count in range(0, pings_per_speed_test):
                ping_test(client)
                time.sleep(ping_pause)
        print(f"Waiting now for {test_interval} seconds before testing again")
        time.sleep(test_interval)


main()
