import serial
import time
import sys
import threading

# --- 設定區域 ---
DUT_PORT = '/dev/tty.usbserial-A5069RR4' #'COM6' 
BAUDRATE = 115200

HEADER = b'Loewe test '
END_BYTE = b'\x0d'

# --- 待測物全域狀態 ---
device_state = {
    "volume": 8,            
    "button_status": "None", 
    "bt_addr": "00:11:22:33:44:55",
    "fw_ver": "v1.0.5",
    "test_mode": False,
    # 新增: 強制覆寫下一次的回應 (One-shot)
    "override_response": None 
}

# --- 通訊紀錄 ---
last_log = {"rx": "無", "tx": "無", "time": "-"}
running = True 

def handle_command(cmd, param):
    """
    處理指令並產生 Log
    """
    global device_state, last_log
    
    cmd_int = int.from_bytes(cmd, byteorder='big')
    param_int = int.from_bytes(param, byteorder='big')
    
    rx_str = f"CMD: {hex(cmd_int)} | PARAM: {hex(param_int)}"
    response_msg = ""

    # === [新增邏輯] 檢查是否有強制回應 ===
    if device_state["override_response"] is not None:
        response_msg = device_state["override_response"]
        # 清除強制回應 (只生效一次，避免永久錯誤)
        device_state["override_response"] = None
        # 標記這是模擬的特殊回應
        rx_str += " (已觸發強制回應)"
    else:
        # === 標準 Protocol 邏輯 ===
        if cmd_int == 0x00: 
            response_msg = device_state["fw_ver"]
        elif cmd_int == 0x01: 
            response_msg = device_state["bt_addr"]
        elif cmd_int == 0x02: 
            response_msg = device_state["button_status"]
        elif cmd_int == 0x04: 
            response_msg = "OK"
        elif cmd_int == 0x0C: 
            if 0 <= param_int <= 15:
                device_state["volume"] = param_int
                response_msg = f"OK (Vol:{param_int})"
            else:
                response_msg = "Error: Range"
        elif cmd_int == 0x99: 
            device_state["test_mode"] = (param_int == 0x01)
            status = "ON" if device_state["test_mode"] else "OFF"
            response_msg = f"Test Mode {status}"
        else:
            response_msg = "Unknown CMD"

    tx_str = f"ACK: {response_msg}"
    
    last_log["rx"] = rx_str
    last_log["tx"] = tx_str
    last_log["time"] = time.strftime("%H:%M:%S")

    # 即時顯示 Log
    print(f"\n\n>>> [RX 接收] {rx_str}")
    print(f">>> [TX 回應] {tx_str}\n")
    print("請選擇模擬動作 (輸入): ", end="", flush=True)

    full_response = f"{tx_str}\r".encode('utf-8')
    return full_response

def uart_listener_task():
    global running
    try:
        ser = serial.Serial(DUT_PORT, BAUDRATE, timeout=0.1)
    except Exception as e:
        print(f"\n[Error] 無法開啟 {DUT_PORT}: {e}")
        running = False
        return

    buffer = b''
    while running:
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer += data
                while len(buffer) >= 14:
                    if buffer.startswith(HEADER):
                        packet = buffer[:14]
                        resp = handle_command(packet[11:12], packet[12:13])
                        ser.write(resp)
                        buffer = buffer[14:]
                    else:
                        buffer = buffer[1:]
            time.sleep(0.01)
        except Exception:
            break
    ser.close()

def print_status():
    override_status = device_state['override_response'] if device_state['override_response'] else "無 (正常模式)"
    print("\n" + "="*45)
    print(f"      MCU 模擬器 - 狀態面板      ")
    print("="*45)
    print(f" [ 內部狀態 ]")
    print(f" * 音量: {device_state['volume']} | 按鍵: {device_state['button_status']}")
    print(f" * 測試模式: {device_state['test_mode']}")
    print(f" * \033[93m強制回應 (Next Response): {override_status}\033[0m")
    print("-" * 45)
    print(f" [ 最後通訊 @ {last_log['time']} ]")
    print(f" * 收到: {last_log['rx']}")
    print(f" * 回應: \033[96m{last_log['tx']}\033[0m")
    print("="*45)

def main_menu():
    global running, device_state
    
    print(f"正在開啟 {DUT_PORT}...")
    t = threading.Thread(target=uart_listener_task)
    t.start()
    time.sleep(1) 

    if not running: return

    while running:
        print_status()
        print("1. 音量 + (Vol Up)")
        print("2. 音量 - (Vol Down)")
        print("3. 按下 Play 鍵")
        print("4. 按下 Power 鍵")
        print("5. 釋放按鍵")
        print("6. \033[93m設定下一次的強制回應 (Injection)\033[0m")
        print("Q. 離開")
        print("-" * 45)
        
        choice = input("請選擇模擬動作 (輸入): ").strip().upper()
        
        if choice == '1':
            if device_state["volume"] < 15: device_state["volume"] += 1
        elif choice == '2':
            if device_state["volume"] > 0: device_state["volume"] -= 1
        elif choice == '3':
            device_state["button_status"] = "Play Pressed"
        elif choice == '4':
            device_state["button_status"] = "Power Pressed"
        elif choice == '5':
            device_state["button_status"] = "None"
        elif choice == '6':
            print("\n請輸入下一次 MCU 要回傳的字串 (例如: ERROR_BUSY)")
            msg = input("自訂回應內容: ").strip()
            if msg:
                device_state["override_response"] = msg
                print(">> 設定完成！下一次收到任何指令都會回傳此內容。")
        elif choice == 'Q':
            running = False
            break
        else:
            print("\n[!] 無效輸入")

    t.join()
    print("程式結束")

if __name__ == "__main__":
    main_menu()