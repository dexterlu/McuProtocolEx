import serial
import json
import time
import os

# 載入設定檔
CONFIG_FILE = 'test_config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"找不到設定檔: {CONFIG_FILE}")
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_packet(cmd_hex_str, param_hex_str):
    """
    建立符合 Protocol 的 14 bytes 封包
    Structure: [Header 11] + [CMD 1] + [Param 1] + [0x0D]
    """
    header = b'Loewe test ' # 11 bytes
    cmd = int(cmd_hex_str, 16).to_bytes(1, 'big')
    param = int(param_hex_str, 16).to_bytes(1, 'big')
    end = b'\x0d'
    
    packet = header + cmd + param + end
    return packet

def validate_response(response_str, test_case):
    """
    根據 JSON 中的條件判斷 Pass/Fail
    """
    # 移除 ACK 前綴和換行符號以便比對
    clean_resp = response_str.replace("ACK: ", "").strip()
    
    criteria = test_case.get('criteria')
    expect_type = test_case.get('expect_type')

    if expect_type == 'exact':
        return clean_resp == str(criteria)
    elif expect_type == 'contains':
        return str(criteria) in clean_resp
    elif expect_type == 'length':
        # 例如 BT Address 長度檢查
        return len(clean_resp) >= int(criteria)
    else:
        return True # 未定義條件視為 Pass

def run_test(ser, test_case):
    print(f"\n--- 執行測試: {test_case['name']} ---")
    
    # 1. 組建封包
    packet = build_packet(test_case['cmd_hex'], test_case['param_hex'])
    
    # 2. 清空 Buffer 並傳送
    ser.reset_input_buffer()
    print(f"TX (Hex): {packet.hex(' ')}")
    ser.write(packet)
    
    # 3. 等待回應
    time.sleep(0.2) # 給 MCU 一點處理時間
    
    # 4. 讀取回應
    # 這裡假設回應以 \r 結尾，或是讀取固定長度，這裡用 read_until
    raw_response = ser.read_until(b'\r')
    
    if not raw_response:
        print("結果: FAIL (Timeout / No Response)")
        return False

    try:
        response_str = raw_response.decode('utf-8', errors='ignore').strip()
        print(f"RX (Str): {response_str}")
        
        # 5. 判斷結果
        if validate_response(response_str, test_case):
            print(">>> 判定: \033[92mPASS\033[0m") # 綠色 PASS
            return True
        else:
            print(f">>> 判定: \033[91mFAIL\033[0m (預期: {test_case['criteria']})") # 紅色 FAIL
            return False
            
    except Exception as e:
        print(f"解析錯誤: {e}")
        return False

def main():
    config = load_config()
    if not config:
        return

    uart_cfg = config['uart_settings']
    try:
        ser = serial.Serial(
            uart_cfg['port'], 
            uart_cfg['baudrate'], 
            timeout=uart_cfg['timeout']
        )
        print(f"已連接 {uart_cfg['port']} @ {uart_cfg['baudrate']}")
    except serial.SerialException:
        print(f"錯誤: 無法開啟 {uart_cfg['port']}，請檢查是否被佔用。")
        return

    tests = config['test_cases']

    while True:
        print("\n==============================")
        print("      MCU 產測工具選單      ")
        print("==============================")
        for t in tests:
            print(f"{t['id']}. {t['name']}")
        print("A. 執行所有測試")
        print("Q. 離開")
        print("------------------------------")
        
        choice = input("請選擇: ").upper()

        if choice == 'Q':
            break
        elif choice == 'A':
            print("\n*** 開始自動測試所有項目 ***")
            results = []
            for t in tests:
                res = run_test(ser, t)
                results.append((t['name'], res))
                time.sleep(0.5)
            
            print("\n*** 總結報告 ***")
            for name, status in results:
                status_str = "PASS" if status else "FAIL"
                print(f"{name}: {status_str}")
                
        else:
            # 尋找對應 ID 的測試項目
            selected_test = next((t for t in tests if str(t['id']) == choice), None)
            if selected_test:
                run_test(ser, selected_test)
            else:
                print("無效的選擇，請重試。")

    ser.close()
    print("程式結束")

if __name__ == "__main__":
    main()