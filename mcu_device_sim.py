import serial
import time
import sys
import threading

# --- 設定區域 ---
# 若在同一台電腦測試，PC端用 COM5，這裡建議用 COM6 (需搭配虛擬 COM Port)
DUT_PORT = '/dev/tty.usbserial-A5069RR4' #'COM6' 
BAUDRATE = 115200

# Protocol 定義
HEADER = b'Loewe test '
END_BYTE = b'\x0d'

# --- 待測物全域狀態 (模擬 RAM) ---
device_state = {
    "volume": 8,            
    "button_status": "None", 
    "bt_addr": "00:11:22:33:44:55",
    "fw_ver": "v1.0.5",
    "test_mode": False
}

# --- 通訊紀錄 (用於顯示在選單上) ---
last_log = {
    "rx": "無",
    "tx": "無",
    "time": "-"
}

running = True 

def handle_command(cmd, param):
    """
    處理指令並產生 Log
    """
    global device_state, last_log
    
    cmd_int = int.from_bytes(cmd, byteorder='big')
    param_int = int.from_bytes(param, byteorder='big')
    
    # 1. 準備 Log 資訊 (RX)
    rx_str = f"CMD: {hex(cmd_int)} | PARAM: {hex(param_int)}"
    
    # 2. 處理邏輯
    response_msg = ""
    if cmd_int == 0x00: # FirmwareVer
        response_msg = device_state["fw_ver"]
    elif cmd_int == 0x01: # BT Address
        response_msg = device_state["bt_addr"]
    elif cmd_int == 0x02: # GetButton
        response_msg = device_state["button_status"]
    elif cmd_int == 0x04: # MagicLed
        response_msg = "OK"
    elif cmd_int == 0x0C: # SetVolume
        if 0 <= param_int <= 15:
            device_state["volume"] = param_int
            response_msg = f"OK (Vol:{param_int})"
        else:
            response_msg = "Error: Range"
    elif cmd_int == 0x99: # TestMode
        device_state["test_mode"] = (param_int == 0x01)
        status = "ON" if device_state["test_mode"] else "OFF"
        response_msg = f"Test Mode {status}"
    else:
        response_msg = "Unknown CMD"

    # 3. 準備 Log 資訊 (TX)
    # 模擬實際回應格式 ACK: ...
    tx_str = f"ACK: {response_msg}"
    
    # 更新全域 Log 變數 (給選單顯示用)
    last_log["rx"] = rx_str
    last_log["tx"] = tx_str
    last_log["time"] = time.strftime("%H:%M:%S")

    # 4.【即時顯示 Log】
    # 使用 \r 清除當前行，避免與 input 打架，印完後重新顯示提示符
    print(f"\n\n>>> [RX 接收] {rx_str}")
    print(f">>> [TX 回應] {tx_str}\n")
    print("請選擇模擬動作 (輸入): ", end="", flush=True)

    # 5. 包裝實體回應資料
    full_response = f"{tx_str}\r".encode('utf-8')
    return full_response

def uart_listener_task():
    """
    背景執行緒：監聽 Serial Port
    """
    global running
    try:
        ser = serial.Serial(DUT_PORT, BAUDRATE, timeout=0.1)
        # print(f"\n[System] UART 監聽啟動 ({DUT_PORT})")
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
                        
                        cmd_byte = packet[11:12]
                        param_byte = packet[12:13]
                        end_byte = packet[13:14]

                        if end_byte == END_BYTE:
                            resp = handle_command(cmd_byte, param_byte)
                            ser.write(resp)
                        
                        buffer = buffer[14:]
                    else:
                        buffer = buffer[1:]
            
            time.sleep(0.01)
        except Exception as e:
            print(f"[Error] UART Exception: {e}")
            break
            
    ser.close()

def print_status():
    """顯示模擬器狀態面板"""
    # 清畫面 (選擇性開啟，這裡為了 Log 保留不全清，只印分隔線)
    print("\n" + "="*40)
    print(f"      MCU 模擬器 - 狀態面板      ")
    print("="*40)
    print(f" [ 內部狀態 ]")
    print(f" * 音量 (Volume) : {device_state['volume']}")
    print(f" * 按鍵 (Button) : {device_state['button_status']}")
    print(f" * 測試模式      : {device_state['test_mode']}")
    print("-" * 40)
    print(f" [ 最後一次通訊紀錄 @ {last_log['time']} ]")
    print(f" * 收到: \033[93m{last_log['rx']}\033[0m") # 黃色文字
    print(f" * 回應: \033[96m{last_log['tx']}\033[0m") # 青色文字
    print("="*40)

def main_menu():
    global running, device_state
    
    print(f"正在開啟 {DUT_PORT}...")
    t = threading.Thread(target=uart_listener_task)
    t.start()
    time.sleep(1) # 等待 Serial 開啟

    if not running:
        print("無法啟動程式，請檢查 COM Port。")
        return

    while running:
        print_status()
        print("1. 音量 + (Vol Up)")
        print("2. 音量 - (Vol Down)")
        print("3. 按下 Play 鍵")
        print("4. 按下 Power 鍵")
        print("5. 釋放按鍵 (Release)")
        print("Q. 離開")
        print("-" * 40)
        
        # 這裡的 input 會被背景 thread 的 print 插隊，這是正常的
        # 我們在 handle_command 裡加了補救措施
        choice = input("請選擇模擬動作 (輸入): ").strip().upper()
        
        if choice == '1':
            if device_state["volume"] < 15:
                device_state["volume"] += 1
        elif choice == '2':
            if device_state["volume"] > 0:
                device_state["volume"] -= 1
        elif choice == '3':
            device_state["button_status"] = "Play Pressed"
        elif choice == '4':
            device_state["button_status"] = "Power Pressed"
        elif choice == '5':
            device_state["button_status"] = "None"
        elif choice == 'Q':
            running = False
            break
        else:
            print("\n[!] 無效輸入")

    t.join()
    print("程式結束")

if __name__ == "__main__":
    main_menu()