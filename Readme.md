# Readme

## 執行步驟
安裝必要套件： 在終端機執行：pip install pyserial

設定環境：
如果您只有一台電腦，請下載虛擬 COM Port 軟體 (如 com0com) 建立一對虛擬 Port (例如 COM5 <-> COM6)。
將 test_config.json 中的 Port 設為 COM5。
將 mcu_device_sim.py 中的 DUT_PORT 設為 COM6。

執行：
開啟一個終端機，執行 python mcu_device_sim.py (模擬待測物)。
開啟另一個終端機，執行 python pc_tester_tool.py (產測程式)。

操作：
在 PC 端程式選單中輸入 1，您應該會看到模擬器收到 Hex 指令，並回傳版本號，PC 端判定 PASS。
您可以修改 JSON 檔案中的 criteria 來測試 FAIL 的情況。

程式碼特點
JSON 驅動：新增 Command 不需要修改 Python Code，只需在 JSON 增加項目即可。
模組化封包建立：build_packet 函式嚴格遵守 14 bytes 長度與 Header 格式。
視覺化回饋：PC 端程式使用簡單的 ANSI Color Code 顯示綠色 PASS / 紅色 FAIL。
彈性判斷：支援 exact (完全符合), contains (包含字串), length (長度檢查) 三種判斷模式。