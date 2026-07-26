import requests
def send_to_esp32(data):
    ESP32_IP = "172.20.10.3"
    url = f"http://{ESP32_IP}/update"
    params = data
    response = requests.get(url, params=params)
    print(response.status_code)
    print(response.text)
    #初版
