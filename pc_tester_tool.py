import serial
import json
import time
import os

# 載入設定檔
CONFIG_FILE = 'test_config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        # 如果沒有設定檔，回傳一個基本的預設值以免報錯
        return {"uart_settings": {"port": "COM5", "baudrate": 115200, "timeout": 1}, "test_cases": []}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_packet(cmd_int, param_int):
    """
    建立符合 Protocol 的 14 bytes 封包
    """
    header = b'Loewe test ' # 11 bytes
    cmd = cmd_int.to_bytes(1, 'big')
    param = param_int.to_bytes(1, 'big')
    end = b'\x0d'
    
    packet = header + cmd + param + end
    return packet

def send_and_receive(ser, cmd_int, param_int, desc="Manual Test"):
    """
    發送並接收的通用函式
    """
    print(f"\n--- 執行: {desc} ---")
    packet = build_packet(cmd_int, param_int)
    
    # 清空 Buffer
    ser.reset_input_buffer()
    
    print(f"TX (Hex): {packet.hex(' ')}")
    ser.write(packet)
    
    time.sleep(0.2)
    
    raw_response = ser.read_until(b'\r')
    
    if not raw_response:
        print("結果: [無回應/Timeout]")
        return None
    
    try:
        response_str = raw_response.decode('utf-8', errors='ignore').strip()
        print(f"RX (Str): \033[96m{response_str}\033[0m") # 青色文字顯示回應
        return response_str
    except Exception as e:
        print(f"解析錯誤: {e}")
        return None

def validate_response(response_str, test_case):
    if not response_str: return False
    clean_resp = response_str.replace("ACK: ", "").strip()
    criteria = test_case.get('criteria')
    expect_type = test_case.get('expect_type')

    if expect_type == 'exact':
        return clean_resp == str(criteria)
    elif expect_type == 'contains':
        return str(criteria) in clean_resp
    elif expect_type == 'length':
        return len(clean_resp) >= int(criteria)
    else:
        return True

def manual_input_mode(ser):
    """
    手動輸入 Hex 指令模式
    """
    print("\n[ 手動輸入模式 ]")
    print("請輸入 16 進位數值 (例如: 0C 或 0x0C)")
    
    try:
        cmd_str = input("CMD (Hex): ").strip()
        if not cmd_str: return
        cmd_int = int(cmd_str, 16)
        
        param_str = input("PARAM (Hex): ").strip()
        if not param_str: return
        param_int = int(param_str, 16)
        
        # 發送
        send_and_receive(ser, cmd_int, param_int, f"手動 CMD:{hex(cmd_int)} PARAM:{hex(param_int)}")
        
    except ValueError:
        print("錯誤: 輸入格式不正確，請輸入 Hex (0-255)")

def main():
    config = load_config()
    uart_cfg = config.get('uart_settings', {'port': 'COM5', 'baudrate': 115200, 'timeout': 1})
    
    try:
        ser = serial.Serial(uart_cfg['port'], uart_cfg['baudrate'], timeout=uart_cfg['timeout'])
        print(f"已連接 {uart_cfg['port']} @ {uart_cfg['baudrate']}")
    except serial.SerialException:
        print(f"錯誤: 無法開啟 {uart_cfg['port']}。")
        return

    tests = config.get('test_cases', [])

    while True:
        print("\n==============================")
        print("      MCU 產測工具選單      ")
        print("==============================")
        for t in tests:
            print(f"{t['id']}. {t['name']}")
        print("-" * 30)
        print("M. 手動輸入指令 (Manual Input)")
        print("A. 執行所有測試 (Auto Run)")
        print("Q. 離開 (Quit)")
        print("==============================")
        
        choice = input("請選擇: ").upper()

        if choice == 'Q':
            break
        elif choice == 'M':
            manual_input_mode(ser)
        elif choice == 'A':
            print("\n*** 開始自動測試 ***")
            for t in tests:
                # JSON 中的 cmd 是字串 "0x00"，需轉回 int
                c = int(t['cmd_hex'], 16)
                p = int(t['param_hex'], 16)
                resp = send_and_receive(ser, c, p, t['name'])
                
                status = False
                if resp:
                    status = validate_response(resp, t)
                
                if status:
                    print(">>> 判定: \033[92mPASS\033[0m")
                else:
                    print(f">>> 判定: \033[91mFAIL\033[0m (預期: {t['criteria']})")
                time.sleep(0.5)
        else:
            selected_test = next((t for t in tests if str(t['id']) == choice), None)
            if selected_test:
                c = int(selected_test['cmd_hex'], 16)
                p = int(selected_test['param_hex'], 16)
                resp = send_and_receive(ser, c, p, selected_test['name'])
                
                if resp and validate_response(resp, selected_test):
                    print(">>> 判定: \033[92mPASS\033[0m")
                else:
                    print(f">>> 判定: \033[91mFAIL\033[0m")
            else:
                print("無效的選擇")

    ser.close()

if __name__ == "__main__":
    main()