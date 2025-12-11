import serial
import time
import sys

# 設定模擬器的 Port (若在同一台電腦測試，這裡不能是 COM5，建議用 COM6 並配合虛擬 Com Port 軟體)
# 如果是真實燒錄到 MCU，這段邏輯需改寫為 C code。這裡是 Python 模擬器。
DUT_PORT = '/dev/ttyUSB0'  # 修改為你的模擬器 Port
BAUDRATE = 115200

HEADER = b'Loewe test '
END_BYTE = b'\x0d'

def calculate_checksum(data):
    # 這裡可以實作 checksum，目前 Protocol 似乎沒有 checksum
    pass

def handle_command(cmd, param):
    """
    根據 CMD Hex 處理邏輯並回傳模擬數據
    """
    cmd_int = int.from_bytes(cmd, byteorder='big')
    param_int = int.from_bytes(param, byteorder='big')
    
    print(f"-> 收到指令 CMD: {hex(cmd_int)}, PARAM: {hex(param_int)}")

    # 模擬回應邏輯
    response_msg = ""
    
    if cmd_int == 0x00: # FirmwareVer
        response_msg = "v1.0.5"
    elif cmd_int == 0x01: # BT Address
        response_msg = "00:11:22:33:44:55"
    elif cmd_int == 0x02: # GetButton
        response_msg = "VolUp:0, VolDown:0"
    elif cmd_int == 0x04: # MagicLed
        response_msg = "OK"
    elif cmd_int == 0x0C: # SetVolume
        response_msg = "OK"
    elif cmd_int == 0x99: # TestMode
        if param_int == 0x01:
            response_msg = "Test Mode ON"
        else:
            response_msg = "Test Mode OFF"
    else:
        response_msg = "Unknown CMD"

    # 包裝回應 (模擬 ACK: <Message>)
    full_response = f"ACK: {response_msg}\r".encode('utf-8')
    return full_response

def main():
    try:
        ser = serial.Serial(DUT_PORT, BAUDRATE, timeout=0.1)
        print(f"--- MCU 模擬器啟動 ({DUT_PORT}) ---")
        print("等待 Command 中...")
    except Exception as e:
        print(f"無法開啟 Port {DUT_PORT}: {e}")
        return

    buffer = b''
    
    while True:
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                buffer += data
                
                # 檢查封包長度 (Protocol 定義 Total Len = 14)
                while len(buffer) >= 14:
                    # 檢查 Header
                    if buffer.startswith(HEADER):
                        # 取出完整封包 (14 bytes)
                        packet = buffer[:14]
                        
                        # 解析內容
                        cmd_byte = packet[11:12]
                        param_byte = packet[12:13]
                        end_byte = packet[13:14]

                        if end_byte == END_BYTE:
                            # 執行指令並回應
                            resp = handle_command(cmd_byte, param_byte)
                            ser.write(resp)
                            print(f"<- 回傳: {resp}")
                        else:
                            print("錯誤: 結尾 byte 不正確")

                        # 移除已處理的數據
                        buffer = buffer[14:]
                    else:
                        # 如果開頭不是 Header，往後移 1 byte 繼續找 (Sliding window)
                        buffer = buffer[1:]
                        
            time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n關閉模擬器")
            ser.close()
            sys.exit()
        except Exception as e:
            print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()