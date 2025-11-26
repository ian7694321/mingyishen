#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
from pymodbus.client import ModbusTcpClient

HOST = "192.168.1.1"

PORTS = [502, 2001]          # 先掃常見 Modbus TCP port
UNITS = [0, 1, 255]          # 裝置 address:00，先把 0、1、255 都試試
BASES = ["3x", "4x"]         # 3x=Input(04), 4x=Holding(03)
WINDOWS = [(0, 16), (20, 16), (100, 16), (200, 16)]  # 起始位址(0-based), 長度

def read_regs(client, base, start, count, unit):
    """回傳 registers 或 None；兼容不同版本的 pymodbus 參數名稱。"""
    fn = client.read_input_registers if base == "3x" else client.read_holding_registers
    try:
        rr = fn(address=start, count=count, unit=unit)
    except TypeError:
        # 舊版用 slave 參數
        rr = fn(address=start, count=count, slave=unit)
    if rr.isError():
        try:
            ec = rr.exception_code  # Modbus 例外碼（若有）
        except Exception:
            ec = None
        return None
    return rr.registers

def fmt_vals(regs):
    # 顯示前 8 筆，附上嘗試解讀 float 的示例（word swap）
    out = "words=" + " ".join(f"{w:5d}" for w in regs[:8])
    if len(regs) >= 2:
        try:
            # 嘗試把前兩個 word 解析成 32bit 浮點（字交換常見）
            val = struct.unpack(">f", struct.pack(">HH", regs[1], regs[0]))[0]
            out += f" | floatSWAP[0:2]={val:.3f}"
        except Exception:
            pass
    return out

def probe():
    any_hit = False
    for port in PORTS:
        client = ModbusTcpClient(HOST, port=port, timeout=2)
        if not client.connect():
            print(f"[x] 無法連線 {HOST}:{port}")
            continue
        print(f"[+] 已連 {HOST}:{port}")
        for unit in UNITS:
            for base in BASES:
                for start, length in WINDOWS:
                    regs = read_regs(client, base, start, length, unit)
                    if regs:
                        any_hit = True
                        logical = 30001 if base == "3x" else 40001
                        print(f"  [OK] port={port} unit={unit} base={base} "
                              f"addr={logical+start}..{logical+start+length-1} -> {fmt_vals(regs)}")
        client.close()
    if not any_hit:
        print(">>> 沒有任何組合成功。大多數情況是：Port 不對（請確認是否 502），或裝置目前不是 Modbus 模式。")

if __name__ == "__main__":
    probe()
