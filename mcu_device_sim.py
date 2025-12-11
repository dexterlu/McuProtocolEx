import serial
import time
import sys
import threading

# --- 設定區域 ---
# 如果在同一台電腦測試，PC端用 COM5，這裡建議用 COM6 (需搭配虛擬 COM Port 軟體)
DUT_PORT = '/dev/tty.usbserial-A5069RR4' #'COM6' 
BAUDRATE = 115200

# Protocol 定義
HEADER = b'Loewe test '
END_BYTE = b'\x0d'

# --- 待測物全域狀態 (模擬 RAM) ---
# 這些變數會被兩個執行緒共用：
# 1. UART Thread: 讀取這些值回傳給 PC，或被 PC 寫入修改
# 2. Main Thread: 使用者透過鍵盤修改這些值 (模擬實體操作)
device_state = {
    "volume": 8,            # 預設音量
    "button_status": "None", # 目前按鍵狀態
    "bt_addr": "00:11:22:33:44:55",
    "fw_ver": "v1.0.5",
    "test_mode": False
}

running = True # 程式執行旗標

def handle_command(cmd, param):
    """
    根據 CMD Hex 處理邏輯，讀取或寫入 device_state
    """
    global device_state
    
    cmd_int = int.from_bytes(cmd, byteorder='big')
    param_int = int.from_bytes(param, byteorder='big')
    
    # Debug 顯示收到的指令
    # print(f"\n[UART] 收到 CMD: {hex(cmd_int)}, PARAM: {hex(param_int)}")

    response_msg = ""
    
    if cmd_int == 0x00: # FirmwareVer
        response_msg = device_state["fw_ver"]
        
    elif cmd_int == 0x01: # BT Address
        response_msg = device_state["bt_addr"]
        
    elif cmd_int == 0x02: # GetButton
        # 回傳目前模擬的按鍵狀態
        response_msg = device_state["button_status"]
        # 模擬按鍵放開 (Read on clear)，讀取後自動歸零，視需求而定
        # device_state["button_status"] = "None" 
        
    elif cmd_int == 0x04: # MagicLed
        response_msg = "OK"
        
    elif cmd_int == 0x0C: # SetVolume (PC 設定音量)
        if 0 <= param_int <= 15:
            device_state["volume"] = param_int
            response_msg = f"OK (Vol:{param_int})"
        else:
            response_msg = "Error: Range 0-15"
            
    elif cmd_int == 0x99: # TestMode
        device_state["test_mode"] = (param_int == 0x01)
        status = "ON" if device_state["test_mode"] else "OFF"
        response_msg = f"Test Mode {status}"
        
    else:
        response_msg = "Unknown CMD"

    # 包裝回應 ACK
    full_response = f"ACK: {response_msg}\r".encode('utf-8')
    return full_response

def uart_listener_task():
    """
    背景執行緒：專門負責 Serial Port 通訊
    """
    global running
    try:
        ser = serial.Serial(DUT_PORT, BAUDRATE, timeout=0.1)
        print(f"\n[System] UART 監聽中 ({DUT_PORT})...")
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
                
                # 處理封包 (Total Len = 14)
                while len(buffer) >= 14:
                    if buffer.startswith(HEADER):
                        packet = buffer[:14]
                        
                        cmd_byte = packet[11:12]
                        param_byte = packet[12:13]
                        end_byte = packet[13:14]

                        if end_byte == END_BYTE:
                            resp = handle_command(cmd_byte, param_byte)
                            ser.write(resp)
                            # print(f"[UART] 回傳: {resp}") # 為了不干擾選單顯示，可註解掉
                        
                        buffer = buffer[14:]
                    else:
                        buffer = buffer[1:]
            
            time.sleep(0.01)
        except Exception as e:
            print(f"[Error] UART 錯誤: {e}")
            break
            
    ser.close()
    print("\n[System] UART 關閉")

def print_status():
    """顯示目前模擬器的狀態"""
    print("\n--------------------------------")
    print(f" [模擬器狀態]")
    print(f" 音量 (Volume) : {device_state['volume']}")
    print(f" 按鍵 (Button) : {device_state['button_status']}")
    print(f" 測試模式      : {device_state['test_mode']}")
    print("--------------------------------")

def main_menu():
    """主執行緒：使用者互動選單"""
    global running, device_state
    
    print("=== MCU 待測物模擬器啟動 ===")
    print("說明: 您可以在此模擬實體按鍵與旋鈕操作，")
    print("      PC 端程式查詢時會得到您設定的狀態。")

    # 啟動 UART 執行緒
    t = threading.Thread(target=uart_listener_task)
    t.start()
    
    time.sleep(1) # 等待 UART 開啟

    while running:
        print_status()
        print("請選擇模擬動作:")
        print("1. 模擬 [音量 +] (Vol Up)")
        print("2. 模擬 [音量 -] (Vol Down)")
        print("3. 模擬 [按下 Play 鍵]")
        print("4. 模擬 [按下 Power 鍵]")
        print("5. 模擬 [釋放所有按鍵] (Release)")
        print("Q. 離開程式")
        
        choice = input("輸入: ").strip().upper()
        
        if choice == '1':
            if device_state["volume"] < 15:
                device_state["volume"] += 1
                print(">> 音量已增加")
            else:
                print(">> 音量已達最大值")
                
        elif choice == '2':
            if device_state["volume"] > 0:
                device_state["volume"] -= 1
                print(">> 音量已降低")
            else:
                print(">> 音量已達最小值")
                
        elif choice == '3':
            device_state["button_status"] = "Play Pressed"
            print(">> 按鍵狀態設為: Play Pressed")
            
        elif choice == '4':
            device_state["button_status"] = "Power Pressed"
            print(">> 按鍵狀態設為: Power Pressed")
            
        elif choice == '5':
            device_state["button_status"] = "None"
            print(">> 按鍵狀態設為: None")
            
        elif choice == 'Q':
            print(">> 正在關閉...")
            running = False
            break
        else:
            print(">> 無效輸入")

    t.join() # 等待 UART 執行緒結束
    print("程式已結束")

if __name__ == "__main__":
    main_menu()