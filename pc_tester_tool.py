import serial
import json
import time
import os

# 載入設定檔
CONFIG_FILE = 'test_config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"uart_settings": {"port": "COM5", "baudrate": 115200, "timeout": 1}, "test_cases": []}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_packet(cmd_int, param_int):
    header = b'Loewe test ' 
    cmd = cmd_int.to_bytes(1, 'big')
    param = param_int.to_bytes(1, 'big')
    end = b'\x0d'
    return header + cmd + param + end

def send_and_receive(ser, cmd_int, param_int, desc="Manual Test"):
    print(f"\n--- 執行: {desc} ---")
    packet = build_packet(cmd_int, param_int)
    ser.reset_input_buffer() # 測試前清空，避免讀到舊的 Event
    print(f"TX (Hex): {packet.hex(' ')}")
    ser.write(packet)
    time.sleep(0.2)
    
    raw_response = ser.read_until(b'\r')
    if not raw_response:
        print("結果: [無回應]")
        return None
    try:
        response_str = raw_response.decode('utf-8', errors='ignore').strip()
        print(f"RX (Str): \033[96m{response_str}\033[0m")
        return response_str
    except Exception as e:
        print(f"解析錯誤: {e}")
        return None

def validate_response(response_str, test_case):
    if not response_str: return False
    clean_resp = response_str.replace("ACK: ", "").strip()
    criteria = test_case.get('criteria')
    expect_type = test_case.get('expect_type')
    if expect_type == 'exact': return clean_resp == str(criteria)
    elif expect_type == 'contains': return str(criteria) in clean_resp
    elif expect_type == 'length': return len(clean_resp) >= int(criteria)
    else: return True

def manual_input_mode(ser):
    print("\n[ 手動輸入模式 ]")
    try:
        cmd_str = input("CMD (Hex): ").strip()
        if not cmd_str: return
        cmd_int = int(cmd_str, 16)
        param_str = input("PARAM (Hex): ").strip()
        if not param_str: return
        param_int = int(param_str, 16)
        send_and_receive(ser, cmd_int, param_int, f"手動 CMD:{hex(cmd_int)}")
    except ValueError:
        print("錯誤: 輸入格式不正確")

def monitor_mode(ser):
    """
    監聽模式：持續顯示接收到的資料
    """
    print("\n" + "="*40)
    print("     進入監聽模式 (Monitor Mode)     ")
    print("  說明: 將持續顯示所有從 MCU 收到的資料")
    print("  離開: 請按 \033[93mCtrl + C\033[0m")
    print("="*40)
    
    ser.timeout = 0.1 # 設定短 timeout 以便迴圈檢查中斷
    
    try:
        while True:
            if ser.in_waiting > 0:
                # 讀取一行或一堆資料
                raw_data = ser.read(ser.in_waiting)
                try:
                    # 嘗試解碼顯示
                    text_data = raw_data.decode('utf-8', errors='replace').strip()
                    # 加上時間戳記
                    timestamp = time.strftime("%H:%M:%S")
                    if text_data:
                        print(f"[{timestamp}] RX: \033[95m{text_data}\033[0m")
                    else:
                        # 顯示原始 Hex (如果是無法顯示的字元)
                        print(f"[{timestamp}] RX (Hex): {raw_data.hex(' ')}")
                except Exception:
                    print(f"RX Raw: {raw_data}")
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n>>> 停止監聽，回到主選單。")
        # 恢復原本的 Timeout 設定 (假設 config 是 1秒)
        ser.timeout = 1 

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
        print("L. \033[95m進入監聽模式 (Live Monitor)\033[0m") # 新增功能
        print("A. 執行所有測試 (Auto Run)")
        print("Q. 離開 (Quit)")
        print("==============================")
        
        choice = input("請選擇: ").upper()

        if choice == 'Q': break
        elif choice == 'M': manual_input_mode(ser)
        elif choice == 'L': monitor_mode(ser) # 呼叫監聽模式
        elif choice == 'A':
            print("\n*** 開始自動測試 ***")
            for t in tests:
                c = int(t['cmd_hex'], 16)
                p = int(t['param_hex'], 16)
                resp = send_and_receive(ser, c, p, t['name'])
                status = validate_response(resp, t) if resp else False
                print(">>> PASS" if status else ">>> FAIL")
                time.sleep(0.5)
        else:
            selected_test = next((t for t in tests if str(t['id']) == choice), None)
            if selected_test:
                c = int(selected_test['cmd_hex'], 16)
                p = int(selected_test['param_hex'], 16)
                resp = send_and_receive(ser, c, p, selected_test['name'])
                if resp and validate_response(resp, selected_test):
                    print(">>> PASS")
                else:
                    print(">>> FAIL")

    ser.close()

if __name__ == "__main__":
    main()